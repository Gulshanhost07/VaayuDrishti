
from __future__ import annotations

import asyncio
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from api.deps import SessionDep, client_ip
from shared import objectstore
from shared.config import settings
from shared.logging import q, setup_logging
from shared.models import CitizenToken, Report
from shared.redis_client import RateLimiter
from shared.schemas import CitizenReportIn, CitizenSubmitOut

log = setup_logging("api.citizen")

router = APIRouter(prefix="/citizen", tags=["citizen"])

submit_limiter = RateLimiter(
    "citizen_submit", limit=settings.citizen_rate_limit_per_hour, window_seconds=3600
)
_URL_COUNT = re.compile(r"https?://", re.IGNORECASE)
_FORM_KEYS = ("text", "city", "state", "lat", "lon", "event_category")


def _validate(body: CitizenReportIn) -> CitizenReportIn:
    if len(_URL_COUNT.findall(body.text)) > 4:
        raise HTTPException(status_code=422, detail="too many links in submission")
    if "<script" in body.text.lower():
        raise HTTPException(status_code=422, detail="invalid content")
    return body


async def _save_upload(file: Any, external_prefix: str) -> dict[str, Any]:
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype not in objectstore.ALLOWED_IMAGE:
        raise HTTPException(status_code=422, detail="only images (jpg/png/webp/gif) allowed")
    data = await file.read(settings.media_max_image_bytes + 1)
    if len(data) > settings.media_max_image_bytes:
        raise HTTPException(status_code=413, detail="image too large (max 10 MB)")
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    key = objectstore.media_key(external_prefix, ctype, data)
    await asyncio.to_thread(objectstore.put_bytes, key, data, ctype)
    return {
        "bucket": settings.minio_bucket,
        "key": key,
        "content_type": ctype,
        "sha256": objectstore.sha256(data),
        "size": len(data),
        "source_url": None,
    }


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="invalid coordinate") from None


async def _load_body(request: Request) -> tuple[CitizenReportIn, Any]:
    ctype = (request.headers.get("content-type") or "").lower()
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        raw: dict[str, Any] = {k: form.get(k) for k in _FORM_KEYS}
        if not raw.get("text"):
            raise HTTPException(status_code=422, detail="text is required")
        for key in ("city", "state", "event_category"):
            if raw.get(key) == "":
                raw[key] = None
        raw["lat"] = _parse_float(raw.get("lat"))
        raw["lon"] = _parse_float(raw.get("lon"))
        upload = form.get("file")
        if upload is not None and not hasattr(upload, "read"):
            upload = None
        return _validate_body(raw), upload
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="JSON body expected") from exc
    return _validate_body(payload), None


def _validate_body(payload: Any) -> CitizenReportIn:
    try:
        return CitizenReportIn.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(include_url=False),
        ) from exc


@router.post("/reports", response_model=CitizenSubmitOut, status_code=status.HTTP_201_CREATED)
async def submit_report(request: Request, session: SessionDep) -> CitizenSubmitOut:
    ip = client_ip(request)
    if not await submit_limiter.allow(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"limit {settings.citizen_rate_limit_per_hour} submissions/hour",
        )

    body, upload = await _load_body(request)
    body = _validate(body)

    report_id = uuid.uuid4()
    media: list[dict[str, Any]] = []
    if upload is not None:
        media.append(await _save_upload(upload, f"citizen/{report_id}"))

    token = secrets.token_urlsafe(32)
    row = Report(
        id=report_id,
        source="citizen",
        external_id=str(report_id),
        text=body.text,
        city=body.city,
        state=body.state,
        lat=body.lat,
        lon=body.lon,
        event_category=body.event_category,
        observed_at=datetime.now(UTC),
        media=media,
        raw={"citizen_pending_publish": True, "submitted_ip": ip},
    )
    session.add(row)
    try:
        await session.flush()
        session.add(CitizenToken(report_id=report_id, token=token))
        await session.flush()
        await session.commit()
    except Exception as exc:
        await session.rollback()
        log.warning(q(f"[citizen] insert failed: {exc}"))
        raise HTTPException(status_code=400, detail="submission rejected") from exc

    log.info(q(f"[citizen] report {report_id} accepted from {ip}"))
    return CitizenSubmitOut(
        id=report_id,
        token=token,
        tracking_path=f"/api/v1/reports/track/{token}",
        status="pending",
    )
