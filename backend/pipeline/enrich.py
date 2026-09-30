
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import re
from typing import Any

import httpx
from langdetect import DetectorFactory, LangDetectException, detect
from sqlalchemy import select

from ingest.base import clean_html, http_client
from ml.geocode import (
    City,
    all_cities,
    city_aliases,
    find_city_by_name,
    nearest_city,
    state_aliases,
)
from pipeline.run_stage import Stage
from shared import objectstore
from shared import topics as T
from shared.db import session_scope
from shared.logging import q, setup_logging
from shared.models import Report
from shared.redis_client import cache_get, cache_set
from shared.schemas import EnrichedPost, MediaRef, RawPost

log = setup_logging("pipeline.enrich")

DetectorFactory.seed = 0

_INDIC = "\u0900-\u097f\u0980-\u09ff\u0a00-\u0aff\u0b80-\u0bff\u0c00-\u0cff\u0d00-\u0d7f"
HASHTAG_RE = re.compile(rf"#+([\w{_INDIC}]+)", re.UNICODE)
MEDIA_TIMEOUT = 15.0
MEDIA_URL_DEADLINE = 30.0
MAX_MEDIA_PER_POST = 4
MEDIA_CACHE_PREFIX = "media:url:"
MEDIA_CACHE_TTL = 14 * 24 * 3600
MEDIA_FAIL_MARKER = "-"
MEDIA_FAIL_TTL = 900

_STATE_HINTS: dict[str, str] = {}


def _state_index() -> dict[str, str]:
    if not _STATE_HINTS:
        for city in all_cities():
            _STATE_HINTS[city.state.lower()] = city.state
    return _STATE_HINTS


def extract_hashtags(text: str) -> list[str]:
    return [f"#{m}" for m in HASHTAG_RE.findall(text)]


def detect_lang(text: str) -> str | None:
    try:
        return detect(text)
    except LangDetectException:
        return None


def geocode(post: RawPost) -> tuple[City | None, str]:
    if post.lat is not None and post.lon is not None:
        city = nearest_city(post.lat, post.lon)
        if city is not None:
            return city, "gps"
    if post.city_hint:
        city = find_city_by_name(post.city_hint)
        if city is not None:
            return city, "hint"
    text = post.text.lower()
    for city in sorted(all_cities(), key=lambda c: -len(c.name)):
        if len(city.name) >= 4 and city.name.lower() in text:
            return city, "text"
    norm_text = re.sub(r"[^a-z0-9\u0900-\u097f]+", "", text)
    for alias, city in city_aliases().items():
        if alias not in norm_text:
            continue
        if (alias.isascii() and len(alias) >= 5) or (
            not alias.isascii() and len(alias) >= 4
        ):
            return city, "text"
    for alias, state_name in state_aliases().items():
        if alias in norm_text and (
            (alias.isascii() and len(alias) >= 5) or (not alias.isascii() and len(alias) >= 4)
        ):
            return City(name=state_name, state=state_name, district="", lat=0.0, lon=0.0), "text"
    for key, state_name in _state_index().items():
        if len(key) >= 5 and re.sub(r"[^a-z0-9]+", "", key) in norm_text:
            return City(name=state_name, state=state_name, district="", lat=0.0, lon=0.0), "text"
    return None, "none"


async def _fetch_one(client: httpx.AsyncClient, url: str, post: RawPost) -> MediaRef | None:
    async with client.stream("GET", url) as resp:
        if resp.status_code != 200:
            return None
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
        if ctype not in objectstore.ALLOWED_TYPES:
            return None
        limit = (
            objectstore.settings.media_max_image_bytes
            if ctype in objectstore.ALLOWED_IMAGE
            else objectstore.settings.media_max_video_bytes
        )
        chunks: list[bytes] = []
        size = 0
        async for chunk in resp.aiter_bytes():
            size += len(chunk)
            if size > limit:
                chunks = []
                break
            chunks.append(chunk)
        if not chunks:
            return None
        data = b"".join(chunks)
        key = objectstore.media_key(post.source, ctype, data)
        await asyncio.to_thread(objectstore.put_bytes, key, data, ctype)
        return MediaRef(
            bucket=objectstore.settings.minio_bucket,
            key=key,
            content_type=ctype,
            sha256=objectstore.sha256(data),
            size=len(data),
            source_url=url,
        )


def _cache_key(url: str) -> str:
    return MEDIA_CACHE_PREFIX + hashlib.sha256(url.encode("utf-8")).hexdigest()


async def _cache_lookup(url: str) -> tuple[str | None, MediaRef | None]:
    try:
        raw = await cache_get(_cache_key(url))
    except Exception:
        return None, None
    if not raw or raw == MEDIA_FAIL_MARKER:
        return raw, None
    ref: MediaRef | None = None
    with contextlib.suppress(Exception):
        candidate = MediaRef.model_validate_json(raw)
        if await asyncio.to_thread(objectstore.exists, candidate.key):
            ref = candidate
    return raw, ref


async def _mark_dead(url: str) -> None:
    with contextlib.suppress(Exception):
        await cache_set(_cache_key(url), MEDIA_FAIL_MARKER, ttl=MEDIA_FAIL_TTL)


async def _fetch_guarded(
    client: httpx.AsyncClient, url: str, post: RawPost
) -> MediaRef | None:
    raw, cached = await _cache_lookup(url)
    if raw == MEDIA_FAIL_MARKER:
        return None
    if cached is not None:
        return cached
    try:
        ref = await asyncio.wait_for(
            _fetch_one(client, url, post), timeout=MEDIA_URL_DEADLINE
        )
    except TimeoutError:
        log.warning(
            q(f"[enrich] media deadline {MEDIA_URL_DEADLINE:.0f}s: {url[:80]}")
        )
        await _mark_dead(url)
        return None
    except Exception as exc:
        log.debug(q(f"[enrich] media download failed {url[:80]}: {exc}"))
        await _mark_dead(url)
        return None
    if ref is not None:
        with contextlib.suppress(Exception):
            await cache_set(
                _cache_key(url), ref.model_dump_json(), ttl=MEDIA_CACHE_TTL
            )
    return ref


async def download_media(post: RawPost) -> list[MediaRef]:
    urls = (post.media_urls or [])[:MAX_MEDIA_PER_POST]
    if not urls:
        return []
    async with http_client(timeout=MEDIA_TIMEOUT) as client:
        results = await asyncio.gather(
            *(_fetch_guarded(client, url, post) for url in urls)
        )
    return [r for r in results if r is not None]


async def _media_already_sunk(raw: RawPost) -> bool:
    try:
        async with session_scope() as session:
            res = await session.execute(
                select(Report.media).where(
                    Report.source == raw.source,
                    Report.external_id == raw.external_id,
                )
            )
            row = res.first()
            return row is not None and bool(row[0])
    except Exception as exc:
        log.warning(q(f"[enrich] sunk-media check failed: {exc}"))
        return False


async def handle(message: dict[str, Any]) -> EnrichedPost:
    raw = RawPost.model_validate(message)

    lang = raw.lang or detect_lang(raw.text)

    seen: dict[str, str] = {}
    for tag in list(raw.hashtags) + extract_hashtags(clean_html(raw.text)):
        key = tag.lower()
        seen.setdefault(key, tag)
    hashtags = list(seen.values())

    city, method = geocode(raw)
    state_only = city is not None and not city.lat and not city.lon
    resolved_city = None if state_only else city

    media: list[MediaRef] = []
    for item in (raw.model_extra or {}).get("media") or []:
        try:
            media.append(MediaRef.model_validate(item))
        except Exception:
            continue
    if raw.media_urls and not await _media_already_sunk(raw):
        media.extend(await download_media(raw))

    overridden = {"media", "lang", "hashtags", "lat", "lon"}
    base = {k: v for k, v in raw.model_dump().items() if k not in overridden}
    return EnrichedPost(
        **base,
        lang=lang,
        hashtags=hashtags,
        city=resolved_city.name if resolved_city else None,
        district=resolved_city.district if resolved_city and resolved_city.district else None,
        state=(city.state if city else None) or raw.state_hint,
        media=media,
        geocode_method=method,
        lat=raw.lat if raw.lat is not None else (resolved_city.lat if resolved_city else None),
        lon=raw.lon if raw.lon is not None else (resolved_city.lon if resolved_city else None),
    )


def main() -> None:
    stage = Stage("enrich", T.RAW_POSTS, T.ENRICHED_POSTS, handle)
    asyncio.run(stage.run())


if __name__ == "__main__":
    main()
