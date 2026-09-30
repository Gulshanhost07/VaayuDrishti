
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shared.schemas import (
    CitizenReportIn,
    ClassifiedPost,
    DedupedPost,
    EnrichedPost,
)


def _base(text: str) -> dict:
    return {
        "source": "mastodon",
        "external_id": "m-1",
        "text": text,
        "observed_at": datetime.now(UTC),
    }


def test_enriched_defaults() -> None:
    p = EnrichedPost(**_base("heavy rain"))
    assert p.stage == "enriched"
    assert p.lang is None
    assert p.geocode_method is None
    assert p.city is None


def test_enriched_to_deduped_chain() -> None:
    e = EnrichedPost(**_base("heavy rain"))
    data = e.model_dump()
    data["stage"] = "deduped"
    d = DedupedPost(**data, is_duplicate=False, duplicate_of=None)
    assert d.stage == "deduped"
    assert d.is_duplicate is False


def test_deduped_to_classified_chain() -> None:
    e = EnrichedPost(**_base("flash floods in Patna"))
    d_data = e.model_dump()
    d_data["stage"] = "deduped"
    d = DedupedPost(**d_data, is_duplicate=False, duplicate_of=None)
    c_data = d.model_dump()
    c_data["stage"] = "classified"
    c = ClassifiedPost(
        **c_data,
        event_category="flooding",
        credibility=0.8,
        severity="severe",
        matched_terms=["flood"],
    )
    assert c.stage == "classified"
    assert c.severity == "severe"
    assert c.event_category == "flooding"


def test_classified_rejects_bad_severity() -> None:
    with pytest.raises(ValidationError):
        ClassifiedPost(
            **_base("x"),
            stage="classified",
            event_category="other",
            credibility=0.5,
            severity="catastrophic",
        )


def test_citizen_report_min_length() -> None:
    with pytest.raises(ValidationError):
        CitizenReportIn(text="short", lat=28.6, lon=77.2, city="Delhi")


def test_citizen_report_rejects_bad_category() -> None:
    with pytest.raises(ValidationError):
        CitizenReportIn(
            text="very heavy rain on the main road and waterlogging everywhere",
            city="Delhi",
            event_category="meteor",
        )


def test_citizen_report_ok() -> None:
    r = CitizenReportIn(
        text="very heavy rain and waterlogging on the main road",
        lat=28.61,
        lon=77.21,
        city="Delhi",
        state="DL",
        event_category="rainfall",
    )
    assert r.city == "Delhi"
    assert r.event_category == "rainfall"
