
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select

from api.deps import REPORT_FILTER_PARAMS, SessionDep, build_report_filters
from shared import objectstore
from shared.logging import setup_logging
from shared.models import CitizenToken, Report
from shared.schemas import PageMeta, ReportDetailOut, ReportOut, ReportPage, TrackOut

log = setup_logging("api.reports")

router = APIRouter(tags=["reports"])


async def _query_reports(
    session: Any,
    clauses: list[Any],
    page: int,
    page_size: int,
    order_by: Any,
) -> tuple[list[Report], int]:
    total = (
        await session.execute(select(func.count()).select_from(Report).where(*clauses))
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(Report)
                .where(*clauses)
                .order_by(order_by)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


@router.get("/reports", response_model=ReportPage)
async def list_reports(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: Annotated[str, Query(pattern="^(observed_at|ingested_at|credibility_score)$")] = "observed_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    date_from: Annotated[str | None, REPORT_FILTER_PARAMS["date_from"]] = None,
    date_to: Annotated[str | None, REPORT_FILTER_PARAMS["date_to"]] = None,
    state: Annotated[str | None, REPORT_FILTER_PARAMS["state"]] = None,
    city: Annotated[str | None, REPORT_FILTER_PARAMS["city"]] = None,
    category: Annotated[str | None, REPORT_FILTER_PARAMS["category"]] = None,
    source: Annotated[str | None, REPORT_FILTER_PARAMS["source"]] = None,
    verification_status: Annotated[
        str | None, REPORT_FILTER_PARAMS["verification_status"]
    ] = None,
    lang: Annotated[str | None, REPORT_FILTER_PARAMS["lang"]] = None,
    include_duplicates: Annotated[bool, REPORT_FILTER_PARAMS["include_duplicates"]] = False,
    min_credibility: Annotated[float | None, REPORT_FILTER_PARAMS["min_credibility"]] = None,
) -> ReportPage:
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        city=city,
        category=category,
        source=source,
        verification_status=verification_status,
        lang=lang,
        include_duplicates=include_duplicates,
        min_credibility=min_credibility,
    )
    col = getattr(Report, sort)
    order_by = col.asc() if order == "asc" else col.desc()
    rows, total = await _query_reports(session, clauses, page, page_size, order_by)
    return ReportPage(
        items=[ReportOut.model_validate(r, from_attributes=True) for r in rows],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            pages=(total + page_size - 1) // page_size if page_size else 0,
        ),
    )


@router.get("/reports/search", response_model=ReportPage)
async def search_reports(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    date_from: Annotated[str | None, REPORT_FILTER_PARAMS["date_from"]] = None,
    date_to: Annotated[str | None, REPORT_FILTER_PARAMS["date_to"]] = None,
    state: Annotated[str | None, REPORT_FILTER_PARAMS["state"]] = None,
    category: Annotated[str | None, REPORT_FILTER_PARAMS["category"]] = None,
    source: Annotated[str | None, REPORT_FILTER_PARAMS["source"]] = None,
    include_duplicates: Annotated[bool, REPORT_FILTER_PARAMS["include_duplicates"]] = False,
) -> ReportPage:
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        category=category,
        source=source,
        include_duplicates=include_duplicates,
    )
    ids = await _search_ids(q, page * page_size)
    if ids:
        rows = (
            (
                await session.execute(
                    select(Report).where(Report.id.in_(ids)).where(*clauses)
                )
            )
            .scalars()
            .all()
        )
        by_id = {r.id: r for r in rows}
        ordered = [by_id[i] for i in ids if i in by_id]
        total = len(ordered)
        ordered = ordered[(page - 1) * page_size : page * page_size]
    else:
        from sqlalchemy import or_

        like = f"%{q}%"
        fts_clauses = [
            *clauses,
            or_(
                Report.text.ilike(like),
                func.coalesce(func.array_to_string(Report.hashtags, " "), "").ilike(like),
                func.coalesce(Report.city, "").ilike(like),
                func.coalesce(Report.state, "").ilike(like),
            ),
        ]
        ordered, total = await _query_reports(
            session, fts_clauses, page, page_size, Report.observed_at.desc()
        )
    return ReportPage(
        items=[ReportOut.model_validate(r, from_attributes=True) for r in ordered],
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            pages=(total + page_size - 1) // page_size if page_size else 0,
        ),
    )


async def _search_ids(q: str, size: int) -> list[uuid.UUID]:
    try:
        import asyncio

        from shared import search as S

        def _run() -> list[uuid.UUID]:
            client = S.client()
            body = {
                "size": size,
                "query": {
                    "multi_match": {
                        "query": q,
                        "fields": ["text^2", "hashtags", "city", "state", "author"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                },
            }
            resp = client.search(index=S.INDEX, body=body)
            out: list[uuid.UUID] = []
            for hit in resp.get("hits", {}).get("hits", []):
                try:
                    out.append(uuid.UUID(hit["_id"]))
                except (ValueError, KeyError):
                    continue
            return out

        return await asyncio.to_thread(_run)
    except Exception as exc:
        log.debug(f"[search] opensearch unavailable, fallback: {type(exc).__name__}")
        return []


@router.get("/reports/track/{token}", response_model=TrackOut)
async def track(token: str, session: SessionDep) -> TrackOut:
    res = await session.execute(
        select(Report)
        .join(CitizenToken, CitizenToken.report_id == Report.id)
        .where(CitizenToken.token == token)
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown tracking token")
    return TrackOut(
        id=row.id,
        verification_status=row.verification_status,
        verification_note=row.verification_note,
        observed_at=row.observed_at,
        city=row.city,
        state=row.state,
        event_category=row.event_category,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
async def get_report(report_id: uuid.UUID, session: SessionDep) -> ReportDetailOut:
    row = await session.get(Report, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    return ReportDetailOut.model_validate(row, from_attributes=True)


@router.get("/reports/{report_id}/media/{key:path}")
async def get_media(report_id: uuid.UUID, key: str, session: SessionDep) -> Response:
    row = await session.get(Report, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    refs = row.media or []
    match = next((m for m in refs if isinstance(m, dict) and m.get("key") == key), None)
    if match is None:
        raise HTTPException(status_code=404, detail="media not found on this report")

    def _load() -> bytes | None:
        return objectstore.get_bytes(key)

    import asyncio

    data = await asyncio.to_thread(_load)
    if data is None:
        raise HTTPException(status_code=404, detail="media object missing")
    return Response(
        content=data,
        media_type=match.get("content_type") or "application/octet-stream",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Disposition": f'inline; filename="{key.rsplit("/", 1)[-1]}"',
        },
    )
