
from __future__ import annotations

import re
from datetime import UTC, datetime

from ingest.base import Adapter, clean_html, http_client
from shared.logging import q, setup_logging
from shared.schemas import RawPost

log = setup_logging("ingest.mastodon")

INSTANCES = [
    "https://mastodon.social",
    "https://fosstodon.org",
    "https://mstdn.social",
]

HASHTAGS = [
    "IMD",
    "IMDWeather",
    "rain",
    "heavyrain",
    "flood",
    "flooding",
    "cyclone",
    "thunderstorm",
    "heatwave",
    "duststorm",
    "fog",
    "weather",
    "monsoon",
    "MumbaiRains",
    "DelhiRains",
    "मौसम",
    "बारिश",
    "बाढ़",
]

WEATHER_HINT = re.compile(
    r"rain|flood|storm|cyclone|heat|fog|hail|wind|weather|monsoon|"
    r"thunder|lightning|waterlog|मौसम|बारिश|बाढ़|तूफान|चक्रवात|ओला|कोहरा",
    re.I,
)

LIMIT = 20
PER_CYCLE_TAGS = 6


class MastodonAdapter(Adapter):
    name = "mastodon"
    default_interval = 300
    dedupe_at_source = True
    _tag_cursor = 0

    async def fetch(self) -> list[RawPost]:
        posts: list[RawPost] = []
        start = MastodonAdapter._tag_cursor
        tags = [HASHTAGS[(start + i) % len(HASHTAGS)] for i in range(min(PER_CYCLE_TAGS, len(HASHTAGS)))]
        MastodonAdapter._tag_cursor = (start + PER_CYCLE_TAGS) % len(HASHTAGS)

        async with http_client(timeout=25.0) as client:
            for instance in INSTANCES:
                for tag in tags:
                    try:
                        resp = await client.get(
                            f"{instance}/api/v1/timelines/tag/{tag}",
                            params={"limit": LIMIT, "local": "false", "only_media": "false"},
                        )
                        if resp.status_code != 200:
                            log.debug(q(f"[mastodon] {instance} tag={tag} -> {resp.status_code}"))
                            continue
                        for status in resp.json():
                            post = self._to_post(instance, status, tag)
                            if post is not None:
                                posts.append(post)
                    except Exception as exc:
                        log.debug(q(f"[mastodon] {instance}/{tag} failed: {exc}"))
        return posts

    @staticmethod
    def _to_post(instance: str, status: dict, tag: str) -> RawPost | None:
        text = clean_html(status.get("content") or "")
        if not text:
            return None
        tags = [t.get("name", "") for t in (status.get("tags") or [])]
        if not (WEATHER_HINT.search(text) or any(WEATHER_HINT.search(t) for t in tags)):
            return None

        account = status.get("account") or {}
        media_urls: list[str] = []
        for att in status.get("media_attachments") or []:
            url = att.get("url") or att.get("preview_url")
            if url and att.get("type") in ("image", "video", "gifv", "unknown", None):
                media_urls.append(url)

        hashtags = ["#" + t.lstrip("#") for t in tags]
        observed = status.get("created_at") or datetime.now(UTC).isoformat()
        instance_host = instance.split("//", 1)[-1]
        return RawPost(
            source="mastodon",
            external_id=f"{instance_host}:{status.get('id')}",
            text=text,
            source_url=status.get("url") or f"{instance}/@{account.get('acct', '')}/{status.get('id')}",
            author=account.get("acct"),
            observed_at=datetime.fromisoformat(str(observed).replace("Z", "+00:00")),
            hashtags=hashtags,
            media_urls=media_urls,
            lang=status.get("language"),
            raw={"instance": instance_host, "tag": tag, "reblogs": status.get("reblogs_count"),
                 "favourites": status.get("favourites_count")},
        )
