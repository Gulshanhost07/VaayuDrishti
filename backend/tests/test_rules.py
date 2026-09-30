
from __future__ import annotations

import pytest

from ml.classify import CATEGORIES, classify_text

SAMPLES = [
    ("rainfall", "Heavy rain lashing Mumbai since morning, 120mm recorded in 6 hours"),
    ("rainfall", "भारी बारिश के कारण मुंबई में जनजीवन प्रभावित, 150 मिमी बारिश"),
    ("flooding", "Flash floods after river overflow, evacuation underway in Patna"),
    ("flooding", "बिहार में बाढ़ की स्थिति, तटबंध टूटने से कई गांव जलमग्न"),
    ("thunderstorm", "Severe thunderstorm with lightning strikes damages houses in Delhi"),
    ("thunderstorm", "वज्रपात से दो की मौत, गरज के साथ बौछार जारी"),
    ("heatwave", "Heatwave continues, temperature crosses 44C in Churu"),
    ("heatwave", "राजस्थान में लू का कहर, तापमान 45 डिग्री"),
    ("fog", "Dense fog disrupts flight operations, visibility below 50 metres"),
    ("fog", "घना कोहरा, शून्य दृश्यता के कारण रेल यातायात प्रभावित"),
    ("dust_storm", "Dust storm warning issued for western Rajasthan"),
    ("dust_storm", "धूल भरी आंधी की चेतावनी जारी, धूल से आंखों में जलन"),
    ("strong_winds", "Gusty winds at 60 kmph uproot trees across Kolkata"),
    ("strong_winds", "तेज हवा के साथ आंधी, कई जगह पेड़ गिरे"),
    ("other", "Weather looks pleasant for a picnic this weekend in Bengaluru"),
]


@pytest.mark.parametrize(("expected", "text"), SAMPLES)
def test_classifies_expected_category(expected: str, text: str) -> None:
    result = classify_text(text)
    assert result.category == expected, (
        f"expected {expected}, got {result.category} "
        f"scores={result.scores} terms={result.matched_terms}"
    )
    assert result.confidence >= 0.3
    assert result.confidence <= 0.97
    assert result.category in CATEGORIES


def test_fallback_is_other_with_low_confidence() -> None:
    result = classify_text("I like long walks and cold coffee in the evening")
    assert result.category == "other"
    assert result.confidence <= 0.35
    assert result.severity == "unknown"


def test_extreme_severity_for_record_wording() -> None:
    result = classify_text("Cloudburst triggers flash floods, 300mm in 24 hours")
    assert result.category in ("flooding", "rainfall")
    assert result.severity in ("extreme", "severe")


def test_scores_dict_covers_all_categories() -> None:
    result = classify_text("thunder and lightning today")
    assert set(result.scores) == set(CATEGORIES)


def test_explainable_terms_returned() -> None:
    result = classify_text("dense fog disrupts operations")
    assert result.matched_terms
