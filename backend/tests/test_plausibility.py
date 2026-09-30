
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ml.classify.plausibility import RULES, check, haversine_km


def test_rule_coverage() -> None:
    assert set(RULES) >= {"rainfall", "flooding", "heatwave", "strong_winds"}
    for metric, threshold, op, label in RULES.values():
        assert metric in {"precip_mm", "temp_c", "wind_kph", "humidity_pct"}
        assert threshold > 0
        assert op in {">=", "<="}
        assert label


@pytest.mark.asyncio
async def test_category_without_rule() -> None:
    verdict = await check("fog", 28.6, 77.2, datetime.now(UTC))
    assert verdict == {"checked": False, "reason": "no_reference_rule"}


@pytest.mark.asyncio
async def test_missing_location_short_circuits() -> None:
    verdict = await check("rainfall", None, None, None)
    assert verdict == {"checked": False, "reason": "no_location"}


def test_haversine_known_distance() -> None:
    km = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < km < 1200
    assert haversine_km(19.0760, 72.8777, 19.0760, 72.8777) == pytest.approx(0.0)
