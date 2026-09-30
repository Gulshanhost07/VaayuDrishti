
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.logging import q, setup_logging
from shared.redis_client import LIVE_CHANNEL, get_redis

log = setup_logging("api.live")

router = APIRouter(tags=["live"])

HEARTBEAT_SECONDS = 20


@router.websocket("/live/stream")
async def live_stream(ws: WebSocket) -> None:
    await ws.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    stop = asyncio.Event()
    await pubsub.subscribe(LIVE_CHANNEL)
    await ws.send_text(
        json.dumps({"type": "hello", "channel": LIVE_CHANNEL, "ts": datetime.now(UTC).isoformat()})
    )
    log.debug(q("[live] client connected"))

    async def reader() -> None:
        try:
            while not stop.is_set():
                await ws.receive_text()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            stop.set()

    async def pump() -> None:
        try:
            while not stop.is_set():
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("data"):
                    await ws.send_text(msg["data"])
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            stop.set()

    async def heartbeat() -> None:
        try:
            while not stop.is_set():
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await ws.send_text(
                    json.dumps(
                        {"type": "heartbeat", "ts": datetime.now(UTC).isoformat()}
                    )
                )
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            stop.set()

    tasks = [asyncio.create_task(fn()) for fn in (reader, pump, heartbeat)]
    try:
        await stop.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        with_error: Any = None
        try:
            await pubsub.unsubscribe(LIVE_CHANNEL)
            await pubsub.aclose()
        except Exception as exc:
            with_error = exc
        await redis.aclose()
        if with_error:
            log.debug(q(f"[live] teardown: {with_error}"))
        log.debug(q("[live] client disconnected"))
