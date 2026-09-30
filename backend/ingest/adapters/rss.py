
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser

from ingest.base import Adapter, clean_html, http_client
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("ingest.rss")

GOOGLE_NEWS = "https://news.google.com/rss/search"

QUERIES: list[tuple[str, str]] = [
    ("heavy rain India IMD", "rainfall"),
    ("flood India rain", "flooding"),
    ("heatwave India temperature", "heatwave"),
    ("thunderstorm lightning India", "thunderstorm"),
    ("cyclone India warning", "strong_winds"),
    ("dust storm India", "dust_storm"),
    ("fog India visibility", "fog"),
]

TITLE_HINTS: dict[str, list[str]] = {
    "rainfall": ["rain", "downpour", "pouring", "monsoon", "waterlog"],
    "flooding": ["flood", "inundat", "submerg", "overflow", "relief camp"],
    "heatwave": ["heatwave", "heat wave", "scorch", "temperature rises", "hot day", "warm"],
    "thunderstorm": ["thunder", "lightning", "hail", "squall"],
    "strong_winds": ["cyclone", "storm", "wind", "gale", "typhoon"],
    "dust_storm": ["dust storm", "duststorm", "sandstorm", "dust"],
    "fog": ["fog", "mist", "low visibility"],
}


class RSSAdapter(Adapter):
    name = "rss"
    _cursor: int = 0

    default_interval = 900
    dedupe_at_source = True

    async def fetch(self) -> list[RawPost]:
        posts: list[RawPost] = []
        RSSAdapter._cursor = (getattr(RSSAdapter, "_cursor", 0) + 2) % len(QUERIES)
        start = RSSAdapter._cursor
        picks = [QUERIES[(start + i) % len(QUERIES)] for i in range(3)]

        async with http_client(timeout=25.0) as client:
            for query, hint in picks:
                try:
                    resp = await client.get(
                        GOOGLE_NEWS,
                        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
                    )
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.content)
                except Exception as exc:
                    log.warning(q(f"[rss] query '{query}' failed: {exc}"))
                    continue
                for entry in feed.entries[:15]:
                    post = self._to_post(entry, hint)
                    if post is not None:
                        posts.append(post)
        return posts

    @staticmethod
    def _to_post(entry, hint: str) -> RawPost | None:
        title = clean_html(getattr(entry, "title", "") or "")
        summary = clean_html(getattr(entry, "summary", "") or "")
        link = getattr(entry, "link", "") or ""
        if not title or not link:
            return None

        haystack = f"{title} {summary}".lower()
        category = hint
        for cat, words in TITLE_HINTS.items():
            if any(w in haystack for w in words):
                category = cat
                break
        else:
            return None

        published = getattr(entry, "published", None) or getattr(entry, "updated", None)
        try:
            observed = parsedate_to_datetime(published) if published else datetime.now(UTC)
        except (TypeError, ValueError):
            observed = datetime.now(UTC)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=UTC)

        publisher = ""
        source = getattr(entry, "source", None)
        if source is not None:
            publisher = getattr(source, "title", "") or ""

        external_id = hashlib.sha1(link.encode("utf-8")).hexdigest()[:24]
        text = f"{title}" + (f" - {summary}" if summary and summary != title else "")
        return RawPost(
            source="rss",
            external_id=f"gn-{external_id}",
            text=text[:4000],
            source_url=link,
            author=publisher or "Google News",
            observed_at=observed,
            hashtags=["#IMD", "#Weather", f"#{category}"],
            lang="en",
            raw={"query_hint": hint, "category_hint": category, "publisher": publisher},
        )
