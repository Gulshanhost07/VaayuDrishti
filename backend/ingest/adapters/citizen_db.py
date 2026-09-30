
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from ingest.base import Adapter
from shared.db import SessionLocal
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("ingest.citizen")

BATCH = 50


class CitizenDbAdapter(Adapter):
    name = "citizen_db"
    default_interval = 30

    async def fetch(self) -> list[RawPost]:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT id, text, city, state, lat, lon, hashtags, media, observed_at, "
                        "source_url, author, raw "
                        "FROM reports "
                        "WHERE source = 'citizen' AND raw->>'citizen_pending_publish' = 'true' "
                        "ORDER BY ingested_at LIMIT :lim"
                    ),
                    {"lim": BATCH},
                )
            ).mappings().all()

            posts: list[RawPost] = []
            for row in rows:
                media_urls = [
                    m.get("source_url") or ""
                    for m in (row["media"] or [])
                    if isinstance(m, dict) and m.get("source_url")
                ]
                raw = dict(row["raw"] or {})
                raw.pop("citizen_pending_publish", None)
                observed = row["observed_at"]
                posts.append(
                    RawPost(
                        source="citizen",
                        external_id=str(row["id"]),
                        text=row["text"],
                        source_url=row["source_url"],
                        author=row["author"] or "citizen",
                        observed_at=observed
                        if isinstance(observed, datetime)
                        else datetime.now(UTC),
                        hashtags=row["hashtags"] or [],
                        lat=row["lat"],
                        lon=row["lon"],
                        city_hint=row["city"],
                        state_hint=row["state"],
                        media_urls=media_urls,
                        raw=raw,
                    )
                )

            if posts:
                ids = [p.external_id for p in posts]
                await session.execute(
                    text(
                        "UPDATE reports SET raw = raw - 'citizen_pending_publish' "
                        "WHERE id::text = ANY(:ids)"
                    ),
                    {"ids": ids},
                )
                await session.commit()
                log.info(q(f"[citizen_db] draining {len(posts)} citizen reports"))
            return posts
