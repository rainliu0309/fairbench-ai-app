from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Message(BaseModel):
    zh: str
    en: str


class ApiResponse(BaseModel, Generic[T]):
    data: T
    message: Message


class SetupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=200)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("A valid email address is required")
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class AuthUser(BaseModel):
    id: str
    email: str
    display_name: str
    role: str


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)


class DatasetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: str
    sample_count: int
    is_demo: bool
    created_at: datetime


class SampleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    filename: str
    content_type: str
    ground_truth_identity: str | None
    agnes_labels: dict[str, Any] | None
    manual_labels: dict[str, Any] | None
    effective_labels: dict[str, Any] | None
    label_source: str
    label_status: str
    annotation_error: str | None = None
    preview_url: str | None = None
    created_at: datetime


class LabelUpdate(BaseModel):
    age_group: str = Field(min_length=1, max_length=50)
    gender: str = Field(min_length=1, max_length=50)
    ethnicity: str = Field(min_length=1, max_length=80)
    ground_truth_identity: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=3, max_length=500)


class TargetApiConfig(BaseModel):
    """Non-secret vendor contract mapping stored with an evaluation task.

    A key itself is deliberately absent: it is accepted once in ``api_key`` and
    held only in Redis for the configured task-secret TTL.
    """

    auth_scheme: str = Field(default="bearer", pattern="^(bearer|header|none)$")
    auth_header_name: str = Field(default="Authorization", min_length=1, max_length=100)
    image_field: str = Field(default="image", min_length=1, max_length=100)
    identity_field: str | None = Field(default="expected_identity", max_length=100)
    extra_form_fields: dict[str, str] = Field(default_factory=dict)
    static_headers: dict[str, str] = Field(default_factory=dict)
    response_identity_path: str = Field(default="predicted_identity", min_length=1, max_length=200)
    response_confidence_path: str | None = Field(default="confidence", max_length=200)
    response_correct_path: str | None = Field(default="is_correct", max_length=200)
    timeout_seconds: float = Field(default=30, ge=1, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)


class TaskCreate(BaseModel):
    dataset_id: str
    name: str = Field(min_length=2, max_length=180)
    algorithm_name: str = Field(min_length=2, max_length=160)
    target_api_url: str = Field(min_length=3, max_length=1024)
    target_api_method: str = "POST"
    api_key: str = Field(default="", max_length=2048)
    provider_config: TargetApiConfig = Field(default_factory=TargetApiConfig)
    fairness_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    language: str = Field(default="zh", pattern="^(zh|en)$")

    @field_validator("target_api_method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        method = value.upper()
        if method not in {"POST", "PUT"}:
            raise ValueError("Only POST and PUT are supported")
        return method

    @field_validator("target_api_url")
    @classmethod
    def reject_secrets_in_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Target API URL must use HTTP or HTTPS")
        sensitive_keys = {"api_key", "apikey", "key", "token", "secret"}
        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be embedded in the URL")
        if sensitive_keys.intersection(key.lower() for key in parse_qs(parsed.query)):
            raise ValueError("Secrets must be submitted through the api_key field")
        return value


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    name: str
    algorithm_name: str
    target_api_url: str
    target_api_method: str
    target_api_config: dict[str, Any] | None
    status: str
    progress: int
    fairness_threshold: float
    language: str
    metrics: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class FailedSample(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    sample_id: str
    status: str
    error_code: str | None
    error_message: str | None
    retry_count: int
    updated_at: datetime


class RetryFailedRequest(BaseModel):
    api_key: str = Field(default="", max_length=2048)


class ReportCreate(BaseModel):
    task_id: str
    language: str = Field(default="zh", pattern="^(zh|en)$")
    title: str = Field(min_length=2, max_length=240)
    include_failed_samples: bool = True
    include_methodology: bool = True
    issuing_authority: str = Field(default="Public AI Regulatory Authority", max_length=240)
    signer: str = Field(default="Regulatory Reviewer", max_length=160)


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    report_no: str
    title: str
    language: str
    parameters: dict[str, Any] | None
    checksum: str
    created_at: datetime


class AuditLogSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    occurred_at: datetime
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    request_id: str | None
    details: dict[str, Any] | None
    entry_hash: str
