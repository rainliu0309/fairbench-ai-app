import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import SystemOperationLog


async def append_audit_log(
    session: AsyncSession,
    *,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
    actor_role: str = "regulatory_reviewer",
) -> SystemOperationLog:
    """Append a hash-chained log entry. No update or delete API exists."""
    if session.bind and session.bind.dialect.name == "postgresql":
        # Serialize chain writers so concurrent requests cannot create forks.
        await session.execute(text("SELECT pg_advisory_xact_lock(20260730)"))
    previous = await session.scalar(
        select(SystemOperationLog).order_by(desc(SystemOperationLog.occurred_at)).limit(1)
    )
    previous_hash = previous.entry_hash if previous else None
    occurred_at = datetime.now(timezone.utc)
    canonical = json.dumps(
        {
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request_id": request_id,
            "occurred_at": occurred_at.isoformat(),
            "details": details or {},
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    entry = SystemOperationLog(
        occurred_at=occurred_at,
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        ip_address=ip_address,
        details=details or {},
        previous_hash=previous_hash,
        entry_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
    session.add(entry)
    return entry
