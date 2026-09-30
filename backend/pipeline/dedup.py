
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import zlib
from typing import Any

from pipeline.run_stage import Stage
from shared import topics as T
from shared.logging import setup_logging
from shared.redis_client import get_redis, incr_counter
from shared.schemas import DedupedPost, EnrichedPost

log = setup_logging("pipeline.dedup")

TTL_SECONDS = 7 * 24 * 3600
SIG_LEN = 64
BANDS = 16
BAND_ROWS = SIG_LEN // BANDS
JACCARD_THRESHOLD = 0.85
MIN_LEN_FOR_NEAR = 20
SHINGLE_K = 4
DOC_MAX_CHARS = 1500

_MERSENNE = (1 << 61) - 1
_RND = random.Random(20260930)
_A = [_RND.randrange(1, _MERSENNE) for _ in range(SIG_LEN)]
_B = [_RND.randrange(0, _MERSENNE) for _ in range(SIG_LEN)]

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
_KEEP_RE = re.compile(r"[^a-z0-9\u0900-\u097f]+")


def normalize(text: str) -> str:
    t = text.lower()
    t = _URL_RE.sub(" ", t)
    t = _KEEP_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip()


def content_hash(norm_text: str) -> str:
    return hashlib.sha256(norm_text.encode("utf-8")).hexdigest()


def shingles(norm_text: str, k: int = SHINGLE_K) -> set[str]:
    if len(norm_text) < k:
        return {norm_text} if norm_text else set()
    return {norm_text[i : i + k] for i in range(len(norm_text) - k + 1)}


def minhash(shingle_set: set[str]) -> list[int]:
    sig = [_MERSENNE] * SIG_LEN
    for sh in shingle_set:
        h1 = zlib.crc32(sh.encode("utf-8"))
        h2 = zlib.crc32(sh.encode("utf-8"), 0x9E3779B9)
        for i in range(SIG_LEN):
            v = (_A[i] * h1 + _B[i] * h2) % _MERSENNE
            if v < sig[i]:
                sig[i] = v
    return sig


def band_keys(sig: list[int]) -> list[str]:
    keys: list[str] = []
    for b in range(BANDS):
        chunk = ",".join(str(v) for v in sig[b * BAND_ROWS : (b + 1) * BAND_ROWS])
        keys.append(hashlib.blake2b(chunk.encode(), digest_size=8).hexdigest())
    return keys


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _rebuild(post: EnrichedPost, **updates: Any) -> DedupedPost:
    payload = post.model_dump()
    payload.pop("stage", None)
    return DedupedPost(**payload, **updates)


async def handle(message: dict[str, Any]) -> DedupedPost:
    post = EnrichedPost.model_validate(message)
    key = f"{post.source}:{post.external_id}"
    norm = normalize(post.text)
    digest = content_hash(norm)

    r = get_redis()
    try:
        exact = await r.get(f"dedup:hash:{digest}")
        if exact and exact != key:
            await incr_counter("dedup_exact")
            return _rebuild(post, is_duplicate=True, duplicate_of=exact, dedup_score=1.0)

        sig: list[int] | None = None
        keys: list[str] = []
        if len(norm) >= MIN_LEN_FOR_NEAR:
            sh = shingles(norm)
            sig = minhash(sh)
            keys = band_keys(sig)
            for i, bkey in enumerate(keys):
                cand = await r.get(f"dedup:lsh:{i}:{bkey}")
                if not cand or cand == key:
                    continue
                doc = await r.get(f"dedup:doc:{cand}")
                other_norm = ""
                if doc:
                    try:
                        other_norm = json.loads(doc).get("t", "")
                    except (ValueError, TypeError):
                        other_norm = ""
                if not other_norm:
                    continue
                jac = jaccard(sh, shingles(other_norm))
                if jac >= JACCARD_THRESHOLD:
                    await incr_counter("dedup_near")
                    return _rebuild(
                        post,
                        is_duplicate=True,
                        duplicate_of=cand,
                        dedup_score=round(jac, 3),
                    )

        pipe = r.pipeline(transaction=False)
        pipe.set(f"dedup:hash:{digest}", key, ex=TTL_SECONDS)
        if sig is not None:
            for i, bkey in enumerate(keys):
                pipe.set(f"dedup:lsh:{i}:{bkey}", key, ex=TTL_SECONDS, nx=True)
        pipe.set(
            f"dedup:doc:{key}",
            json.dumps({"t": norm[:DOC_MAX_CHARS]}, ensure_ascii=False),
            ex=TTL_SECONDS,
        )
        await pipe.execute()
        await incr_counter("dedup_unique")
        return _rebuild(post, is_duplicate=False, duplicate_of=None, dedup_score=None)
    finally:
        await r.aclose()


def main() -> None:
    stage = Stage("dedup", T.ENRICHED_POSTS, T.DEDUPED_POSTS, handle)
    asyncio.run(stage.run())


if __name__ == "__main__":
    main()
