from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import (
    Dataset,
    EvaluationTask,
    SampleImage,
    SampleStatus,
    TaskSampleResult,
    TaskStatus,
)
from services.audit_service import append_audit_log
from services.stats_service import calculate_fairness_metrics
from services.storage_service import storage_service
from core.config import settings


async def load_bundled_demo_asset(sample: SampleImage) -> bytes | None:
    """Read a controlled SVG fixture packaged in the application image.

    Demo rows are deliberately immutable and always point to a ``demo/`` key.
    Keeping a read-only image copy in the deployment image lets the public
    walkthrough remain usable if an older seed run committed metadata before
    its S3 object archive was available. User-uploaded samples never take this
    path and continue to be served exclusively from object storage.
    """

    if not sample.object_key.startswith("demo/"):
        return None

    root = Path(settings.demo_assets_path).resolve()
    filename = Path(sample.filename)
    if filename.name != sample.filename:
        return None
    asset = (root / filename).resolve()
    if root not in asset.parents or not asset.is_file():
        return None
    return await asyncio.to_thread(asset.read_bytes)


async def _ensure_demo_objects(samples: list[SampleImage]) -> None:
    """Archive controlled synthetic assets in MinIO for actual HTTP evaluation."""
    for sample in samples:
        payload = await load_bundled_demo_asset(sample)
        if payload is None:
            continue
        await storage_service.put_bytes(sample.object_key, payload, sample.content_type)


async def seed_demo_data(session: AsyncSession) -> None:
    """Create optional synthetic fixtures; never seed real deployments by default."""
    existing = (
        await session.scalars(
            select(Dataset).where(Dataset.is_demo.is_(True)).options(selectinload(Dataset.samples))
        )
    ).first()
    if existing:
        await _ensure_demo_objects(existing.samples)
        legacy_tasks = await session.scalars(
            select(EvaluationTask).where(EvaluationTask.dataset_id == existing.id)
        )
        for task in legacy_tasks:
            if task.target_api_url.startswith("mock://"):
                task.target_api_url = settings.simulator_target_api_url
                task.target_api_config = {"auth_scheme": "none"}
        await session.commit()
        return

    dataset = Dataset(
        name="公共场景人脸公平性基准集 2026-Q2",
        description=(
            "覆盖年龄、性别与族裔交叉分组的合成演示图集；"
            "全部身份与样本均为模拟数据，不对应真实个人。"
        ),
        status="ready",
        sample_count=36,
        owner_id="regulator-demo",
        is_demo=True,
    )
    session.add(dataset)
    await session.flush()

    genders = ["female", "male", "non_binary"]
    age_groups = ["18-29", "30-44", "45-59", "60+"]
    ethnicities = ["east_asian", "south_asian", "black", "white", "latino", "mena"]
    samples: list[SampleImage] = []
    for index in range(36):
        labels = {
            "gender": genders[index % len(genders)],
            "age_group": age_groups[index % len(age_groups)],
            "ethnicity": ethnicities[index % len(ethnicities)],
            "confidence": round(0.88 + (index % 9) / 100, 2),
        }
        sample = SampleImage(
            dataset_id=dataset.id,
            filename=f"synthetic_face_{index + 1:03d}.svg",
            object_key=f"demo/synthetic_face_{index + 1:03d}.svg",
            content_type="image/svg+xml",
            ground_truth_identity=f"demo-person-{index + 1:03d}",
            agnes_labels=labels,
            effective_labels=labels,
            label_source="agnes",
            label_status="completed",
        )
        samples.append(sample)
        session.add(sample)
    await session.flush()

    profiles = [
        ("CityVision Face API v4.2", "completed", 100, 7),
        ("CivicID Recognition 3.8", "completed", 100, 5),
        ("MetroSecure CV 2.1", "partial", 100, 9),
        ("NorthStar Edge 1.6", "running", 64, 8),
    ]
    for task_index, (algorithm, status, progress, error_mod) in enumerate(profiles):
        records = []
        task = EvaluationTask(
            dataset_id=dataset.id,
            name=f"2026-Q2 {algorithm} 公平性复核",
            algorithm_name=algorithm,
            target_api_url=settings.simulator_target_api_url,
            target_api_config={"auth_scheme": "none"},
            status=TaskStatus(status),
            progress=progress,
            fairness_threshold=0.10,
            language="zh",
            created_by="regulator-demo",
        )
        session.add(task)
        await session.flush()
        if status == "running":
            task.metrics = None
            continue

        for index, sample in enumerate(samples):
            is_failed = status == "partial" and index % 13 == 0
            is_correct = (index + task_index * 2) % error_mod != 0
            row = TaskSampleResult(
                task_id=task.id,
                sample_id=sample.id,
                status=SampleStatus.failed if is_failed else SampleStatus.completed,
                predicted_identity=(
                    None
                    if is_failed
                    else sample.ground_truth_identity
                    if is_correct
                    else f"unknown-{index:03d}"
                ),
                confidence=None if is_failed else round(0.74 + (index % 20) / 100, 2),
                is_correct=None if is_failed else is_correct,
                latency_ms=None if is_failed else 80 + index * 3,
                response_payload=None if is_failed else {"mode": "seeded-demo"},
                error_code="UPSTREAM_TIMEOUT" if is_failed else None,
                error_message="Synthetic upstream timeout" if is_failed else None,
                retry_count=0,
            )
            session.add(row)
            if not is_failed:
                records.append({**(sample.effective_labels or {}), "is_correct": is_correct})
        task.metrics = calculate_fairness_metrics(records, task.fairness_threshold)

    await append_audit_log(
        session,
        actor_id="system-bootstrap",
        action="demo.seeded",
        resource_type="dataset",
        resource_id=dataset.id,
        details={"sample_count": 36, "task_count": len(profiles)},
    )
    await session.commit()
    await _ensure_demo_objects(samples)
