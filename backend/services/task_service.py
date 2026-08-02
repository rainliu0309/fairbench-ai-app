from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import AsyncSessionLocal
from core.security import get_task_secret
from models import (
    Dataset,
    EvaluationTask,
    SampleImage,
    SampleStatus,
    TaskSampleResult,
    TaskStatus,
)
from services.agnes_service import agnes_service
from services.audit_service import append_audit_log
from services.demo_service import load_bundled_demo_asset
from services.stats_service import calculate_fairness_metrics
from services.storage_service import storage_service
from services.target_api_service import evaluate_sample


async def read_sample_bytes(sample: SampleImage) -> bytes:
    """Load user samples from S3 and controlled demo samples from the image."""

    demo_payload = await load_bundled_demo_asset(sample)
    if demo_payload is not None:
        return demo_payload
    return await storage_service.get_bytes(sample.object_key)


async def enqueue_evaluation(task_id: str, failed_only: bool = False) -> None:
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await redis.enqueue_job("run_evaluation", task_id, failed_only)
    finally:
        await redis.aclose()


async def enqueue_dataset_annotation(dataset_id: str) -> None:
    """Schedule annotation after bytes have been durably written to MinIO."""
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await redis.enqueue_job("annotate_dataset", dataset_id)
    finally:
        await redis.aclose()


async def annotate_dataset(_ctx: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    """Obtain Agnes labels before a dataset becomes available for assessment."""
    async with AsyncSessionLocal() as session:
        dataset = await session.scalar(
            select(Dataset)
            .where(Dataset.id == dataset_id)
            .options(selectinload(Dataset.samples))
        )
        if dataset is None:
            return {"status": "not_found", "dataset_id": dataset_id}
        dataset.status = "annotating"

        # Process samples in small, bounded batches.  This prevents a slow or
        # unavailable external provider from turning an upload into N serial
        # timeout windows, while avoiding an unbounded number of image bytes
        # and coroutines in memory for a large dataset.  Database writes stay
        # serialized after each batch, so the SQLAlchemy session is never
        # shared across concurrent coroutines.
        candidates = [
            sample
            for sample in dataset.samples
            if not sample.manual_labels and not sample.effective_labels
        ]

        async def annotate_one(sample: SampleImage) -> tuple[str, dict[str, Any] | None, str | None]:
            try:
                image_bytes = await read_sample_bytes(sample)
                labels = await agnes_service.annotate(
                    image_bytes, sample.content_type, sample.filename
                )
                return sample.id, labels, None
            except Exception as exc:
                return sample.id, None, str(exc)[:1000]

        succeeded = 0
        failed = 0
        batch_size = max(1, settings.agnes_max_concurrency)
        for offset in range(0, len(candidates), batch_size):
            batch = candidates[offset : offset + batch_size]
            outcomes = await asyncio.gather(*(annotate_one(sample) for sample in batch))
            by_id = {sample.id: sample for sample in batch}

            for sample_id, labels, error in outcomes:
                sample = by_id[sample_id]
                if labels is not None:
                    sample.agnes_labels = labels
                    sample.effective_labels = labels
                    sample.label_source = "agnes"
                    sample.label_status = "completed"
                    sample.annotation_error = None
                    succeeded += 1
                else:
                    sample.label_status = "failed"
                    sample.annotation_error = error
                    failed += 1

            # Preserve progress if the worker restarts partway through a large
            # dataset.  The final dataset status and audit record are written
            # after every candidate has reached a terminal annotation state.
            await session.commit()
        dataset.status = "ready" if failed == 0 else "label_review_required"
        await append_audit_log(
            session,
            actor_id="system-worker",
            action="dataset.annotation_completed",
            resource_type="dataset",
            resource_id=dataset.id,
            details={"annotated": succeeded, "failed": failed, "status": dataset.status},
        )
        await session.commit()
        return {"status": dataset.status, "annotated": succeeded, "failed": failed}


async def run_evaluation(
    _ctx: dict[str, Any], task_id: str, failed_only: bool = False
) -> dict[str, Any]:
    """ARq entry point: label, evaluate, aggregate, and persist one task."""
    async with AsyncSessionLocal() as session:
        task = await session.scalar(
            select(EvaluationTask)
            .where(EvaluationTask.id == task_id)
            .options(
                selectinload(EvaluationTask.dataset).selectinload(Dataset.samples)
            )
        )
        if task is None:
            return {"status": "not_found", "task_id": task_id}

        task.status = TaskStatus.running
        task.started_at = task.started_at or datetime.now(timezone.utc)
        task.error_message = None
        await append_audit_log(
            session,
            actor_id="system-worker",
            action="evaluation.started",
            resource_type="evaluation_task",
            resource_id=task.id,
            details={"failed_only": failed_only},
        )
        await session.commit()

        secret = await get_task_secret(task.id)
        provider_config = task.target_api_config or {}
        requires_secret = provider_config.get("auth_scheme", "bearer") != "none"
        if requires_secret and secret is None:
            task.status = TaskStatus.failed
            task.error_message = "API_SECRET_EXPIRED"
            await append_audit_log(
                session,
                actor_id="system-worker",
                action="evaluation.failed",
                resource_type="evaluation_task",
                resource_id=task.id,
                details={"reason": "API_SECRET_EXPIRED"},
            )
            await session.commit()
            return {"status": "failed", "reason": "API_SECRET_EXPIRED"}

        samples = task.dataset.samples
        if failed_only:
            failed_ids = set(
                (
                    await session.scalars(
                        select(TaskSampleResult.sample_id).where(
                            TaskSampleResult.task_id == task.id,
                            TaskSampleResult.status == SampleStatus.pending,
                        )
                    )
                ).all()
            )
            samples = [sample for sample in samples if sample.id in failed_ids]

        completed = 0
        failed = 0
        for index, sample in enumerate(samples, start=1):
            existing = await session.scalar(
                select(TaskSampleResult).where(
                    TaskSampleResult.task_id == task.id,
                    TaskSampleResult.sample_id == sample.id,
                )
            )
            result_row = existing or TaskSampleResult(
                task_id=task.id, sample_id=sample.id
            )
            if existing is None:
                session.add(result_row)

            try:
                image_bytes = await read_sample_bytes(sample)
                if not sample.effective_labels:
                    labels = await agnes_service.annotate(
                        image_bytes, sample.content_type, sample.filename
                    )
                    sample.agnes_labels = labels
                    sample.effective_labels = labels
                    sample.label_status = "completed"

                response = await evaluate_sample(
                    url=task.target_api_url,
                    method=task.target_api_method,
                    api_key=secret or "",
                    image_bytes=image_bytes,
                    filename=sample.filename,
                    content_type=sample.content_type,
                    ground_truth_identity=sample.ground_truth_identity,
                    provider_config=provider_config,
                )
                result_row.status = SampleStatus.completed
                result_row.predicted_identity = response["predicted_identity"]
                result_row.confidence = response["confidence"]
                result_row.is_correct = response["is_correct"]
                result_row.latency_ms = response["latency_ms"]
                result_row.response_payload = response["raw"]
                result_row.error_code = None
                result_row.error_message = None
                completed += 1
            except Exception as exc:
                result_row.status = SampleStatus.failed
                result_row.is_correct = None
                result_row.error_code = getattr(exc, "code", type(exc).__name__)
                result_row.error_message = str(exc)[:1000]
                failed += 1

            task.progress = int(index / max(len(samples), 1) * 100)
            if index % 10 == 0:
                await session.commit()

        rows = (
            await session.execute(
                select(TaskSampleResult)
                .where(
                    TaskSampleResult.task_id == task.id,
                    TaskSampleResult.status == SampleStatus.completed,
                )
                .options(selectinload(TaskSampleResult.sample))
            )
        ).scalars()
        records = []
        for row in rows:
            labels = row.sample.effective_labels or {}
            records.append({**labels, "is_correct": bool(row.is_correct)})

        task.metrics = calculate_fairness_metrics(records, task.fairness_threshold)
        task.progress = 100
        task.completed_at = datetime.now(timezone.utc)
        task.status = TaskStatus.partial if failed else TaskStatus.completed
        await append_audit_log(
            session,
            actor_id="system-worker",
            action="evaluation.completed",
            resource_type="evaluation_task",
            resource_id=task.id,
            details={
                "completed_samples": completed,
                "failed_samples": failed,
                "is_compliant": task.metrics["is_compliant"],
            },
        )
        await session.commit()
        return {"status": task.status.value, "completed": completed, "failed": failed}
