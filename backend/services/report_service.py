from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from weasyprint import HTML

from core.report_text import REPORT_TEXT
from models import AuditReport, EvaluationTask, SampleStatus, TaskSampleResult
from schemas import ReportCreate
from services.audit_service import append_audit_log
from services.storage_service import storage_service

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


async def build_report_context(
    session: AsyncSession, request: ReportCreate
) -> tuple[EvaluationTask, dict[str, Any]]:
    task = await session.scalar(
        select(EvaluationTask)
        .where(EvaluationTask.id == request.task_id)
        .options(selectinload(EvaluationTask.dataset))
    )
    if task is None:
        raise LookupError("task_not_found")
    failed_results = (
        await session.scalars(
            select(TaskSampleResult)
            .where(
                TaskSampleResult.task_id == task.id,
                TaskSampleResult.status == SampleStatus.failed,
            )
            .order_by(TaskSampleResult.updated_at.desc())
        )
    ).all()
    language = request.language if request.language in REPORT_TEXT else "zh"
    metrics = task.metrics or {}
    generated_at = datetime.now(timezone.utc)
    context = {
        "t": REPORT_TEXT[language],
        "language": language,
        "report_no": f"FB-{generated_at:%Y%m%d%H%M%S%f}-{task.id[:8].upper()}",
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "title": request.title,
        "authority": request.issuing_authority,
        "signer": request.signer,
        "algorithm": task.algorithm_name,
        "dataset": (
            REPORT_TEXT[language]["demo_dataset"]
            if task.dataset.is_demo
            else task.dataset.name
        ),
        "threshold": task.fairness_threshold,
        "metrics": metrics,
        "groups": metrics.get("groups", []),
        "is_compliant": metrics.get("is_compliant", False),
        "failed_count": len(failed_results),
        "failed_samples": [
            {
                "sample_id": row.sample_id,
                "error_code": row.error_code or "—",
                "error_message": row.error_message or "—",
                "retry_count": row.retry_count,
            }
            for row in failed_results
        ],
        "include_failed_samples": request.include_failed_samples,
        "include_methodology": request.include_methodology,
    }
    context["source_checksum"] = hashlib.sha256(
        repr(sorted(context.items(), key=lambda item: item[0])).encode("utf-8")
    ).hexdigest()
    return task, context


async def render_report_html(
    session: AsyncSession, request: ReportCreate
) -> tuple[EvaluationTask, dict[str, Any], str]:
    task, context = await build_report_context(session, request)
    template = jinja.get_template("audit_report.html")
    return task, context, template.render(**context)


async def generate_report(
    session: AsyncSession, request: ReportCreate, actor_id: str
) -> tuple[AuditReport, bytes]:
    task, context, html = await render_report_html(session, request)
    pdf_bytes = await asyncio.to_thread(HTML(string=html).write_pdf)
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    object_key = f"reports/{task.id}/{context['report_no']}.pdf"
    await storage_service.put_bytes(object_key, pdf_bytes, "application/pdf")
    report = AuditReport(
        task_id=task.id,
        report_no=context["report_no"],
        title=request.title,
        language=request.language,
        object_key=object_key,
        parameters=request.model_dump(exclude={"task_id"}),
        generated_by=actor_id,
        checksum=checksum,
    )
    session.add(report)
    await session.flush()
    await append_audit_log(
        session,
        actor_id=actor_id,
        action="report.generated",
        resource_type="audit_report",
        resource_id=report.id,
        details={
            "task_id": task.id,
            "report_no": report.report_no,
            "language": request.language,
            "checksum": checksum,
        },
    )
    await session.commit()
    await session.refresh(report)
    return report, pdf_bytes
