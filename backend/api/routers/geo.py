
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text

from api.deps import REPORT_FILTER_PARAMS, SessionDep, build_report_filters
from shared.models import Report

router = APIRouter(prefix="/geo", tags=["geo"])


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(p) for p in bbox.split(",")]
    except ValueError as exc:
        raise ValueError("bbox must be minlon,minlat,maxlon,maxlat") from exc
    if len(parts) != 4:
        raise ValueError("bbox must be minlon,minlat,maxlon,maxlat")
    minlon, minlat, maxlon, maxlat = parts
    if not (-180 <= minlon <= 180 and -180 <= maxlon <= 180):
        raise ValueError("longitude out of range")
    if not (-90 <= minlat <= 90 and -90 <= maxlat <= 90):
        raise ValueError("latitude out of range")
    return minlon, minlat, maxlon, maxlat


@router.get("/reports.geojson")
async def reports_geojson(
    session: SessionDep,
    bbox: Annotated[str | None, Query(description="minlon,minlat,maxlon,maxlat")] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[float | None, Query(gt=0, le=2000)] = None,
    limit: Annotated[int, Query(ge=1, le=20000)] = 2000,
    date_from: Annotated[str | None, REPORT_FILTER_PARAMS["date_from"]] = None,
    date_to: Annotated[str | None, REPORT_FILTER_PARAMS["date_to"]] = None,
    state: Annotated[str | None, REPORT_FILTER_PARAMS["state"]] = None,
    city: Annotated[str | None, REPORT_FILTER_PARAMS["city"]] = None,
    category: Annotated[str | None, REPORT_FILTER_PARAMS["category"]] = None,
    source: Annotated[str | None, REPORT_FILTER_PARAMS["source"]] = None,
    verification_status: Annotated[
        str | None, REPORT_FILTER_PARAMS["verification_status"]
    ] = None,
    include_duplicates: Annotated[bool, REPORT_FILTER_PARAMS["include_duplicates"]] = False,
) -> dict[str, Any]:
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        city=city,
        category=category,
        source=source,
        verification_status=verification_status,
        include_duplicates=include_duplicates,
    )
    clauses += [Report.lat.is_not(None), Report.lon.is_not(None)]
    params: dict[str, Any] = {}

    if bbox:
        try:
            minlon, minlat, maxlon, maxlat = _parse_bbox(bbox)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        clauses += [
            Report.lon >= minlon,
            Report.lon <= maxlon,
            Report.lat >= minlat,
            Report.lat <= maxlat,
        ]
    if lat is not None and lon is not None and radius_km is not None:
        clauses.append(
            text(
                "6371 * acos(least(1.0, "
                "cos(radians(:plat)) * cos(radians(lat)) * "
                "cos(radians(lon) - radians(:plon)) + "
                "sin(radians(:plat)) * sin(radians(lat)))) <= :radius_km"
            )
        )
        params.update({"plat": lat, "plon": lon, "radius_km": radius_km})

    rows = (
        (
            await session.execute(
                select(Report)
                .where(*clauses)
                .order_by(Report.observed_at.desc())
                .limit(limit),
                params,
            )
        )
        .scalars()
        .all()
    )

    features = []
    for r in rows:
        if r.lat is None or r.lon is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
                "properties": {
                    "id": str(r.id),
                    "source": r.source,
                    "city": r.city,
                    "district": r.district,
                    "state": r.state,
                    "event_category": r.event_category,
                    "severity": r.severity,
                    "confidence": float(r.confidence) if r.confidence is not None else None,
                    "credibility_score": float(r.credibility_score or 0),
                    "verification_status": r.verification_status,
                    "is_duplicate": bool(r.is_duplicate),
                    "lang": r.lang,
                    "media_count": len(r.media or []),
                    "observed_at": r.observed_at.isoformat() if r.observed_at else None,
                    "text": (r.text or "")[:200],
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {"count": len(features), "limit": limit, "truncated": len(rows) == limit},
    }
