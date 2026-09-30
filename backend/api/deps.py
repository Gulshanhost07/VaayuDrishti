
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db import get_session
from shared.models import AdminUser
from shared.security import TokenError, decode_token, role_at_least

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
) -> AdminUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, expected_kind="access")
    except TokenError as exc:
        raise unauthorized from exc
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise unauthorized from exc
    user = await session.get(AdminUser, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_role(minimum: str):

    async def dependency(
        user: Annotated[AdminUser, Depends(get_current_user)],
    ) -> AdminUser:
        if not role_at_least(user.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires {minimum} role",
            )
        return user

    return dependency


CurrentUser = Annotated[AdminUser, Depends(get_current_user)]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def parse_dt(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid datetime: {value}") from exc
    if len(value) == 10 and end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def build_report_filters(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    state: str | None = None,
    city: str | None = None,
    category: str | None = None,
    source: str | None = None,
    verification_status: str | None = None,
    lang: str | None = None,
    include_duplicates: bool = False,
    include_rejected: bool = True,
    min_credibility: float | None = None,
) -> list[Any]:
    from shared.models import Report

    clauses: list[Any] = []
    if (start := parse_dt(date_from)) is not None:
        clauses.append(Report.observed_at >= start)
    if (end := parse_dt(date_to, end_of_day=True)) is not None:
        clauses.append(Report.observed_at <= end)
    if state:
        clauses.append(Report.state.ilike(state))
    if city:
        clauses.append(Report.city.ilike(city))
    if category:
        clauses.append(Report.event_category == category)
    if source:
        clauses.append(Report.source == source)
    if verification_status:
        clauses.append(Report.verification_status == verification_status)
    elif not include_rejected:
        clauses.append(Report.verification_status != "rejected")
    if lang:
        clauses.append(Report.lang == lang)
    if not include_duplicates:
        clauses.append(Report.is_duplicate.is_(False))
    if min_credibility is not None:
        clauses.append(Report.credibility_score >= min_credibility)
    return clauses


def build_report_query(
    filters: dict[str, Any],
    *,
    include_duplicates: bool = False,
    include_rejected: bool = True,
) -> list[Any]:
    return build_report_filters(
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        state=filters.get("state"),
        city=filters.get("city"),
        category=filters.get("category"),
        source=filters.get("source"),
        verification_status=filters.get("verification_status"),
        lang=filters.get("lang"),
        include_duplicates=include_duplicates,
        include_rejected=include_rejected,
        min_credibility=filters.get("min_credibility"),
    )


REPORT_FILTER_PARAMS = {
    "date_from": Query(description="ISO date/datetime lower bound on observed_at"),
    "date_to": Query(description="ISO date/datetime upper bound on observed_at"),
    "state": Query(max_length=120),
    "city": Query(max_length=120),
    "category": Query(
        pattern="^(rainfall|thunderstorm|flooding|heatwave|fog|dust_storm|strong_winds|other)$",
    ),
    "source": Query(max_length=32),
    "verification_status": Query( pattern="^(pending|verified|rejected|disputed)$"
    ),
    "lang": Query(max_length=8),
    "include_duplicates": Query(),
    "min_credibility": Query(ge=0.0, le=1.0),
}
