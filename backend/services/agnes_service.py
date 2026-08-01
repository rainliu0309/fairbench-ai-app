"""Configurable adapter for the external Agnes demographic-label API."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import httpx

from core.config import settings
from services.target_api_service import read_json_path


class AgnesServiceError(RuntimeError):
    pass


REQUIRED_LABELS = ("age_group", "gender", "ethnicity")
VALID_LABELS = {
    "age_group": {"18-29", "30-44", "45-59", "60+"},
    "gender": {"female", "male", "non_binary"},
    "ethnicity": {"east_asian", "south_asian", "black", "white", "latino", "mena"},
}


class AgnesService:
    """Bounded-concurrency API client with retry handling for 429/5xx failures."""

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.agnes_max_concurrency)

    def _headers(self) -> dict[str, str]:
        if settings.agnes_auth_scheme == "none":
            return {}
        if not settings.agnes_api_key:
            raise AgnesServiceError("Agnes API key is not configured")
        value = (
            f"Bearer {settings.agnes_api_key}"
            if settings.agnes_auth_scheme == "bearer"
            else settings.agnes_api_key
        )
        return {settings.agnes_auth_header: value}

    def _multipart_labels(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "age_group": read_json_path(payload, settings.agnes_response_age_path),
            "gender": read_json_path(payload, settings.agnes_response_gender_path),
            "ethnicity": read_json_path(payload, settings.agnes_response_ethnicity_path),
            "confidence": read_json_path(payload, settings.agnes_response_confidence_path),
        }

    def _vision_request(self, image_bytes: bytes, content_type: str) -> dict[str, Any]:
        data_url = "data:{};base64,{}".format(
            content_type or "image/jpeg",
            base64.b64encode(image_bytes).decode("ascii"),
        )
        instruction = (
            "Review this one authorized fairness-evaluation sample. Do not identify the person. "
            "Return only a JSON object using exactly these keys and literal values: "
            '{"age_group":"18-29|30-44|45-59|60+",'
            '"gender":"female|male|non_binary",'
            '"ethnicity":"east_asian|south_asian|black|white|latino|mena",'
            '"confidence":0.0}. '
            "Use confidence from 0 to 1. Do not include markdown or explanatory text."
        )
        return {
            "model": settings.agnes_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You return compact, machine-readable JSON only."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        }

    def _vision_labels(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AgnesServiceError("Agnes response did not include a chat completion") from exc
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise AgnesServiceError("Agnes returned a non-text annotation response")
        source = content.strip()
        if source.startswith("```"):
            source = source.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            decoded = json.loads(source)
        except json.JSONDecodeError as exc:
            raise AgnesServiceError("Agnes did not return JSON labels") from exc
        if not isinstance(decoded, dict):
            raise AgnesServiceError("Agnes JSON labels must be an object")
        return decoded

    def _validated_labels(self, labels: dict[str, Any]) -> dict[str, Any]:
        if not all(labels.get(key) is not None for key in REQUIRED_LABELS):
            raise AgnesServiceError("Invalid Agnes response schema")
        normalized = {key: str(labels[key]).strip().lower() for key in REQUIRED_LABELS}
        for key, allowed in VALID_LABELS.items():
            if normalized[key] not in allowed:
                raise AgnesServiceError(f"Agnes returned an unsupported {key} label")
        try:
            confidence = float(labels.get("confidence", 0))
        except (TypeError, ValueError) as exc:
            raise AgnesServiceError("Invalid Agnes confidence") from exc
        if not 0 <= confidence <= 1:
            raise AgnesServiceError("Agnes confidence must be between 0 and 1")
        return {**normalized, "confidence": confidence}

    async def annotate(
        self, image_bytes: bytes, content_type: str, filename: str = "sample"
    ) -> dict[str, Any]:
        attempts = settings.agnes_max_retries
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=settings.agnes_timeout_seconds) as client:
                for attempt in range(attempts):
                    try:
                        if settings.agnes_provider_mode == "openai_vision":
                            response = await client.post(
                                settings.agnes_api_url,
                                headers={**self._headers(), "Content-Type": "application/json"},
                                json=self._vision_request(image_bytes, content_type),
                            )
                        else:
                            response = await client.post(
                                settings.agnes_api_url,
                                headers=self._headers(),
                                files={settings.agnes_image_field: (filename, image_bytes, content_type)},
                            )
                        if response.status_code == 429 or response.status_code >= 500:
                            if attempt < attempts - 1:
                                await asyncio.sleep(0.5 * (2**attempt))
                                continue
                            code = "rate limit" if response.status_code == 429 else "unavailable"
                            raise AgnesServiceError(f"Agnes service {code}")
                        if response.is_error:
                            raise AgnesServiceError(f"Agnes returned HTTP {response.status_code}")
                        try:
                            payload = response.json()
                        except ValueError as exc:
                            raise AgnesServiceError("Agnes did not return JSON") from exc
                        labels = (
                            self._vision_labels(payload)
                            if settings.agnes_provider_mode == "openai_vision"
                            else self._multipart_labels(payload)
                        )
                        return self._validated_labels(labels)
                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        if attempt < attempts - 1:
                            await asyncio.sleep(0.5 * (2**attempt))
                            continue
                        raise AgnesServiceError("Agnes network timeout") from exc
        raise AgnesServiceError("Agnes annotation failed")


agnes_service = AgnesService()
