from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "Fair Bench API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://fairbench:fairbench_dev_password@localhost:5432/fairbench"
    )
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "fairbench"
    minio_secret_key: str = "fairbench_minio_password"
    minio_bucket: str = "fairbench-assets"
    minio_secure: bool = False
    # Production can use any S3-compatible provider (Supabase Storage on the
    # free Render profile).  Empty S3 values intentionally fall back to the
    # MinIO settings above so the existing Compose workflow keeps working.
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True
    s3_auto_create_bucket: bool = True
    database_pool_size: int = 3
    database_max_overflow: int = 2
    worker_max_jobs: int = 4
    agnes_api_url: str = "https://api.example.com/v1/face-attributes"
    agnes_api_key: str = ""
    agnes_auth_scheme: str = "bearer"
    agnes_auth_header: str = "Authorization"
    agnes_provider_mode: str = "multipart_attributes"
    agnes_model: str = "agnes-2.0-flash"
    agnes_image_field: str = "image"
    agnes_response_age_path: str = "age_group"
    agnes_response_gender_path: str = "gender"
    agnes_response_ethnicity_path: str = "ethnicity"
    agnes_response_confidence_path: str = "confidence"
    agnes_timeout_seconds: float = 20.0
    agnes_max_retries: int = 3
    agnes_max_concurrency: int = 4
    api_secret_ttl_seconds: int = 86400
    max_upload_files: int = 200
    max_upload_file_bytes: int = 15 * 1024 * 1024
    seed_demo_data: bool = False
    demo_assets_path: str = "/demo_data/images"
    simulator_target_api_url: str = "http://simulator:8080/v1/face/recognize"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 60
    local_single_user_mode: bool = False
    local_admin_email: str = "local-admin@fairbench.local"
    local_admin_display_name: str = "Local Regulatory Administrator"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: str) -> str:
        """Accept managed PostgreSQL URLs while keeping SQLAlchemy async-native.

        Render exposes its internal connection string as ``postgresql://``.
        SQLAlchemy's async engine requires the ``postgresql+asyncpg://``
        dialect prefix, so normalize only plain PostgreSQL URLs here. Existing
        explicitly configured SQLAlchemy URLs remain untouched.
        """

        raw_url = str(value)
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql+asyncpg://" + raw_url.removeprefix(
                "postgres://"
            )
        elif raw_url.startswith("postgresql://"):
            raw_url = "postgresql+asyncpg://" + raw_url.removeprefix(
                "postgresql://"
            )

        # Managed PostgreSQL dashboards commonly emit libpq's ``sslmode``
        # parameter. asyncpg expects the equivalent parameter to be named
        # ``ssl``. Preserve every other query parameter unchanged.
        parts = urlsplit(raw_url)
        query = [
            ("ssl" if key == "sslmode" else key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
        return urlunsplit(parts._replace(query=urlencode(query)))

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def has_jwt_secret(self) -> bool:
        return len(self.jwt_secret) >= 32

    @property
    def storage_endpoint_url(self) -> str:
        if self.s3_endpoint_url:
            return self.s3_endpoint_url.rstrip("/")
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"

    @property
    def storage_access_key(self) -> str:
        return self.s3_access_key or self.minio_access_key

    @property
    def storage_secret_key(self) -> str:
        return self.s3_secret_key or self.minio_secret_key

    @property
    def storage_bucket(self) -> str:
        return self.s3_bucket or self.minio_bucket


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
