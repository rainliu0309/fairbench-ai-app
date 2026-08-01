import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import ActorContext, get_actor
from core.database import get_db
from core.i18n import bilingual
from core.security import cache_task_secret, clear_task_secret, secret_fingerprint
from models import (
    Dataset,
    EvaluationTask,
    SampleStatus,
    TaskSampleResult,
    TaskStatus,
)
from schemas import (
    ApiResponse,
    FailedSample,
    RetryFailedRequest,
    TaskCreate,
    TaskSummary,
)
from services.audit_service import append_audit_log
from services.task_service import enqueue_evaluation
from services.storage_service import storage_service

router = APIRouter(prefix="/tasks", tags=["Task / 评测任务"])

SEEDED_DEMO_ALGORITHMS = {
    "CityVision Face API v4.2",
    "CivicID Recognition 3.8",
    "MetroSecure CV 2.1",
    "NorthStar Edge 1.6",
}


@router.get("", response_model=ApiResponse[dict])
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    filters = []
    if status:
        filters.append(EvaluationTask.status == status)
    if dataset_id:
        filters.append(EvaluationTask.dataset_id == dataset_id)
    total = await session.scalar(select(func.count(EvaluationTask.id)).where(*filters))
    tasks = (
        await session.scalars(
            select(EvaluationTask)
            .where(*filters)
            .order_by(EvaluationTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApiResponse(
        data={
            "items": [TaskSummary.model_validate(item) for item in tasks],
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
        },
        message=bilingual("ok"),
    )


@router.post("", response_model=ApiResponse[TaskSummary], status_code=201)
async def create_task(
    payload: TaskCreate,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[TaskSummary]:
    dataset = await session.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    if dataset.status != "ready":
        raise HTTPException(status_code=409, detail=bilingual("dataset_not_ready"))
    task = EvaluationTask(
        dataset_id=payload.dataset_id,
        name=payload.name,
        algorithm_name=payload.algorithm_name,
        target_api_url=payload.target_api_url,
        target_api_method=payload.target_api_method,
        target_api_config=payload.provider_config.model_dump(),
        api_key_fingerprint=secret_fingerprint(payload.api_key) if payload.api_key else None,
        fairness_threshold=payload.fairness_threshold,
        language=payload.language,
        status=TaskStatus.queued,
        created_by=actor.actor_id,
    )
    session.add(task)
    await session.flush()
    if payload.api_key:
        await cache_task_secret(task.id, payload.api_key)
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="evaluation.created",
        resource_type="evaluation_task",
        resource_id=task.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={
            "dataset_id": payload.dataset_id,
            "algorithm_name": payload.algorithm_name,
            "target_api_url": payload.target_api_url,
            "provider_config": payload.provider_config.model_dump(),
            "fairness_threshold": payload.fairness_threshold,
            "api_key_fingerprint": task.api_key_fingerprint,
        },
    )
    await session.commit()
    await session.refresh(task)
    await enqueue_evaluation(task.id)
    return ApiResponse(
        data=TaskSummary.model_validate(task), message=bilingual("task_queued")
    )


@router.get("/{task_id}", response_model=ApiResponse[TaskSummary])
async def get_task(
    task_id: str, session: AsyncSession = Depends(get_db)
) -> ApiResponse[TaskSummary]:
    task = await session.get(EvaluationTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    return ApiResponse(data=TaskSummary.model_validate(task), message=bilingual("ok"))


@router.delete("/{task_id}", response_model=ApiResponse[dict])
async def delete_task(
    task_id: str,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Purge a finished evaluation while retaining its immutable audit evidence."""
    task = await session.scalar(
        select(EvaluationTask)
        .where(EvaluationTask.id == task_id)
        .options(selectinload(EvaluationTask.reports))
    )
    if task is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    if task.created_by == "regulator-demo" and task.algorithm_name in SEEDED_DEMO_ALGORITHMS:
        raise HTTPException(status_code=403, detail=bilingual("demo_task_protected"))
    if task.status in {TaskStatus.queued, TaskStatus.running}:
        raise HTTPException(status_code=409, detail=bilingual("task_active"))

    result_count = await session.scalar(
        select(func.count(TaskSampleResult.id)).where(TaskSampleResult.task_id == task.id)
    )
    report_keys = [report.object_key for report in task.reports]
    for object_key in report_keys:
        await storage_service.delete_object(object_key)
    for report in task.reports:
        await session.delete(report)
    await session.delete(task)
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="evaluation.deleted",
        resource_type="evaluation_task",
        resource_id=task_id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={
            "task_name": task.name,
            "algorithm_name": task.algorithm_name,
            "status": task.status.value,
            "sample_result_count": int(result_count or 0),
            "archived_report_count": len(report_keys),
        },
    )
    await session.commit()
    await clear_task_secret(task_id)
    return ApiResponse(
        data={"task_id": task_id, "deleted": True},
        message=bilingual("task_deleted"),
    )


@router.get("/{task_id}/failed-samples", response_model=ApiResponse[list[FailedSample]])
async def list_failed_samples(
    task_id: str, session: AsyncSession = Depends(get_db)
) -> ApiResponse[list[FailedSample]]:
    rows = (
        await session.scalars(
            select(TaskSampleResult)
            .where(
                TaskSampleResult.task_id == task_id,
                TaskSampleResult.status == SampleStatus.failed,
            )
            .order_by(TaskSampleResult.updated_at.desc())
        )
    ).all()
    return ApiResponse(
        data=[FailedSample.model_validate(row) for row in rows],
        message=bilingual("ok"),
    )


@router.post("/{task_id}/retry-failed", response_model=ApiResponse[dict])
async def retry_failed_samples(
    task_id: str,
    payload: RetryFailedRequest,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    task = await session.get(EvaluationTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    rows = (
        await session.scalars(
            select(TaskSampleResult).where(
                TaskSampleResult.task_id == task_id,
                TaskSampleResult.status == SampleStatus.failed,
            )
        )
    ).all()
    for row in rows:
        row.status = SampleStatus.pending
        row.retry_count += 1
    task.status = TaskStatus.queued
    task.progress = 0
    if payload.api_key:
        await cache_task_secret(task.id, payload.api_key)
        task.api_key_fingerprint = secret_fingerprint(payload.api_key)
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="evaluation.failed_samples_retried",
        resource_type="evaluation_task",
        resource_id=task.id,
        request_id=actor.request_id,
        details={"sample_count": len(rows)},
    )
    await session.commit()
    await enqueue_evaluation(task.id, failed_only=True)
    return ApiResponse(
        data={"task_id": task.id, "sample_count": len(rows)},
        message=bilingual("retry_queued"),
    )


@router.get("/{task_id}/results.csv")
async def export_task_results(
    task_id: str, session: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    rows = (
        await session.scalars(
            select(TaskSampleResult)
            .where(TaskSampleResult.task_id == task_id)
            .options(selectinload(TaskSampleResult.sample))
        )
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "sample_id",
            "filename",
            "status",
            "predicted_identity",
            "confidence",
            "is_correct",
            "latency_ms",
            "error_code",
            "retry_count",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.sample_id,
                row.sample.filename,
                row.status.value,
                row.predicted_identity,
                row.confidence,
                row.is_correct,
                row.latency_ms,
                row.error_code,
                row.retry_count,
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{task_id}-results.csv"'},
    )
