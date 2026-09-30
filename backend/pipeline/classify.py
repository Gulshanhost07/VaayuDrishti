
from __future__ import annotations

import asyncio
from typing import Any

from ml.classify import classify_text
from ml.classify.credibility import score as credibility_score
from ml.classify.plausibility import check as plausibility_check
from pipeline.run_stage import Stage
from shared import topics as T
from shared.logging import q, setup_logging
from shared.redis_client import incr_counter
from shared.schemas import ClassifiedPost, DedupedPost

log = setup_logging("pipeline.classify")


def _rebuild(post: DedupedPost, **updates: Any) -> ClassifiedPost:
    payload = post.model_dump()
    payload.pop("stage", None)
    return ClassifiedPost(**payload, **updates)


async def handle(message: dict[str, Any]) -> ClassifiedPost:
    post = DedupedPost.model_validate(message)

    result = classify_text(post.text)
    cred, features = credibility_score(post)
    features["matched_terms"] = result.matched_terms
    features["rule_scores"] = result.scores

    location_key = post.city or post.state or ""
    plaus = await plausibility_check(
        result.category,
        post.lat,
        post.lon,
        post.observed_at,
        location_key=location_key,
    )

    enriched = _rebuild(
        post,
        event_category=result.category,
        category_confidence=result.confidence,
        severity=result.severity,
        credibility_score=cred,
        credibility_features=features,
        plausibility=plaus,
    )
    await incr_counter("classify_done")
    log.debug(
        q(
            f"[classify] {post.source}:{post.external_id} -> {result.category} "
            f"conf={result.confidence} sev={result.severity} cred={cred}"
        )
    )
    return enriched


def main() -> None:
    stage = Stage("classify", T.DEDUPED_POSTS, T.CLASSIFIED_POSTS, handle)
    asyncio.run(stage.run())


if __name__ == "__main__":
    main()
