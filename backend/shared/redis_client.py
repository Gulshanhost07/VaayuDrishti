
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from shared.config import settings
from shared.logging import q, setup_logging

log = setup_logging("redis")

LIVE_CHANNEL = "weather:live"
PIPELINE_KEY = "pipeline:stats"


def get_redis() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=5.0
    )


async def publish_live(event: dict[str, Any]) -> None:
    r = get_redis()
    try:
        await r.publish(LIVE_CHANNEL, json.dumps(event, default=str, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover - cache must never break sink
        log.warning(q(f"publish_live failed: {exc}"))
    finally:
        await r.aclose()


async def cache_get(key: str) -> str | None:
    r = get_redis()
    try:
        value = await r.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
    finally:
        await r.aclose()


async def cache_set(key: str, value: str, ttl: int = 60) -> None:
    r = get_redis()
    try:
        await r.set(key, value, ex=ttl)
    finally:
        await r.aclose()


class RateLimiter:

    def __init__(self, prefix: str, limit: int, window_seconds: int) -> None:
        self.prefix = prefix
        self.limit = limit
        self.window = window_seconds

    async def allow(self, ident: str) -> bool:
        r = get_redis()
        try:
            key = f"ratelimit:{self.prefix}:{ident}"
            n = await r.incr(key)
            if n == 1:
                await r.expire(key, self.window)
            return n <= self.limit
        finally:
            await r.aclose()


async def incr_counter(name: str, amount: int = 1) -> None:
    r = get_redis()
    try:
        await r.hincrby(PIPELINE_KEY, name, amount)
    finally:
        await r.aclose()


async def get_counters() -> dict[str, int]:
    r = get_redis()
    try:
        data = await r.hgetall(PIPELINE_KEY)
        out: dict[str, int] = {}
        for k, v in data.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            raw_v = v.decode("utf-8") if isinstance(v, bytes) else v
            out[str(key)] = int(raw_v)
        return out
    finally:
        await r.aclose()
