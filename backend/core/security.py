import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from redis.asyncio import Redis

from core.config import settings

password_hash = PasswordHash.recommended()


class TokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(*, user_id: str, email: str, role: str) -> str:
    if not settings.has_jwt_secret:
        raise TokenError("JWT_SECRET must contain at least 32 characters")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "email": email, "role": role, "exp": expires_at, "type": "access"},
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict[str, Any]:
    if not settings.has_jwt_secret:
        raise TokenError("JWT authentication is not configured")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired access token") from exc
    if payload.get("type") != "access" or not all(payload.get(key) for key in ("sub", "email", "role")):
        raise TokenError("Invalid access token claims")
    return payload


def secret_fingerprint(secret: str) -> str:
    """Create a non-reversible fingerprint suitable for audit correlation."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


async def cache_task_secret(task_id: str, secret: str) -> None:
    """Store credentials only in volatile Redis with an explicit TTL."""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.setex(
            f"fairbench:task-secret:{task_id}",
            settings.api_secret_ttl_seconds,
            secret,
        )
    finally:
        await redis.aclose()


async def get_task_secret(task_id: str) -> str | None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        return await redis.get(f"fairbench:task-secret:{task_id}")
    finally:
        await redis.aclose()


async def clear_task_secret(task_id: str) -> None:
    """Remove a volatile target credential when its task is explicitly purged."""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.delete(f"fairbench:task-secret:{task_id}")
    finally:
        await redis.aclose()
