
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from ml.geocode import load_credibility_lexicon
from shared.schemas import ClassifiedPost, DedupedPost

SOURCE_WEIGHTS: dict[str, float] = {
    "imd": 0.95,
    "open_meteo": 0.92,
    "dataset": 0.90,
    "rss": 0.72,
    "citizen": 0.60,
    "mastodon": 0.55,
    "twitter": 0.55,
    "reddit": 0.45,
    "simulator": 0.50,
}

_REPEATED_TOKEN = re.compile(r"\b(\w{4,})\s+\1\s+\1", re.IGNORECASE)
_URL = re.compile(r"https?://", re.IGNORECASE)
_OFFICIAL_DOMAIN = re.compile(
    r"\b(?:[a-z0-9-]+\.)*(?:gov\.in|nic\.in|imd\.gov\.in|noaa\.gov|weather\.gov)\b",
    re.IGNORECASE,
)


@lru_cache
def _lexicon() -> tuple[tuple[float, str], ...]:
    return tuple(load_credibility_lexicon())


def score(post: DedupedPost | ClassifiedPost) -> tuple[float, dict[str, Any]]:
    text = post.text
    low = text.lower()

    source_weight = SOURCE_WEIGHTS.get(post.source, 0.5)
    has_location = bool(post.city or post.state or post.lat is not None)
    has_media = bool(post.media)
    has_url = bool(post.source_url or _URL.search(text))
    official_domain = bool(_OFFICIAL_DOMAIN.search(text))
    letters = [ch for ch in text if ch.isalpha()]
    caps_ratio = (sum(1 for ch in letters if ch.isupper()) / len(letters)) if letters else 0.0
    exclamations = text.count("!") + text.count("?")

    lex_hits: list[str] = []
    lex_raw = 0.0
    for weight, term in _lexicon():
        if term in low:
            lex_raw += weight
            if len(lex_hits) < 20:
                lex_hits.append(term)
    lex_delta = max(-0.25, min(0.25, -lex_raw))

    s = 0.15 + 0.35 * source_weight
    if has_location:
        s += 0.12
    if has_media:
        s += 0.06
    if official_domain:
        s += 0.15
    elif has_url:
        s += 0.02
    if post.lang:
        s += 0.05
    if 40 <= len(text) <= 2000:
        s += 0.05
    s += lex_delta
    if caps_ratio > 0.5 and len(text) > 30:
        s -= 0.12
    if exclamations >= 3:
        s -= 0.10
    if _REPEATED_TOKEN.search(text):
        s -= 0.08
    if len(text) < 40:
        s -= 0.05

    score_value = round(max(0.05, min(0.98, s)), 3)
    features: dict[str, Any] = {
        "source": post.source,
        "source_weight": source_weight,
        "has_location": has_location,
        "has_media": has_media,
        "has_source_url": has_url,
        "official_domain": official_domain,
        "has_lang": bool(post.lang),
        "text_length": len(text),
        "caps_ratio": round(caps_ratio, 3),
        "exclamation_count": exclamations,
        "repeated_token": bool(_REPEATED_TOKEN.search(text)),
        "lexicon_hits": lex_hits,
        "lexicon_delta": round(lex_delta, 3),
    }
    return score_value, features
