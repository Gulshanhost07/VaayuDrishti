
from __future__ import annotations

import asyncio
import os
import signal
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from shared import topics as T
from shared.kafka import Consumer, Producer, ensure_topics
from shared.logging import q, setup_logging
from shared.redis_client import incr_counter

log = setup_logging("pipeline")

Handler = Callable[[dict[str, Any]], Awaitable[BaseModel | None]]

STAGE_TIMEOUT_SECONDS = float(os.environ.get("STAGE_TIMEOUT_SECONDS", "120"))
HEARTBEAT_SECONDS = 30.0


class Stage:
    def __init__(
        self,
        name: str,
        in_topic: str,
        out_topic: str | None,
        handler: Handler,
    ) -> None:
        self.name = name
        self.in_topic = in_topic
        self.out_topic = out_topic
        self.handler = handler
        self._stop = asyncio.Event()
        self.processed = 0
        self.failed = 0
        self._last_msg_at = time.monotonic()

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> int:
        await ensure_topics()
        consumer = Consumer(self.in_topic, group=f"pipeline-{self.name}")
        producer = Producer()
        await consumer.start()
        await producer.start()
        log.info(q(f"stage '{self.name}' listening on {self.in_topic}"))

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except (NotImplementedError, RuntimeError):
                signal.signal(sig, lambda *_: self.request_stop())

        heartbeat = asyncio.create_task(self._heartbeat())

        try:
            while not self._stop.is_set():
                try:
                    raw = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                except TimeoutError:
                    continue
                self._last_msg_at = time.monotonic()
                await self._process(raw, producer)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await consumer.stop()
            await producer.stop()
            log.info(
                q(
                    f"stage '{self.name}' stopped "
                    f"(processed={self.processed} failed={self.failed})"
                )
            )
        return 0

    async def _heartbeat(self) -> None:
        try:
            while not self._stop.is_set():
                await asyncio.sleep(HEARTBEAT_SECONDS)
                idle = time.monotonic() - self._last_msg_at
                log.info(
                    q(
                        f"stage '{self.name}' heartbeat "
                        f"processed={self.processed} failed={self.failed} "
                        f"idle={idle:.0f}s"
                    )
                )
        except asyncio.CancelledError:
            pass

    async def _process(self, raw: dict[str, Any], producer: Producer) -> None:
        try:
            await asyncio.wait_for(
                self._handle_and_publish(raw, producer),
                timeout=STAGE_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            await self._to_dlq(
                producer,
                raw,
                f"StageTimeout: exceeded {STAGE_TIMEOUT_SECONDS:.0f}s",
            )
        except (ValidationError, KeyError, TypeError, ValueError) as exc:
            await self._to_dlq(producer, raw, f"{type(exc).__name__}: {exc}")
        except Exception as exc:
            await self._to_dlq(producer, raw, f"{type(exc).__name__}: {exc}")

    async def _handle_and_publish(self, raw: dict[str, Any], producer: Producer) -> None:
        out = await self.handler(raw)
        if out is not None and self.out_topic is not None:
            await producer.send(
                self.out_topic,
                out.model_dump(mode="json"),
                key=str(raw.get("external_id") or raw.get("id") or ""),
            )
        self.processed += 1
        if self.processed % 500 == 0:
            await incr_counter(f"{self.name}_processed", 0)
            log.info(q(f"stage '{self.name}' processed={self.processed}"))

    async def _to_dlq(self, producer: Producer, raw: dict[str, Any], error: str) -> None:
        self.failed += 1
        try:
            await producer.send(
                T.DLQ,
                {
                    "topic": self.in_topic,
                    "stage": self.name,
                    "error": error[:2000],
                    "payload": raw,
                },
            )
            await incr_counter(f"{self.name}_failed")
        except Exception as exc:
            log.error(q(f"stage '{self.name}' DLQ publish failed: {exc}"))
        log.warning(q(f"stage '{self.name}' failed: {error[:300]}"))
