
from __future__ import annotations

from datetime import UTC, datetime

from ml.classify import credibility_score
from shared.schemas import DedupedPost


def _post(text: str) -> DedupedPost:
    return DedupedPost(
        source="mastodon",
        external_id="c-1",
        text=text,
        observed_at=datetime.now(UTC),
        stage="deduped",
        is_duplicate=False,
        duplicate_of=None,
    )


def test_trusted_beats_spammy() -> None:
    trusted, _ = credibility_score(
        _post(
            "IMD issues orange warning for heavy rainfall over coastal Karnataka, "
            "visit mausam.imd.gov.in for advisories"
        )
    )
    spammy, _ = credibility_score(
        _post(
            "BREAKING free money now click http://bit.ly/xyz WIN WIN WIN "
            "guaranteed 100% follow me follow me follow me follow me"
        )
    )
    assert trusted > spammy
    assert trusted >= 0.5
    assert spammy <= 0.5


def test_score_bounds_and_features() -> None:
    value, features = credibility_score(_post("Light drizzle reported this afternoon"))
    assert 0.0 <= value <= 1.0
    assert features
    assert any(isinstance(v, (int, float)) for v in features.values())


def test_url_and_official_domain_features() -> None:
    _, spam_features = credibility_score(
        _post("SHOCKING WEATHER SECRET!!! http://spam.example/click now now now")
    )
    assert spam_features["has_source_url"] is True
    assert spam_features["official_domain"] is False
    _, official_features = credibility_score(
        _post("IMD district warning for Pune issued by mausam.imd.gov.in")
    )
    assert official_features["official_domain"] is True
