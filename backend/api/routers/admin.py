
from __future__ import annotations

import asyncio
import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from api.deps import REPORT_FILTER_PARAMS, SessionDep, build_report_filters, require_role
from shared import search
from shared.config import settings
from shared.logging import q, setup_logging
from shared.models import AdminUser, AuditLog, IngestRun, Report, SourceConfig
from shared.redis_client import get_counters
from shared.schemas import (
    BulkVerificationIn,
    PageMeta,
    ReportOut,
    ReportPage,
    SourcePatchIn,
    VerificationIn,
)

log = setup_logging("api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

reviewer_dep = require_role("reviewer")
admin_dep = require_role("admin")


async def _reindex(row: Report) -> None:
    doc = search.to_doc(row)

    def _run() -> None:
        search.ensure_index()
        search.index_report(doc)

    try:
        await asyncio.to_thread(_run)
    except Exception as exc:
        log.warning(q(f"[admin] reindex failed for {row.id}: {exc}"))


def _audit(
    session: Any,
    user: AdminUser,
    action: str,
    entity: str,
    entity_id: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    session.add(
        AuditLog(
            user_id=user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before=before,
            after=after,
        )
    )


@router.get("/reports", response_model=ReportPage)
async def admin_reports(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    date_from: Annotated[str | None, REPORT_FILTER_PARAMS["date_from"]] = None,
    date_to: Annotated[str | None, REPORT_FILTER_PARAMS["date_to"]] = None,
    state: Annotated[str | None, REPORT_FILTER_PARAMS["state"]] = None,
    category: Annotated[str | None, REPORT_FILTER_PARAMS["category"]] = None,
    source: Annotated[str | None, REPORT_FILTER_PARAMS["source"]] = None,
    verification_status: Annotated[
        str | None, REPORT_FILTER_PARAMS["verification_status"]
    ] = "pending",
    include_duplicates: Annotated[bool, REPORT_FILTER_PARAMS["include_duplicates"]] = True,
    min_credibility: Annotated[float | None, REPORT_FILTER_PARAMS["min_credibility"]] = None,
) -> ReportPage:
    _ = user
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        category=category,
        source=source,
        verification_status=verification_status,
        include_duplicates=include_duplicates,
        min_credibility=min_credibility,
    )
    total = (
        await session.execute(select(func.count()).select_from(Report).where(*clauses))
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(Report)
                .where(*clauses)
                .order_by(Report.observed_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return ReportPage(
        items=[ReportOut.model_validate(r, from_attributes=True) for r in rows],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=int(total),
            pages=(int(total) + page_size - 1) // page_size,
        ),
    )


@router.patch("/reports/{report_id}/verification", response_model=ReportOut)
async def set_verification(
    report_id: uuid.UUID,
    body: VerificationIn,
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
) -> ReportOut:
    row = await session.get(Report, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    before = {
        "verification_status": row.verification_status,
        "verification_note": row.verification_note,
    }
    row.verification_status = body.status
    row.verification_note = body.note
    row.verified_by = user.id
    row.verified_at = datetime.now(UTC)
    _audit(
        session,
        user,
        action=f"verification:{body.status}",
        entity="report",
        entity_id=str(report_id),
        before=before,
        after={"verification_status": body.status, "verification_note": body.note},
    )
    await session.commit()
    await _reindex(row)
    log.info(q(f"[admin] {user.email} set {report_id} -> {body.status}"))
    return ReportOut.model_validate(row, from_attributes=True)


@router.post("/reports/bulk-verification")
async def bulk_verification(
    body: BulkVerificationIn,
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
) -> dict[str, Any]:
    updated: list[str] = []
    missing: list[str] = []
    for rid in body.ids:
        row = await session.get(Report, rid)
        if row is None:
            missing.append(str(rid))
            continue
        row.verification_status = body.status
        row.verification_note = body.note
        row.verified_by = user.id
        row.verified_at = datetime.now(UTC)
        updated.append(str(rid))
    _audit(
        session,
        user,
        action=f"bulk_verification:{body.status}",
        entity="reports",
        entity_id=",".join(updated[:50]),
        before=None,
        after={"ids": updated, "note": body.note},
    )
    await session.commit()
    log.info(q(f"[admin] {user.email} bulk {body.status} on {len(updated)} reports"))
    return {
        "updated": len(updated),
        "missing": missing,
        "status": body.status,
    }


async def _consumer_lag() -> dict[str, Any]:
    from aiokafka import AIOKafkaConsumer
    from aiokafka.admin import AIOKafkaAdminClient
    from aiokafka.structs import TopicPartition

    from shared import topics as T

    groups = ["pipeline-enrich", "pipeline-dedup", "pipeline-classify", "pipeline-sink"]
    try:
        async with asyncio.timeout(8):
            committed: dict[str, dict[str, int]] = {}
            admin = AIOKafkaAdminClient(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )
            await admin.start()
            try:
                for group in groups:
                    offsets = await admin.list_consumer_group_offsets(group)
                    committed[group] = {
                        f"{tp.topic}:{tp.partition}": int(getattr(off, "offset", off))
                        for tp, off in (offsets or {}).items()
                    }
            finally:
                await admin.close()

            consumer = AIOKafkaConsumer(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )
            await consumer.start()
            try:
                ends: dict[TopicPartition, int] = {}
                for topic in T.ALL_TOPICS:
                    tps = [TopicPartition(topic, p) for p in range(T.PARTITIONS)]
                    ends.update(await consumer.end_offsets(tps))
            finally:
                await consumer.stop()

            lag: dict[str, int] = {}
            for group, offs in committed.items():
                total = 0
                for key, offset in offs.items():
                    topic, _, partition = key.rpartition(":")
                    tp = TopicPartition(topic, int(partition))
                    end = ends.get(tp)
                    if end is not None and end > offset:
                        total += end - offset
                lag[group] = total
            return {"available": True, "lag": lag, "sum": sum(lag.values())}
    except Exception as exc:
        return {"available": False, "error": type(exc).__name__, "lag": {}, "sum": 0}


@router.get("/pipeline")
async def pipeline_health(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
) -> dict[str, Any]:
    _ = user
    counters = await get_counters()
    lag = await _consumer_lag()
    recent = (
        (
            await session.execute(
                select(IngestRun)
                .order_by(IngestRun.started_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    return {
        "counters": counters,
        "kafka": lag,
        "stages": ["enrich", "dedup", "classify", "sink"],
        "recent_runs": [
            {
                "source": r.source,
                "status": r.status,
                "fetched": r.fetched,
                "published": r.published,
                "errors": r.errors,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in recent
        ],
        "computed_at": datetime.now(UTC).isoformat(),
    }


@router.get("/ingest-runs")
async def ingest_runs(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
    source: Annotated[str | None, Query(max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict[str, Any]:
    _ = user
    stmt = select(IngestRun).order_by(IngestRun.started_at.desc()).limit(limit)
    if source:
        stmt = stmt.where(IngestRun.source == source)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "runs": [
            {
                "id": str(r.id),
                "source": r.source,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "fetched": r.fetched,
                "published": r.published,
                "duplicates": r.duplicates,
                "errors": r.errors,
                "last_error": r.last_error,
            }
            for r in rows
        ]
    }


@router.get("/sources")
async def list_sources(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
) -> dict[str, Any]:
    _ = user
    rows = (await session.execute(select(SourceConfig))).scalars().all()
    return {
        "sources": [
            {
                "name": r.name,
                "enabled": r.enabled,
                "interval_seconds": r.interval_seconds,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    }


@router.patch("/sources/{name}")
async def patch_source(
    name: str,
    body: SourcePatchIn,
    session: SessionDep,
    user: Annotated[AdminUser, Depends(admin_dep)],
) -> dict[str, Any]:
    row = await session.get(SourceConfig, name)
    if row is None:
        raise HTTPException(status_code=404, detail="unknown source")
    before = {"enabled": row.enabled, "interval_seconds": row.interval_seconds}
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.interval_seconds is not None:
        row.interval_seconds = body.interval_seconds
    _audit(
        session,
        user,
        action="source_patch",
        entity="source_config",
        entity_id=name,
        before=before,
        after={"enabled": row.enabled, "interval_seconds": row.interval_seconds},
    )
    await session.commit()
    log.info(
        q(
            f"[admin] {user.email} patched source {name}: {before} -> "
            f"{body.model_dump(exclude_none=True)}"
        )
    )
    return {"name": name, "enabled": row.enabled, "interval_seconds": row.interval_seconds}


@router.get("/audit")
async def audit_log(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    action: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, Any]:
    _ = user
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "entries": [
            {
                "id": r.id,
                "user_id": str(r.user_id) if r.user_id else None,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "before": r.before,
                "after": r.after,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


EXPORT_COLUMNS = [
    "id",
    "source",
    "external_id",
    "observed_at",
    "ingested_at",
    "state",
    "city",
    "district",
    "lat",
    "lon",
    "event_category",
    "severity",
    "confidence",
    "credibility_score",
    "verification_status",
    "is_duplicate",
    "lang",
    "author",
    "source_url",
    "text",
]


@router.get("/export")
async def export_csv(
    session: SessionDep,
    user: Annotated[AdminUser, Depends(reviewer_dep)],
    format: Annotated[str, Query(pattern="^(csv|json)$")] = "csv",
    date_from: Annotated[str | None, REPORT_FILTER_PARAMS["date_from"]] = None,
    date_to: Annotated[str | None, REPORT_FILTER_PARAMS["date_to"]] = None,
    state: Annotated[str | None, REPORT_FILTER_PARAMS["state"]] = None,
    category: Annotated[str | None, REPORT_FILTER_PARAMS["category"]] = None,
    source: Annotated[str | None, REPORT_FILTER_PARAMS["source"]] = None,
    verification_status: Annotated[
        str | None, REPORT_FILTER_PARAMS["verification_status"]
    ] = None,
    include_duplicates: Annotated[bool, REPORT_FILTER_PARAMS["include_duplicates"]] = False,
    limit: Annotated[int, Query(ge=1, le=50000)] = 10000,
) -> Any:
    _ = user
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        category=category,
        source=source,
        verification_status=verification_status,
        include_duplicates=include_duplicates,
    )
    rows = (
        (
            await session.execute(
                select(Report)
                .where(*clauses)
                .order_by(Report.observed_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    def _cell(r: Report, col: str) -> Any:
        v = getattr(r, col)
        if isinstance(v, datetime):
            return v.isoformat()
        if col == "text" and isinstance(v, str):
            return v.replace("\n", " ").replace("\r", " ")
        return v

    if format == "json":
        payload = [{c: _cell(r, c) for c in EXPORT_COLUMNS} for r in rows]
        from fastapi.responses import JSONResponse

        return JSONResponse({"items": payload, "count": len(payload)})

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_COLUMNS)
    for r in rows:
        writer.writerow([_cell(r, c) for c in EXPORT_COLUMNS])
    csv_bytes = buf.getvalue()
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    log.info(q(f"[admin] {user.email} exported {len(rows)} rows"))
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="vaayu_export_{stamp}.csv"'},
    )
