from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by all persistent entities."""


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    # Model import is intentionally local to avoid circular imports.
    import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if connection.dialect.name == "postgresql":
            # The first release used create_all().  These idempotent DDL statements
            # preserve existing audit records while upgrading local deployments.
            await connection.execute(
                text(
                    "ALTER TABLE sample_images "
                    "ADD COLUMN IF NOT EXISTS annotation_error TEXT"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE sample_images "
                    "ADD COLUMN IF NOT EXISTS checksum VARCHAR(64)"
                )
            )
            await connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_sample_images_checksum "
                    "ON sample_images (checksum)"
                )
            )
            await connection.execute(
                text(
                    "ALTER TABLE evaluation_tasks "
                    "ADD COLUMN IF NOT EXISTS target_api_config JSONB"
                )
            )
            # Defense in depth: even direct SQL clients cannot alter the audit trail.
            await connection.execute(
                text(
                    """
                    CREATE OR REPLACE FUNCTION fairbench_prevent_audit_mutation()
                    RETURNS trigger AS $$
                    BEGIN
                        RAISE EXCEPTION 'system_operation_logs is append-only';
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    DROP TRIGGER IF EXISTS trg_fairbench_audit_immutable
                    ON system_operation_logs
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE TRIGGER trg_fairbench_audit_immutable
                    BEFORE UPDATE OR DELETE ON system_operation_logs
                    FOR EACH ROW EXECUTE FUNCTION fairbench_prevent_audit_mutation()
                    """
                )
            )
