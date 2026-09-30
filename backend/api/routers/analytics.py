
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import String, func, literal_column, select, text

from api.deps import SessionDep, build_report_filters
from shared.models import Report, SourceConfig

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _cg(col: Any, default: str) -> Any:
    return func.coalesce(col, literal_column(f"'{default}'"))


GROUP_COLS = {
    "category": _cg(Report.event_category.cast(String), "other"),
    "state": _cg(Report.state, "Unknown"),
    "source": Report.source,
    "city": _cg(Report.city, "Unknown"),
    "lang": _cg(Report.lang, "unknown"),
}


@router.get("/summary")
async def summary(session: SessionDep) -> dict[str, Any]:
    now = datetime.now(UTC)
    status_rows = (
        await session.execute(
            select(Report.verification_status, func.count())
            .where(Report.is_duplicate.is_(False))
            .group_by(Report.verification_status)
        )
    ).all()
    by_status = {str(status): int(n) for status, n in status_rows}
    total = sum(by_status.values())

    avg_cred = (
        await session.execute(
            select(func.avg(Report.credibility_score)).where(Report.is_duplicate.is_(False))
        )
    ).scalar()
    last_24h = (
        await session.execute(
            select(func.count()).where(
                Report.is_duplicate.is_(False),
                Report.observed_at >= now - timedelta(hours=24),
            )
        )
    ).scalar_one()
    last_hour = (
        await session.execute(
            select(func.count()).where(
                Report.is_duplicate.is_(False),
                Report.observed_at >= now - timedelta(hours=1),
            )
        )
    ).scalar_one()
    states = (
        await session.execute(
            select(func.count(func.distinct(Report.state))).where(
                Report.is_duplicate.is_(False), Report.state.is_not(None)
            )
        )
    ).scalar_one()
    cat = _cg(Report.event_category.cast(String), "other")
    category_rows = (
        await session.execute(
            select(cat, func.count())
            .where(Report.is_duplicate.is_(False))
            .group_by(cat)
            .order_by(func.count().desc())
        )
    ).all()
    sources_enabled = (
        await session.execute(
            select(func.count()).where(SourceConfig.enabled.is_(True))
        )
    ).scalar_one()

    verified = by_status.get("verified", 0)
    return {
        "total_reports": total,
        "verified": verified,
        "pending": by_status.get("pending", 0),
        "disputed": by_status.get("disputed", 0),
        "rejected": by_status.get("rejected", 0),
        "verified_pct": round(100 * verified / total, 1) if total else 0.0,
        "avg_credibility": round(float(avg_cred or 0), 3),
        "reports_last_24h": int(last_24h),
        "reports_last_hour": int(last_hour),
        "states_covered": int(states),
        "categories": {str(c): int(n) for c, n in category_rows},
        "sources_enabled": int(sources_enabled),
        "computed_at": now.isoformat(),
    }


@router.get("/timeseries")
async def timeseries(
    session: SessionDep,
    bucket: Annotated[Literal["hour", "day", "week"], Query()] = "hour",
    group_by: Annotated[Literal["category", "state", "source", "city", "lang"], Query()]
    = "category",
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    clauses = build_report_filters(
        date_from=date_from,
        date_to=date_to,
        state=state,
        category=category,
    )
    if not clauses:
        default_from = datetime.now(UTC) - timedelta(days=7)
        clauses = [Report.observed_at >= default_from]
    col = GROUP_COLS[group_by]
    rows = (
        await session.execute(
            select(
                func.date_trunc(bucket, Report.observed_at).label("b"),
                col.label("k"),
                func.count().label("n"),
            )
            .where(*clauses)
            .group_by("b", "k")
            .order_by("b")
        )
    ).all()
    return {
        "bucket": bucket,
        "group_by": group_by,
        "points": [
            {"bucket": b.isoformat(), "key": str(k), "count": int(n)} for b, k, n in rows
        ],
    }


@router.get("/by-state")
async def by_state(
    session: SessionDep,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 36,
) -> dict[str, Any]:
    clauses = build_report_filters(date_from=date_from, date_to=date_to)
    st = _cg(Report.state, "Unknown")
    rows = (
        await session.execute(
            select(
                st.label("state"),
                func.count().label("count"),
                func.count()
                .filter(Report.verification_status == "verified")
                .label("verified"),
                func.avg(Report.credibility_score).label("avg_cred"),
                func.max(Report.observed_at).label("last_seen"),
            )
            .where(*clauses)
            .group_by(st)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()
    return {
        "states": [
            {
                "state": s,
                "count": int(c),
                "verified": int(v),
                "avg_credibility": round(float(a or 0), 3),
                "last_seen": ls.isoformat() if ls else None,
            }
            for s, c, v, a, ls in rows
        ]
    }


@router.get("/by-category")
async def by_category(
    session: SessionDep,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    clauses = build_report_filters(date_from=date_from, date_to=date_to)
    cat = _cg(Report.event_category.cast(String), "other")
    rows = (
        await session.execute(
            select(
                cat,
                func.count(),
                func.avg(Report.credibility_score),
            )
            .where(*clauses)
            .group_by(cat)
            .order_by(func.count().desc())
        )
    ).all()

    now = datetime.now(UTC)
    curr: dict[str, int] = dict(
        (
            await session.execute(
                select(cat, func.count())
                .where(Report.observed_at >= now - timedelta(hours=24))
                .group_by(cat)
            )
        ).all()
    )
    prev: dict[str, int] = dict(
        (
            await session.execute(
                select(cat, func.count())
                .where(
                    Report.observed_at >= now - timedelta(hours=48),
                    Report.observed_at < now - timedelta(hours=24),
                )
                .group_by(cat)
            )
        ).all()
    )
    return {
        "categories": [
            {
                "category": str(c),
                "count": int(n),
                "avg_credibility": round(float(a or 0), 3),
                "last_24h": int(curr.get(str(c), 0)),
                "prev_24h": int(prev.get(str(c), 0)),
                "trend": int(curr.get(str(c), 0)) - int(prev.get(str(c), 0)),
            }
            for c, n, a in rows
        ]
    }


@router.get("/by-source")
async def by_source(
    session: SessionDep,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    clauses = build_report_filters(date_from=date_from, date_to=date_to)
    rows = (
        await session.execute(
            select(Report.source, func.count(), func.avg(Report.credibility_score))
            .where(*clauses)
            .group_by(Report.source)
            .order_by(func.count().desc())
        )
    ).all()
    total = sum(int(n) for _, n, _ in rows) or 1
    return {
        "sources": [
            {
                "source": str(s),
                "count": int(n),
                "share_pct": round(100 * int(n) / total, 1),
                "avg_credibility": round(float(a or 0), 3),
            }
            for s, n, a in rows
        ]
    }


@router.get("/hashtags")
async def hashtags(
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await session.execute(
            text(
                "SELECT lower(t) AS tag, count(*) AS n "
                "FROM reports r, unnest(r.hashtags) AS t "
                "WHERE r.observed_at >= :since AND r.is_duplicate = false "
                "GROUP BY lower(t) ORDER BY n DESC LIMIT :lim"
            ),
            {"since": since, "lim": limit},
        )
    ).all()
    return {"days": days, "hashtags": [{"tag": t, "count": int(n)} for t, n in rows]}


@router.get("/filters")
async def filter_options(session: SessionDep) -> dict[str, Any]:
    states: list[str | None] = list(
        (
            await session.execute(
                select(func.distinct(Report.state))
                .where(Report.state.is_not(None))
                .order_by(Report.state)
                .limit(100)
            )
        ).scalars()
    )
    cities: list[str | None] = list(
        (
            await session.execute(
                select(func.distinct(Report.city))
                .where(Report.city.is_not(None))
                .order_by(Report.city)
                .limit(200)
            )
        ).scalars()
    )
    sources: list[str | None] = list(
        (
            await session.execute(select(func.distinct(Report.source)).order_by(Report.source))
        ).scalars()
    )
    langs: list[str | None] = list(
        (
            await session.execute(
                select(func.distinct(Report.lang)).where(Report.lang.is_not(None))
            )
        ).scalars()
    )
    return {
        "states": [s for s in states if s],
        "cities": [c for c in cities if c],
        "sources": [s for s in sources if s],
        "langs": [lg for lg in langs if lg],
        "categories": [
            "rainfall",
            "thunderstorm",
            "flooding",
            "heatwave",
            "fog",
            "dust_storm",
            "strong_winds",
            "other",
        ],
        "verification_statuses": ["pending", "verified", "rejected", "disputed"],
    }
