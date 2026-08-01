from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class TaskStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class SampleStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class UserRole(str, enum.Enum):
    regulatory_reviewer = "regulatory_reviewer"
    system_administrator = "system_administrator"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="ready")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[str] = mapped_column(String(64), default="regulator-demo")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    samples: Mapped[list[SampleImage]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[EvaluationTask]] = relationship(back_populates="dataset")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.regulatory_reviewer, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SampleImage(Base, TimestampMixin):
    __tablename__ = "sample_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="image/jpeg")
    ground_truth_identity: Mapped[str | None] = mapped_column(String(160))
    agnes_labels: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    manual_labels: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    effective_labels: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    label_source: Mapped[str] = mapped_column(String(32), default="agnes")
    label_status: Mapped[str] = mapped_column(String(32), default="pending")
    annotation_error: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)

    dataset: Mapped[Dataset] = relationship(back_populates="samples")
    results: Mapped[list[TaskSampleResult]] = relationship(back_populates="sample")


class EvaluationTask(Base, TimestampMixin):
    __tablename__ = "evaluation_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    algorithm_name: Mapped[str] = mapped_column(String(160), nullable=False)
    target_api_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_api_method: Mapped[str] = mapped_column(String(12), default="POST")
    target_api_config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    api_key_fingerprint: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.queued, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    fairness_threshold: Mapped[float] = mapped_column(Float, default=0.10)
    language: Mapped[str] = mapped_column(String(8), default="zh")
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(64), default="regulator-demo")

    dataset: Mapped[Dataset] = relationship(back_populates="tasks")
    results: Mapped[list[TaskSampleResult]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    reports: Mapped[list[AuditReport]] = relationship(back_populates="task")


class TaskSampleResult(Base, TimestampMixin):
    __tablename__ = "task_sample_results"
    __table_args__ = (
        UniqueConstraint("task_id", "sample_id", name="uq_task_sample_result"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_tasks.id", ondelete="CASCADE"), index=True
    )
    sample_id: Mapped[str] = mapped_column(ForeignKey("sample_images.id"), index=True)
    status: Mapped[SampleStatus] = mapped_column(
        Enum(SampleStatus), default=SampleStatus.pending, index=True
    )
    predicted_identity: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[float | None] = mapped_column(Float)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped[EvaluationTask] = relationship(back_populates="results")
    sample: Mapped[SampleImage] = relationship(back_populates="results")


class AuditReport(Base, TimestampMixin):
    __tablename__ = "audit_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), index=True)
    report_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="zh")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    generated_by: Mapped[str] = mapped_column(String(64), default="regulator-demo")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    task: Mapped[EvaluationTask] = relationship(back_populates="reports")


class SystemOperationLog(Base):
    __tablename__ = "system_operation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(
        String(64), default="regulatory_reviewer"
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)


@event.listens_for(SystemOperationLog, "before_update")
@event.listens_for(SystemOperationLog, "before_delete")
def _prevent_audit_mutation(*_: Any) -> None:
    """Application-level guard; the API exposes no mutation endpoints."""
    raise ValueError("system_operation_logs is append-only")


__all__ = [
    "AuditReport",
    "Dataset",
    "EvaluationTask",
    "SampleImage",
    "SampleStatus",
    "SystemOperationLog",
    "TaskSampleResult",
    "TaskStatus",
    "User",
    "UserRole",
]
