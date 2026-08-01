"""Internal, HTTP-level provider simulator used only by the Docker demo profile.

It implements the same multipart contracts configured for Agnes and a target
recognition provider.  This lets integration tests exercise networking, MinIO
objects, queueing, retry paths, result normalization and metrics without a
vendor credential.  It is not a face-recognition model and is never exposed by
the Compose file on a host port.
"""

from __future__ import annotations

import hashlib

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

app = FastAPI(title="Fair Bench local provider simulator", docs_url=None, redoc_url=None)

# Per-process state is sufficient for the local-only simulator.  It makes a
# small, deterministic cohort fail the first evaluation run, then succeed when
# the operator uses the product's failed-sample retry action.
_failure_attempts: dict[str, int] = {}


def _bucket(value: bytes) -> int:
    return int(hashlib.sha256(value).hexdigest()[:8], 16) % 100


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "local-simulator"}


@app.post("/v1/agnes/attributes")
async def attributes(image: UploadFile = File(...)) -> dict[str, object]:
    payload = await image.read()
    bucket = _bucket(payload or (image.filename or "sample").encode())
    return {
        "age_group": ["18-29", "30-44", "45-59", "60+"][bucket % 4],
        "gender": ["female", "male", "non_binary"][bucket % 3],
        "ethnicity": ["east_asian", "south_asian", "black", "white", "latino", "mena"][bucket % 6],
        "confidence": round(0.82 + (bucket % 15) / 100, 2),
    }


@app.post("/v1/face/recognize")
async def recognize(
    image: UploadFile = File(...), expected_identity: str = Form(default="")
) -> dict[str, object]:
    payload = await image.read()
    bucket = _bucket((image.filename or "sample").encode() + payload[:32])
    # The target client makes three attempts per sample.  Return 503 for all
    # three on the first run so the sample reaches the failed-sample panel;
    # the next operator-triggered retry then succeeds.
    if bucket < 6:
        sample_key = hashlib.sha256((image.filename or "sample").encode() + payload[:32]).hexdigest()
        attempts = _failure_attempts.get(sample_key, 0)
        if attempts < 3:
            _failure_attempts[sample_key] = attempts + 1
            raise HTTPException(status_code=503, detail="simulated upstream timeout")
    correct = bucket >= 18
    return {
        "predicted_identity": expected_identity if correct else f"simulated-mismatch-{bucket:02d}",
        "confidence": round(0.62 + (bucket % 35) / 100, 4),
        "is_correct": correct,
        "provider_trace": f"sim-{bucket:02d}",
    }
