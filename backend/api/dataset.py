import csv
import hashlib
import io
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import ActorContext, get_actor
from core.config import settings
from core.database import get_db
from core.i18n import bilingual
from core.security import clear_task_secret
from models import Dataset, EvaluationTask, SampleImage, TaskStatus
from schemas import ApiResponse, DatasetSummary, LabelUpdate, SampleSummary
from services.audit_service import append_audit_log
from services.storage_service import storage_service
from services.task_service import enqueue_dataset_annotation

router = APIRouter(prefix="/datasets", tags=["Dataset / 测试图集"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def verified_image_type(payload: bytes) -> str | None:
    """Accept only the three raster formats exposed by the upload policy.

    Browser-provided MIME types are not trustworthy.  SVG is deliberately kept
    out of public uploads because it can contain active/external content; the
    bundled synthetic SVGs are written only by the controlled demo seeder.
    """
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("", response_model=ApiResponse[dict])
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str = Query(default="", max_length=100),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    filters = []
    if search:
        filters.append(
            or_(Dataset.name.ilike(f"%{search}%"), Dataset.description.ilike(f"%{search}%"))
        )
    total = await session.scalar(select(func.count(Dataset.id)).where(*filters))
    datasets = (
        await session.scalars(
            select(Dataset)
            .where(*filters)
            .order_by(Dataset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApiResponse(
        data={
            "items": [DatasetSummary.model_validate(item) for item in datasets],
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
        },
        message=bilingual("ok"),
    )


@router.post("/upload", response_model=ApiResponse[DatasetSummary], status_code=201)
async def upload_dataset(
    name: str = Form(min_length=2, max_length=160),
    description: str = Form(default="", max_length=2000),
    files: list[UploadFile] = File(min_length=1),
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[DatasetSummary]:
    if len(files) > settings.max_upload_files:
        raise HTTPException(status_code=413, detail=bilingual("validation_error"))
    dataset = Dataset(
        name=name,
        description=description,
        status="processing",
        owner_id=actor.actor_id,
    )
    session.add(dataset)
    await session.flush()

    for uploaded in files:
        payload = await uploaded.read(settings.max_upload_file_bytes + 1)
        if len(payload) > settings.max_upload_file_bytes:
            raise HTTPException(status_code=413, detail=bilingual("validation_error"))
        content_type = verified_image_type(payload)
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail=bilingual("validation_error"))
        safe_name = os.path.basename(uploaded.filename or f"sample-{uuid.uuid4()}.jpg")
        if not safe_name or safe_name in {".", ".."}:
            safe_name = f"sample-{uuid.uuid4()}.jpg"
        object_key = f"datasets/{dataset.id}/{uuid.uuid4()}-{safe_name}"
        await storage_service.put_bytes(object_key, payload, content_type)
        session.add(
            SampleImage(
                dataset_id=dataset.id,
                filename=safe_name,
                object_key=object_key,
                content_type=content_type,
                checksum=hashlib.sha256(payload).hexdigest(),
            )
        )
    dataset.sample_count = len(files)
    dataset.status = "processing"
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="dataset.created",
        resource_type="dataset",
        resource_id=dataset.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"name": name, "sample_count": len(files)},
    )
    await session.commit()
    await session.refresh(dataset)
    await enqueue_dataset_annotation(dataset.id)
    return ApiResponse(
        data=DatasetSummary.model_validate(dataset),
        message=bilingual("dataset_uploaded"),
    )


@router.delete("/{dataset_id}", response_model=ApiResponse[dict])
async def delete_dataset(
    dataset_id: str,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Delete a non-demo dataset and its dependent assessment artifacts.

    The immutable system log deliberately remains as evidence of the deletion.
    Public baseline/demo datasets are protected in both the UI and API.
    """
    dataset = await session.scalar(
        select(Dataset)
        .where(Dataset.id == dataset_id)
        .options(
            selectinload(Dataset.samples),
            selectinload(Dataset.tasks).selectinload(EvaluationTask.reports),
        )
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    if dataset.is_demo:
        raise HTTPException(status_code=403, detail=bilingual("demo_dataset_protected"))
    if dataset.status in {"processing", "annotating"} or any(
        task.status in {TaskStatus.queued, TaskStatus.running} for task in dataset.tasks
    ):
        raise HTTPException(status_code=409, detail=bilingual("dataset_active"))

    dataset_name = dataset.name
    task_ids = [task.id for task in dataset.tasks]
    sample_keys = [sample.object_key for sample in dataset.samples]
    report_keys = [report.object_key for task in dataset.tasks for report in task.reports]

    # Delete immutable file objects before committing database deletion.  If a
    # storage operation fails, the transaction is not committed and the dataset
    # remains available for a safe retry.
    for object_key in [*report_keys, *sample_keys]:
        await storage_service.delete_object(object_key)
    for task in dataset.tasks:
        for report in task.reports:
            await session.delete(report)
        await session.delete(task)
    await session.delete(dataset)
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="dataset.deleted",
        resource_type="dataset",
        resource_id=dataset_id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={
            "dataset_name": dataset_name,
            "sample_count": len(sample_keys),
            "evaluation_task_count": len(task_ids),
            "archived_report_count": len(report_keys),
        },
    )
    await session.commit()
    for task_id in task_ids:
        await clear_task_secret(task_id)
    return ApiResponse(
        data={"dataset_id": dataset_id, "deleted": True},
        message=bilingual("dataset_deleted"),
    )


@router.get("/{dataset_id}/samples", response_model=ApiResponse[dict])
async def list_samples(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    label_source: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    filters = [SampleImage.dataset_id == dataset_id]
    if label_source:
        filters.append(SampleImage.label_source == label_source)
    total = await session.scalar(select(func.count(SampleImage.id)).where(*filters))
    samples = (
        await session.scalars(
            select(SampleImage)
            .where(*filters)
            .order_by(SampleImage.created_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApiResponse(
        data={
            "items": [
                SampleSummary.model_validate(item).model_copy(
                    update={"preview_url": f"/datasets/{dataset_id}/samples/{item.id}/content"}
                )
                for item in samples
            ],
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
        },
        message=bilingual("ok"),
    )


@router.get("/{dataset_id}/samples/{sample_id}/content")
async def read_sample_content(
    dataset_id: str,
    sample_id: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    sample = await session.scalar(
        select(SampleImage).where(
            SampleImage.id == sample_id, SampleImage.dataset_id == dataset_id
        )
    )
    if sample is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    payload = await storage_service.get_bytes(sample.object_key)
    return Response(
        content=payload,
        media_type=sample.content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="{sample.filename}"',
        },
    )


@router.get("/{dataset_id}/samples/{sample_id}/preview", response_model=ApiResponse[dict])
async def preview_sample(
    dataset_id: str,
    sample_id: str,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Compatibility endpoint; the client uses authenticated byte streaming."""
    sample = await session.scalar(
        select(SampleImage).where(
            SampleImage.id == sample_id, SampleImage.dataset_id == dataset_id
        )
    )
    if sample is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    return ApiResponse(
        data={"url": f"/datasets/{dataset_id}/samples/{sample_id}/content"},
        message=bilingual("ok"),
    )


@router.patch(
    "/{dataset_id}/samples/{sample_id}/labels",
    response_model=ApiResponse[SampleSummary],
)
async def update_labels(
    dataset_id: str,
    sample_id: str,
    payload: LabelUpdate,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[SampleSummary]:
    sample = await session.scalar(
        select(SampleImage).where(
            SampleImage.id == sample_id, SampleImage.dataset_id == dataset_id
        )
    )
    if sample is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    previous = sample.effective_labels
    previous_annotation_error = sample.annotation_error
    manual = payload.model_dump(exclude={"reason", "ground_truth_identity"})
    sample.manual_labels = manual
    sample.effective_labels = manual
    sample.label_source = "manual"
    sample.label_status = "completed"
    # A completed manual review resolves the actionable annotation failure.
    # The original failure is retained in the immutable audit record below.
    sample.annotation_error = None
    if payload.ground_truth_identity is not None:
        sample.ground_truth_identity = payload.ground_truth_identity
    dataset = await session.get(Dataset, dataset_id)
    if dataset is not None:
        unresolved = await session.scalar(
            select(func.count(SampleImage.id)).where(
                SampleImage.dataset_id == dataset_id,
                SampleImage.effective_labels.is_(None),
            )
        )
        if not unresolved:
            dataset.status = "ready"
    await append_audit_log(
        session,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action="sample.labels_corrected",
        resource_type="sample_image",
        resource_id=sample.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={
            "dataset_id": dataset_id,
            "previous_labels": previous,
            "resolved_annotation_error": previous_annotation_error,
            "new_labels": manual,
            "reason": payload.reason,
            "dataset_status": dataset.status if dataset else None,
        },
    )
    await session.commit()
    await session.refresh(sample)
    return ApiResponse(
        data=SampleSummary.model_validate(sample),
        message=bilingual("label_updated"),
    )


@router.get("/{dataset_id}/export.csv")
async def export_dataset_csv(
    dataset_id: str,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    samples = (
        await session.scalars(
            select(SampleImage)
            .where(SampleImage.dataset_id == dataset_id)
            .order_by(SampleImage.filename)
        )
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "sample_id",
            "filename",
            "ground_truth_identity",
            "age_group",
            "gender",
            "ethnicity",
            "label_source",
        ]
    )
    for sample in samples:
        labels = sample.effective_labels or {}
        writer.writerow(
            [
                sample.id,
                sample.filename,
                sample.ground_truth_identity,
                labels.get("age_group"),
                labels.get("gender"),
                labels.get("ethnicity"),
                sample.label_source,
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}.csv"'},
    )
