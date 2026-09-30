
from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text as sql_text

from shared import search
from shared.config import settings
from shared.db import engine
from shared.logging import q, setup_logging

log = setup_logging("api.system")

router = APIRouter(tags=["system"])


async def _check_db() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(sql_text("SELECT 1"))
        return {"ok": True, "ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


async def _check_redis() -> dict[str, Any]:
    from shared.redis_client import get_redis

    started = time.perf_counter()
    try:
        r = get_redis()
        try:
            await r.ping()
        finally:
            await r.aclose()
        return {"ok": True, "ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _opensearch_sync() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        health = search.client().cluster.health()
        return {
            "ok": health.get("status") in ("green", "yellow"),
            "status": health.get("status"),
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


async def _check_opensearch() -> dict[str, Any]:
    return await asyncio.to_thread(_opensearch_sync)


async def _check_kafka() -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        started = time.perf_counter()
        try:
            import asyncio as _asyncio

            from aiokafka.admin import AIOKafkaAdminClient

            async def _probe() -> None:
                admin = AIOKafkaAdminClient(
                    bootstrap_servers=settings.kafka_bootstrap_servers
                )
                await admin.start()
                try:
                    await admin.list_topics()
                finally:
                    await admin.close()

            _asyncio.run(_probe())
            return {"ok": True, "ms": round((time.perf_counter() - started) * 1000, 1)}
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}

    return await asyncio.to_thread(_run)


def _minio_sync() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        from shared import objectstore

        objectstore.get_client().bucket_exists(settings.minio_bucket)
        return {"ok": True, "ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


@router.get("/health")
async def health(deep: bool = False) -> dict[str, Any]:
    base: dict[str, Any] = {"status": "ok", "service": "api", "env": settings.app_env}
    if not deep:
        return base
    components = {
        "postgres": await _check_db(),
        "redis": await _check_redis(),
        "opensearch": await _check_opensearch(),
        "kafka": await _check_kafka(),
        "minio": await asyncio.to_thread(_minio_sync),
    }
    ok = all(c.get("ok") for c in components.values())
    base["status"] = "ok" if ok else "degraded"
    base["components"] = components
    if not ok:
        log.warning(q(f"[health] degraded: {components}"))
    return base
