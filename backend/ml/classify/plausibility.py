
from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

from sqlalchemy import select

from shared.db import session_scope
from shared.logging import q, setup_logging
from shared.models import ReferenceObservation
from shared.redis_client import cache_get, cache_set

log = setup_logging("plausibility")

RULES: dict[str, tuple[str, float, str, str]] = {
    "rainfall": ("precip_mm", 5.0, ">=", "measured rainfall >= 5 mm"),
    "flooding": ("precip_mm", 15.0, ">=", "measured rainfall >= 15 mm"),
    "heatwave": ("temp_c", 40.0, ">=", "measured temperature >= 40 C"),
    "strong_winds": ("wind_kph", 30.0, ">=", "measured wind >= 30 km/h"),
}
WINDOW = timedelta(hours=4)
MAX_DISTANCE_KM = 100.0
CACHE_TTL = 900


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


async def check(
    event_category: str,
    lat: float | None,
    lon: float | None,
    observed_at: Any,
    location_key: str = "",
) -> dict[str, Any]:
    rule = RULES.get(event_category)
    if rule is None:
        return {"checked": False, "reason": "no_reference_rule"}
    if lat is None or lon is None or observed_at is None:
        return {"checked": False, "reason": "no_location"}

    metric, threshold, op, label = rule
    try:
        hour_bucket = int(observed_at.timestamp()) // 1800
        cache_key = f"plaus:{event_category}:{lat:.2f}:{lon:.2f}:{hour_bucket}"
        hit = await cache_get(cache_key)
        if hit:
            return json.loads(hit)

        result = await _query(event_category, lat, lon, observed_at, metric, threshold, op, label)
        with suppress(Exception):
            await cache_set(cache_key, json.dumps(result, default=str), ttl=CACHE_TTL)
        return result
    except Exception as exc:
        log.warning(q(f"[plausibility] check failed: {exc}"))
        return {"checked": False, "reason": f"error:{type(exc).__name__}"}


async def _query(
    event_category: str,
    lat: float,
    lon: float,
    observed_at: Any,
    metric: str,
    threshold: float,
    op: str,
    label: str,
) -> dict[str, Any]:
    lo = observed_at - WINDOW
    hi = observed_at + WINDOW
    async with session_scope() as session:
        rows = (
            (
                await session.execute(
                    select(ReferenceObservation)
                    .where(ReferenceObservation.observed_at.between(lo, hi))
                    .order_by(ReferenceObservation.observed_at)
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )

    best: ReferenceObservation | None = None
    best_km = MAX_DISTANCE_KM + 1
    for row in rows:
        if row.lat is None or row.lon is None:
            continue
        km = haversine_km(lat, lon, row.lat, row.lon)
        if km < best_km:
            best, best_km = row, km
    if best is None:
        return {"checked": False, "reason": "no_reference_observation"}

    observed = getattr(best, metric, None)
    if observed is None:
        return {"checked": False, "reason": "metric_missing", "metric": metric}

    agrees = observed >= threshold if op == ">=" else observed <= threshold
    return {
        "checked": True,
        "event_category": event_category,
        "metric": metric,
        "observed": round(float(observed), 2),
        "threshold": threshold,
        "operator": op,
        "expectation": label,
        "agrees": bool(agrees),
        "station": best.station,
        "provider": best.provider,
        "reference_at": best.observed_at.isoformat() if best.observed_at else None,
        "distance_km": round(best_km, 1),
        "checked_at": datetime.now(UTC).isoformat(),
    }
