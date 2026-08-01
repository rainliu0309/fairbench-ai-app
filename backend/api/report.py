from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import ActorContext, get_actor
from core.database import get_db
from core.i18n import bilingual
from models import AuditReport
from schemas import ApiResponse, ReportCreate, ReportSummary
from services.report_service import generate_report, render_report_html
from services.storage_service import storage_service

router = APIRouter(prefix="/reports", tags=["Report / 审计报告"])


@router.get("", response_model=ApiResponse[list[ReportSummary]])
async def list_reports(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ReportSummary]]:
    reports = (
        await session.scalars(
            select(AuditReport).order_by(AuditReport.created_at.desc()).limit(100)
        )
    ).all()
    return ApiResponse(
        data=[ReportSummary.model_validate(item) for item in reports],
        message=bilingual("ok"),
    )


@router.post("/preview", response_class=HTMLResponse)
async def preview_report(
    payload: ReportCreate,
    session: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    try:
        _, _, html = await render_report_html(session, payload)
    except LookupError:
        raise HTTPException(status_code=404, detail=bilingual("not_found")) from None
    return HTMLResponse(html)


@router.post("", response_model=ApiResponse[ReportSummary], status_code=201)
async def create_report(
    payload: ReportCreate,
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[ReportSummary]:
    try:
        report, _ = await generate_report(session, payload, actor.actor_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=bilingual("not_found")) from None
    return ApiResponse(
        data=ReportSummary.model_validate(report), message=bilingual("report_ready")
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str, session: AsyncSession = Depends(get_db)
) -> Response:
    report = await session.get(AuditReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    payload = await storage_service.get_bytes(report.object_key)
    return Response(
        payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report.report_no}.pdf"',
            "X-Checksum-SHA256": report.checksum,
        },
    )
