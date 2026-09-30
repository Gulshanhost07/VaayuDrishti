
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import httpx

from shared import topics as T
from shared.db import SessionLocal
from shared.kafka import Producer
from shared.logging import q, setup_logging
from shared.models import IngestRun, RunStatus
from shared.redis_client import get_redis
from shared.schemas import RawPost

log = setup_logging("ingest")

DEFAULT_TIMEOUT = 20.0
USER_AGENT = "VaayuDrishti/1.0 (SIH26069 weather data collector; contact: team@vaayu.local)"

SEEN_TTL_SECONDS = 7 * 24 * 3600


def http_client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )


class Adapter(ABC):

    name: str = "base"
    default_interval: int = 600
    enabled_by_default: bool = True
    dedupe_at_source: bool = False

    def __init__(self, producer: Producer) -> None:
        self.producer = producer

    @abstractmethod
    async def fetch(self) -> list[RawPost]:
        pass

    async def run(self) -> int:
        run_id = await self._start_run()
        sent = 0
        try:
            posts = await self.fetch()
            fetched = len(posts)
            if self.dedupe_at_source:
                posts = await self._filter_seen(posts)
            for post in posts:
                await self.producer.send(
                    T.RAW_POSTS,
                    post.model_dump(mode="json"),
                    key=f"{post.source}:{post.external_id}",
                )
                sent += 1
            await self._finish_run(run_id, RunStatus.success, fetched=fetched, published=sent)
            if posts:
                log.info(q(f"[{self.name}] published {sent}/{fetched} posts"))
            return sent
        except Exception as exc:
            log.error(q(f"[{self.name}] cycle failed: {type(exc).__name__}: {exc}"))
            await self._finish_run(
                run_id, RunStatus.failed, fetched=0, published=sent, error=str(exc)[:2000]
            )
            return sent

    async def _filter_seen(self, posts: list[RawPost]) -> list[RawPost]:
        if not posts:
            return posts
        r = get_redis()
        key = f"ingest:seen:{self.name}"
        try:
            pipe = r.pipeline()
            for post in posts:
                pipe.sadd(key, post.external_id)
            added = await pipe.execute()
            await r.expire(key, SEEN_TTL_SECONDS)
        except Exception as exc:
            log.warning(q(f"[{self.name}] seen-filter unavailable: {exc}"))
            return posts
        finally:
            await r.aclose()
        kept = [p for p, was_new in zip(posts, added, strict=True) if was_new]
        dropped = len(posts) - len(kept)
        if dropped:
            log.info(
                q(
                    f"[{self.name}] dropped {dropped}/{len(posts)} "
                    "already-published posts"
                )
            )
        return kept

    async def _start_run(self) -> Any:
        async with SessionLocal() as session:
            run = IngestRun(source=self.name, status=RunStatus.running.value)
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    async def _finish_run(
        self,
        run_id: Any,
        status: RunStatus,
        fetched: int,
        published: int,
        errors: int = 0,
        error: str | None = None,
    ) -> None:
        try:
            async with SessionLocal() as session:
                row = await session.get(IngestRun, run_id)
                if row is None:
                    return
                row.status = status.value
                row.fetched = fetched
                row.published = published
                row.errors = errors
                row.last_error = error
                row.finished_at = datetime.now(UTC)
                await session.commit()
        except Exception as exc:
            log.warning(q(f"[{self.name}] failed to record run: {exc}"))


async def backoff_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


def clean_html(text: str) -> str:
    import html as htmllib
    import re

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>|</div>|</li>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
