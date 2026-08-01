from arq.connections import RedisSettings

from core.config import Settings


def test_managed_postgres_url_is_async_and_uses_asyncpg_ssl_parameter():
    configured = Settings(
        database_url=(
            "postgresql://regulator:encoded-password@pooler.example.com:5432/"
            "fairbench?sslmode=require"
        )
    )

    assert configured.database_url == (
        "postgresql+asyncpg://regulator:encoded-password@pooler.example.com:5432/"
        "fairbench?ssl=require"
    )


def test_s3_settings_override_local_minio_without_removing_fallback():
    managed = Settings(
        s3_endpoint_url="https://project.storage.supabase.co/storage/v1/s3/",
        s3_access_key="managed-access",
        s3_secret_key="managed-secret",
        s3_bucket="fairbench-assets",
    )
    local = Settings()

    assert managed.storage_endpoint_url.endswith("/storage/v1/s3")
    assert managed.storage_access_key == "managed-access"
    assert managed.storage_secret_key == "managed-secret"
    assert managed.storage_bucket == "fairbench-assets"
    local_scheme = "https" if local.minio_secure else "http"
    assert local.storage_endpoint_url == f"{local_scheme}://{local.minio_endpoint}"
    assert local.storage_bucket == local.minio_bucket


def test_upstash_tls_redis_url_is_supported_by_arq():
    redis = RedisSettings.from_dsn(
        "rediss://default:temporary-value@sample.upstash.io:6379"
    )

    assert redis.ssl is True
