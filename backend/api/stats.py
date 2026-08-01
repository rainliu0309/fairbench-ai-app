from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.i18n import bilingual
from models import Dataset, EvaluationTask, SampleStatus, TaskSampleResult, TaskStatus
from schemas import ApiResponse

router = APIRouter(prefix="/stats", tags=["Stats / 公平性指标"])


@router.get("/overview", response_model=ApiResponse[dict])
async def overview(session: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    dataset_count = await session.scalar(select(func.count(Dataset.id)))
    task_count = await session.scalar(select(func.count(EvaluationTask.id)))
    completed_count = await session.scalar(
        select(func.count(EvaluationTask.id)).where(
            EvaluationTask.status.in_([TaskStatus.completed, TaskStatus.partial])
        )
    )
    failed_sample_count = await session.scalar(
        select(func.count(TaskSampleResult.id)).where(
            TaskSampleResult.status == SampleStatus.failed
        )
    )
    recent = (
        await session.scalars(
            select(EvaluationTask)
            .where(EvaluationTask.metrics.is_not(None))
            .order_by(EvaluationTask.created_at.desc())
            .limit(10)
        )
    ).all()
    compliant = sum(bool((item.metrics or {}).get("is_compliant")) for item in recent)
    return ApiResponse(
        data={
            "dataset_count": int(dataset_count or 0),
            "task_count": int(task_count or 0),
            "completed_count": int(completed_count or 0),
            "failed_sample_count": int(failed_sample_count or 0),
            "compliance_rate": round(compliant / max(len(recent), 1), 4),
        },
        message=bilingual("ok"),
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse[dict])
async def task_metrics(
    task_id: str, session: AsyncSession = Depends(get_db)
) -> ApiResponse[dict]:
    task = await session.get(EvaluationTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    return ApiResponse(
        data={
            "task_id": task.id,
            "algorithm_name": task.algorithm_name,
            "threshold": task.fairness_threshold,
            "metrics": task.metrics or {},
        },
        message=bilingual("ok"),
    )


@router.get("/compare", response_model=ApiResponse[dict])
async def compare_tasks(
    dataset_id: str = Query(...),
    task_ids: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    query = select(EvaluationTask).where(
        EvaluationTask.dataset_id == dataset_id,
        EvaluationTask.metrics.is_not(None),
    )
    if task_ids:
        query = query.where(EvaluationTask.id.in_(task_ids))
    tasks = (await session.scalars(query.order_by(EvaluationTask.created_at))).all()
    series = [
        {
            "task_id": task.id,
            "algorithm_name": task.algorithm_name,
            "status": task.status.value,
            "metrics": task.metrics,
        }
        for task in tasks
    ]
    return ApiResponse(
        data={"dataset_id": dataset_id, "series": series},
        message=bilingual("ok"),
    )
