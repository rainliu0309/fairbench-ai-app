from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.i18n import bilingual
from core.security import TokenError, decode_access_token
from models import User


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    role: str
    request_id: str
    ip_address: str | None


bearer_scheme = HTTPBearer(auto_error=False)


async def get_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> ActorContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail=bilingual("auth_required"))
    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=bilingual("auth_required")) from exc
    user = await session.get(User, str(claims["sub"]))
    if user is None or not user.is_active or user.role.value != claims["role"]:
        raise HTTPException(status_code=401, detail=bilingual("auth_required"))
    actor = ActorContext(
        actor_id=str(claims["sub"]),
        role=str(claims["role"]),
        request_id=request.state.request_id,
        ip_address=request.client.host if request.client else None,
    )
    request.state.actor = actor
    return actor
