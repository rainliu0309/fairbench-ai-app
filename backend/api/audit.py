from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.i18n import bilingual
from models import SystemOperationLog
from schemas import ApiResponse, AuditLogSummary

router = APIRouter(prefix="/audit-logs", tags=["Audit Log / 操作日志"])


@router.get("", response_model=ApiResponse[dict])
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    filters = [SystemOperationLog.action == action] if action else []
    total = await session.scalar(
        select(func.count(SystemOperationLog.id)).where(*filters)
    )
    rows = (
        await session.scalars(
            select(SystemOperationLog)
            .where(*filters)
            .order_by(SystemOperationLog.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApiResponse(
        data={
            "items": [AuditLogSummary.model_validate(row) for row in rows],
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
            "immutable": True,
        },
        message=bilingual("ok"),
    )
