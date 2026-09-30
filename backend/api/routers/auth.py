
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, SessionDep, client_ip
from shared.models import AdminUser
from shared.redis_client import RateLimiter
from shared.schemas import LoginIn, MeOut, RefreshIn, TokenOut
from shared.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

login_limiter = RateLimiter("login", limit=15, window_seconds=300)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: SessionDep) -> TokenOut:
    if not await login_limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts, retry later",
        )
    res = await session.execute(
        select(AdminUser).where(AdminUser.email == body.email.lower().strip())
    )
    user = res.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(
        user.password_hash, body.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    return TokenOut(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id), user.role),
        token_type="bearer",
        role=user.role,
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, session: SessionDep) -> TokenOut:
    try:
        payload = decode_token(body.refresh_token, expected_kind="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="invalid refresh token") from exc
    res = await session.execute(
        select(AdminUser).where(AdminUser.id == payload["sub"])
    )
    user = res.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="account unavailable")
    return TokenOut(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id), user.role),
        token_type="bearer",
        role=user.role,
    )


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )
