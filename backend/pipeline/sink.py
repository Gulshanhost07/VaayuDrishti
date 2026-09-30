
from __future__ import annotations

import asyncio
import threading
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pipeline.run_stage import Stage
from shared import search
from shared import topics as T
from shared.db import session_scope
from shared.logging import q, setup_logging
from shared.models import EventCategory, Report
from shared.redis_client import incr_counter, publish_live
from shared.schemas import ClassifiedPost

log = setup_logging("pipeline.sink")

_index_lock = threading.Lock()
_index_ready = False


def _ensure_index() -> None:
    global _index_ready
    if _index_ready:
        return
    with _index_lock:
        if not _index_ready:
            search.ensure_index()
            _index_ready = True


def _apply(post: ClassifiedPost, row: Report, dup_id: Any) -> None:
    row.source_url = post.source_url or row.source_url
    row.author = post.author or row.author
    row.text = post.text
    row.lang = post.lang
    row.hashtags = post.hashtags
    row.lat = post.lat
    row.lon = post.lon
    row.city = post.city
    row.district = post.district
    row.state = post.state
    row.event_category = EventCategory(post.event_category)
    row.severity = post.severity
    row.confidence = post.category_confidence
    row.credibility_score = post.credibility_score
    row.credibility_features = post.credibility_features
    row.plausibility = post.plausibility
    row.is_duplicate = post.is_duplicate
    row.duplicate_of = dup_id
    if not row.media:
        row.media = [m.model_dump() for m in post.media]
    row.observed_at = post.observed_at
    raw = dict(post.raw or {})
    raw.update(
        {
            "geocode_method": post.geocode_method,
            "duplicate_of": post.duplicate_of,
            "dedup_score": post.dedup_score,
        }
    )
    row.raw = raw


async def _resolve_duplicate(session: Any, post: ClassifiedPost) -> Any:
    if not post.is_duplicate or not post.duplicate_of:
        return None
    src, _, ext = post.duplicate_of.partition(":")
    if not src or not ext:
        return None
    res = await session.execute(
        select(Report.id).where(Report.source == src, Report.external_id == ext)
    )
    return res.scalar_one_or_none()


async def handle(message: dict[str, Any]) -> None:
    post = ClassifiedPost.model_validate(message)

    async with session_scope() as session:
        res = await session.execute(
            select(Report).where(
                Report.source == post.source, Report.external_id == post.external_id
            )
        )
        row = res.scalar_one_or_none()
        dup_id = await _resolve_duplicate(session, post)

        if row is None:
            row = Report(source=post.source, external_id=post.external_id)
            _apply(post, row, dup_id)
            session.add(row)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                res = await session.execute(
                    select(Report).where(
                        Report.source == post.source,
                        Report.external_id == post.external_id,
                    )
                )
                row = res.scalar_one_or_none()
                if row is None:
                    raise
                _apply(post, row, dup_id)
        else:
            _apply(post, row, dup_id)

        report_id = row.id
        doc = search.to_doc(row)
        await session.commit()

    try:
        await asyncio.to_thread(_index_and_store, doc)
    except Exception as exc:
        log.warning(q(f"[sink] opensearch index failed for {report_id}: {exc}"))

    if post.is_duplicate:
        await incr_counter("sink_duplicate")
    else:
        await incr_counter("sink_saved")
        await publish_live(
            {
                "id": str(report_id),
                "source": post.source,
                "city": post.city,
                "state": post.state,
                "event_category": post.event_category,
                "severity": post.severity,
                "confidence": post.category_confidence,
                "credibility_score": post.credibility_score,
                "text": post.text[:280],
                "lat": post.lat,
                "lon": post.lon,
                "observed_at": post.observed_at.isoformat(),
            }
        )
    log.debug(
        q(
            f"[sink] {post.source}:{post.external_id} -> {report_id} "
            f"dup={post.is_duplicate}"
        )
    )
    return None


def _index_and_store(doc: dict[str, Any]) -> None:
    _ensure_index()
    search.index_report(doc)


def main() -> None:
    stage = Stage("sink", T.CLASSIFIED_POSTS, None, handle)
    asyncio.run(stage.run())


if __name__ == "__main__":
    main()
