"""Adapter for externally hosted facial-recognition APIs.

The platform intentionally has no recognition model.  Each task stores a
non-secret contract mapping so a vendor's multipart field names and JSON shape
can be adapted without changing metric or audit code.  Secrets are supplied at
execution time from Redis only.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx


class TargetApiError(RuntimeError):
    def __init__(self, message: str, code: str = "TARGET_API_ERROR") -> None:
        super().__init__(message)
        self.code = code


def read_json_path(payload: Any, path: str | None) -> Any:
    """Read a safe dot-path such as ``result.face.identity`` from JSON."""
    if not path:
        return None
    value = payload
    for part in path.split("."):
        if not part or part.startswith("_") or not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _headers(api_key: str, config: dict[str, Any]) -> dict[str, str]:
    headers = {
        str(key): str(value)
        for key, value in (config.get("static_headers") or {}).items()
    }
    if not api_key or config.get("auth_scheme", "bearer") == "none":
        return headers
    header = str(config.get("auth_header_name") or "Authorization")
    if config.get("auth_scheme", "bearer") == "bearer":
        headers[header] = f"Bearer {api_key}"
    else:
        headers[header] = api_key
    return headers


def _safe_raw(payload: Any) -> dict[str, Any]:
    """Keep a bounded, JSON-only response record suitable for audit evidence."""
    if not isinstance(payload, dict):
        return {"response_type": type(payload).__name__}
    # Store no more than a shallow 20-field result record.  Face templates and
    # vendor diagnostics can be sensitive/large and are not needed for metrics.
    redacted = {key: value for key, value in payload.items() if key.lower() not in {
        "embedding", "template", "biometric_template", "image", "image_base64"
    }}
    return dict(list(redacted.items())[:20])


async def evaluate_sample(
    *,
    url: str,
    method: str,
    api_key: str,
    image_bytes: bytes,
    filename: str,
    content_type: str,
    ground_truth_identity: str | None,
    provider_config: dict[str, Any] | None,
) -> dict[str, Any]:
    """Send one actual HTTP multipart request and normalize the vendor result."""
    config = provider_config or {}
    started = time.perf_counter()
    data = {str(key): str(value) for key, value in (config.get("extra_form_fields") or {}).items()}
    identity_field = config.get("identity_field", "expected_identity")
    if identity_field:
        data[str(identity_field)] = ground_truth_identity or ""
    files = {
        str(config.get("image_field") or "image"): (
            filename,
            image_bytes,
            content_type or "application/octet-stream",
        )
    }
    attempts = int(config.get("max_retries", 2)) + 1
    timeout = float(config.get("timeout_seconds", 30))

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for attempt in range(attempts):
            try:
                response = await client.request(
                    method,
                    url,
                    headers=_headers(api_key, config),
                    files=files,
                    data=data,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < attempts - 1:
                        retry_after = response.headers.get("Retry-After")
                        try:
                            delay = min(float(retry_after or 0), 10)
                        except ValueError:
                            delay = 0
                        await asyncio.sleep(delay or 0.4 * (2**attempt))
                        continue
                    raise TargetApiError(
                        f"Target API returned HTTP {response.status_code}",
                        "UPSTREAM_RATE_LIMIT" if response.status_code == 429 else "UPSTREAM_UNAVAILABLE",
                    )
                if response.is_error:
                    raise TargetApiError(
                        f"Target API returned HTTP {response.status_code}",
                        f"HTTP_{response.status_code}",
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise TargetApiError("Target API did not return JSON", "INVALID_RESPONSE") from exc
                predicted = read_json_path(
                    payload, str(config.get("response_identity_path") or "predicted_identity")
                )
                confidence_raw = read_json_path(payload, config.get("response_confidence_path", "confidence"))
                explicit_correct = read_json_path(payload, config.get("response_correct_path", "is_correct"))
                try:
                    confidence = float(confidence_raw) if confidence_raw is not None else 0.0
                except (TypeError, ValueError) as exc:
                    raise TargetApiError("Target confidence is not numeric", "INVALID_RESPONSE") from exc
                return {
                    "predicted_identity": str(predicted) if predicted is not None else None,
                    "confidence": confidence,
                    "is_correct": bool(explicit_correct)
                    if explicit_correct is not None
                    else predicted == ground_truth_identity,
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "raw": _safe_raw(payload),
                }
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < attempts - 1:
                    await asyncio.sleep(0.4 * (2**attempt))
                    continue
                raise TargetApiError("Target API network timeout", "UPSTREAM_TIMEOUT") from exc

    raise TargetApiError("Target API request failed", "TARGET_API_ERROR")
