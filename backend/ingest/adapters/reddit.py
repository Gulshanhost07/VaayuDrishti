
from __future__ import annotations

import re
from datetime import UTC, datetime

from ingest.base import Adapter, clean_html, http_client
from shared.config import settings
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("ingest.reddit")

SUBREDDITS = ["india", "mumbai", "chennai", "bangalore", "delhi", "weather", "indianweather"]
QUERY = "rain OR flood OR storm OR cyclone OR heatwave OR fog OR thunderstorm OR monsoon"
WEATHER_HINT = re.compile(
    r"rain|flood|storm|cyclone|heat|fog|hail|wind|weather|monsoon|thunder|waterlog", re.I
)


class RedditAdapter(Adapter):
    name = "reddit"
    _cursor: int = 0

    default_interval = 300
    dedupe_at_source = True

    async def fetch(self) -> list[RawPost]:
        posts: list[RawPost] = []
        RedditAdapter._cursor = (getattr(RedditAdapter, "_cursor", 0) + 1) % len(SUBREDDITS)
        sub = SUBREDDITS[RedditAdapter._cursor]

        async with http_client(timeout=20.0) as client:
            resp = await client.get(
                f"https://www.reddit.com/r/{sub}/search.json",
                params={"q": QUERY, "restrict_sr": "1", "sort": "new", "limit": 25},
                headers={"User-Agent": settings.reddit_user_agent},
            )
            if resp.status_code == 403:
                log.warning(q("[reddit] blocked (403) from this network - skipping cycle"))
                return []
            resp.raise_for_status()
            data = resp.json()

        for child in (data.get("data") or {}).get("children") or []:
            post = self._to_post(child.get("data") or {}, sub)
            if post is not None:
                posts.append(post)
        return posts

    @staticmethod
    def _to_post(item: dict, sub: str) -> RawPost | None:
        text = clean_html(item.get("selftext") or item.get("title") or "")
        title = item.get("title") or ""
        full = f"{title}\n{text}".strip()
        if not full:
            return None
        if not WEATHER_HINT.search(full):
            return None
        if item.get("over_18"):
            return None
        created = datetime.fromtimestamp(float(item.get("created_utc", 0)), tz=UTC)
        return RawPost(
            source="reddit",
            external_id=str(item.get("id")),
            text=full[:4000],
            source_url=f"https://www.reddit.com{item.get('permalink', '')}",
            author=item.get("author"),
            observed_at=created or datetime.now(UTC),
            hashtags=["#reddit", f"#{sub}", "#Weather"],
            lang="en",
            raw={"subreddit": sub, "score": item.get("score"), "num_comments": item.get("num_comments")},
        )
