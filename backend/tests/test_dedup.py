
from __future__ import annotations

from datetime import UTC, datetime

from pipeline.dedup import (
    BANDS,
    JACCARD_THRESHOLD,
    SIG_LEN,
    _rebuild,
    band_keys,
    content_hash,
    jaccard,
    minhash,
    normalize,
    shingles,
)
from shared.schemas import EnrichedPost


def test_normalize_strips_urls_and_case() -> None:
    a = normalize("Heavy Rain! https://t.co/abc #IMD")
    b = normalize("heavy rain #IMD")
    assert a == b


def test_content_hash_distinct() -> None:
    assert content_hash(normalize("rain in Mumbai")) != content_hash(
        normalize("fog in Delhi")
    )


def test_shingle_jaccard_near_duplicate() -> None:
    a = shingles(normalize("Heavy rain lashing Mumbai since morning"))
    b = shingles(normalize("Heavy rain lashing Mumbai since morning!"))
    c = shingles(normalize("Dense fog covers Delhi airport runway"))
    assert jaccard(a, b) >= JACCARD_THRESHOLD
    assert jaccard(a, c) < 0.3


def test_minhash_deterministic_and_banded() -> None:
    sh = shingles(normalize("Severe thunderstorm warning for coastal Karnataka"))
    sig = minhash(sh)
    assert len(sig) == SIG_LEN
    assert sig == minhash(sh)
    keys = band_keys(sig)
    assert len(keys) == BANDS
    assert keys == band_keys(minhash(sh))


def test_jaccard_edge_cases() -> None:
    assert jaccard(set(), set()) == 0.0
    assert jaccard({"a"}, {"a"}) == 1.0


def _enriched(text: str, ext: str) -> EnrichedPost:
    return EnrichedPost(
        source="simulator",
        external_id=ext,
        text=text,
        observed_at=datetime.now(UTC),
        stage="enriched",
    )


def test_rebuild_produces_deduped_stage() -> None:
    out = _rebuild(_enriched("rain", "1"), is_duplicate=True, duplicate_of="rss:9")
    assert out.stage == "deduped"
    assert out.is_duplicate is True
    assert out.duplicate_of == "rss:9"
