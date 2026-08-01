"""Local identity endpoints for a self-hosted Fair Bench deployment.

Enterprise roll-outs can replace this module with an OIDC/SAML gateway while
retaining the same ``ActorContext`` interface used by the audit layer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import ActorContext, get_actor
from core.database import get_db
from core.i18n import bilingual
from core.config import settings
from core.security import create_access_token, hash_password, verify_password
from models import User, UserRole
from schemas import ApiResponse, AuthUser, LoginRequest, LoginResult, SetupRequest
from services.audit_service import append_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication / 身份认证"])


def serialize_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value,
    )


async def ensure_local_administrator(session: AsyncSession) -> User | None:
    """Provide a frictionless session only for the explicitly local demo mode."""
    if not settings.local_single_user_mode:
        return None
    user = await session.scalar(
        select(User)
        .where(User.role == UserRole.system_administrator, User.is_active.is_(True))
        .order_by(User.created_at)
    )
    if user is not None:
        return user
    user = User(
        email=settings.local_admin_email.strip().lower(),
        display_name=settings.local_admin_display_name,
        # This account has no known interactive password in local single-user
        # mode. Production mode always uses an operator-created password.
        password_hash=hash_password("local-mode-password-disabled"),
        role=UserRole.system_administrator,
    )
    session.add(user)
    await session.flush()
    await append_audit_log(
        session,
        actor_id=user.id,
        actor_role=user.role.value,
        action="identity.local_administrator_provisioned",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
    )
    await session.commit()
    return user


@router.get("/setup-status", response_model=ApiResponse[dict])
async def setup_status(session: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    count = await session.scalar(select(func.count(User.id)))
    return ApiResponse(
        data={
            # In local single-user mode the first administrator is provisioned
            # by the one-click session endpoint.  Do not expose the normal
            # bootstrap/password form before that first click.
            "setup_required": not bool(count) and not settings.local_single_user_mode,
            # A public password is never sent to the browser.  The deployment
            # owner must explicitly enable local single-user mode to expose the
            # one-click demonstration session.
            "demo_login_available": settings.local_single_user_mode,
            "default_admin_email": (
                settings.local_admin_email if settings.local_single_user_mode else None
            ),
        },
        message=bilingual("ok"),
    )


@router.post("/local-session", response_model=ApiResponse[LoginResult])
async def local_session(session: AsyncSession = Depends(get_db)) -> ApiResponse[LoginResult]:
    """Issue a session for the active local administrator in single-user mode."""
    user = await ensure_local_administrator(session)
    if user is None:
        raise HTTPException(status_code=404, detail=bilingual("not_found"))
    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    return ApiResponse(
        data=LoginResult(
            access_token=token,
            expires_in=settings.jwt_expire_minutes * 60,
            user=serialize_user(user),
        ),
        message=bilingual("ok"),
    )


@router.post("/bootstrap", response_model=ApiResponse[LoginResult], status_code=201)
async def bootstrap(
    payload: SetupRequest, session: AsyncSession = Depends(get_db)
) -> ApiResponse[LoginResult]:
    """Create the first system administrator exactly once."""
    exists = await session.scalar(select(User.id).limit(1))
    if exists:
        raise HTTPException(status_code=409, detail=bilingual("setup_completed"))
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=UserRole.system_administrator,
    )
    session.add(user)
    await session.flush()
    await append_audit_log(
        session,
        actor_id=user.id,
        actor_role=user.role.value,
        action="identity.bootstrap_completed",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
    )
    await session.commit()
    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    return ApiResponse(
        data=LoginResult(
            access_token=token,
            expires_in=60 * 60,
            user=serialize_user(user),
        ),
        message=bilingual("setup_completed"),
    )


@router.post("/login", response_model=ApiResponse[LoginResult])
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db)
) -> ApiResponse[LoginResult]:
    user = await session.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail=bilingual("invalid_credentials"))
    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    await append_audit_log(
        session,
        actor_id=user.id,
        actor_role=user.role.value,
        action="identity.login",
        resource_type="user",
        resource_id=user.id,
        details=None,
    )
    await session.commit()
    return ApiResponse(
        data=LoginResult(
            access_token=token,
            expires_in=60 * 60,
            user=serialize_user(user),
        ),
        message=bilingual("ok"),
    )


@router.get("/me", response_model=ApiResponse[AuthUser])
async def me(
    actor: ActorContext = Depends(get_actor),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[AuthUser]:
    user = await session.get(User, actor.actor_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail=bilingual("auth_required"))
    return ApiResponse(data=serialize_user(user), message=bilingual("ok"))
