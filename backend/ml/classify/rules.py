
from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORIES = (
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_winds",
    "other",
)


def _r(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


@dataclass(frozen=True, slots=True)
class Rule:
    category: str
    weight: float
    tier: int
    term: str
    pattern: re.Pattern[str]


RULES: tuple[Rule, ...] = (
    Rule("rainfall", 1.0, 0, "rain", _r(r"\brain(?:s|fall|ing|y|fed)?\b")),
    Rule("rainfall", 1.0, 0, "बारिश/वर्षा", _r(r"बारिश|वर्षा")),
    Rule("rainfall", 1.5, 1, "heavy rain", _r(r"\b(?:heavy|intense|lashing|battering) rain\b")),
    Rule("rainfall", 1.5, 1, "भारी बारिश", _r(r"भारी\s*बारिश|तेज़\s*बारिश")),
    Rule(
        "rainfall",
        1.8,
        2,
        "cloudburst/torrential",
        _r(r"\b(?:cloudburst|torrential|extreme rain)\b"),
    ),
    Rule("rainfall", 1.8, 2, "मूसलाधार बारिश", _r(r"मूसलाधार|भीषण\s*बारिश")),
    Rule("rainfall", 0.7, 0, "showers/drizzle", _r(r"\b(?:showers?|drizzle)\b")),
    Rule("rainfall", 0.7, 0, "बौछार/रिमझिम", _r(r"बौछार|रिमझिम")),
    Rule("rainfall", 0.6, 0, "monsoon", _r(r"\bmonsoon(?:al)?\b|मानसून")),
    Rule(
        "rainfall",
        1.2,
        0,
        "rainfall mm",
        _r(r"\b\d{1,4}(?:\.\d+)?\s*mm\b|\bmillimet(?:er|re)s? of rain\b"),
    ),
    Rule("flooding", 2.2, 1, "flood", _r(r"\bflood(?:s|ed|ing)?\b")),
    Rule("flooding", 2.2, 1, "बाढ़", _r(r"बाढ़")),
    Rule(
        "flooding",
        1.8,
        1,
        "waterlogging/inundation",
        _r(r"\b(?:waterlog\w*|inundat\w*|submerged)\b"),
    ),
    Rule("flooding", 1.8, 1, "जलभराव/डूब", _r(r"जलभराव|पानी\s*भर|डूब\s*(?:गए|गयी|गया)")),
    Rule("flooding", 2.0, 2, "flash flood", _r(r"\bflash floods?\b")),
    Rule(
        "flooding",
        2.0,
        2,
        "embankment/river breach",
        _r(r"\b(?:embankment|riverbank|levee)\w*.{0,25}\b(?:breach\w*|burst|overflow)\b"),
    ),
    Rule("flooding", 2.0, 2, "तटबंध टूटना", _r(r"तटबंध.{0,12}टूट|नदी.{0,20}उफन")),
    Rule(
        "flooding",
        1.6,
        1,
        "rain-caused flooding",
        _r(r"(?:rain\w*|downpour|बारिश).{0,50}\bflood|flood.{0,50}(?:rain\w*|downpour|बारिश)"),
    ),
    Rule("flooding", 0.8, 0, "relief/evacuation", _r(r"\b(?:relief camps?|evacuat\w+)\b")),
    Rule("flooding", 0.8, 0, "राहत शिविर", _r(r"राहत\s*शिविर")),
    Rule(
        "thunderstorm",
        1.6,
        0,
        "thunder/lightning",
        _r(r"\b(?:thunder(?:storm|s|ing)?|lightning)\b"),
    ),
    Rule("thunderstorm", 1.6, 0, "गरज/बिजली चमक", _r(r"गरज|बिजली\s*चमक|तड़ित")),
    Rule("thunderstorm", 1.7, 1, "lightning strike/वज्रपात", _r(r"\blightning strikes?\b|वज्रपात")),
    Rule("thunderstorm", 1.3, 1, "severe thunderstorm", _r(r"\bsevere thunderstorms?\b")),
    Rule("thunderstorm", 0.9, 0, "thunder shower", _r(r"\bthunder showers?\b")),
    Rule("thunderstorm", 0.9, 0, "गरज के साथ बौछार", _r(r"गरज.{0,12}बौछार")),
    Rule("heatwave", 1.9, 1, "heatwave", _r(r"\bheat[ -]?waves?\b")),
    Rule("heatwave", 1.9, 1, "लू", _r(r"लू")),
    Rule("heatwave", 1.5, 1, "scorching/loo", _r(r"\b(?:scorching|blazing|searing|loo)\b")),
    Rule("heatwave", 1.5, 1, "उष्ण/गर्म लहर", _r(r"उष्ण|भीषण\s*गर्मी|गर्म\s*लहर")),
    Rule(
        "heatwave",
        1.7,
        1,
        "40C+",
        _r(r"\b4[0-9](?:\.\d)?\s*°\s*c\b|\btemperature (?:of |at |reaches? |hits? )?4[0-9]"),
    ),
    Rule(
        "heatwave",
        1.4,
        1,
        "sunstroke/heat stress",
        _r(r"\b(?:sunstroke|heat stroke|heat stress)\b"),
    ),
    Rule("heatwave", 0.8, 0, "sweltering weather", _r(r"\b(?:sweltering|humid|hot) weather\b")),
    Rule("heatwave", 0.7, 0, "गर्मी", _r(r"गर्मी")),
    Rule(
        "fog",
        1.5,
        0,
        "fog/mist/smog",
        _r(r"\b(?:fog|foggy|mists?|misty|smog|smoggy)\b"),
    ),
    Rule("fog", 1.5, 0, "कोहरा/धुंध", _r(r"कोहर|धुंध|धुएँ")),
    Rule(
        "fog",
        1.7,
        1,
        "dense fog/low visibility",
        _r(r"\b(?:dense|thick|heavy) fog\b|\b(?:zero|poor|reduced|low) visibility\b"),
    ),
    Rule("fog", 1.7, 1, "घना कोहरा", _r(r"घना\s*कोहरा|शून्य\s*दृश्यता")),
    Rule(
        "dust_storm",
        1.9,
        1,
        "dust/sandstorm",
        _r(r"\b(?:dust ?storms?|sandstorms?|dusty storms?)\b"),
    ),
    Rule(
        "dust_storm",
        1.9,
        1,
        "धूल भरी आंधी",
        _r(r"धूल\s*भरी\s*आंधी|धूल\s*का\s*तूफान|रेतीला\s*तूफान"),
    ),
    Rule("dust_storm", 0.9, 0, "dust/haze", _r(r"\b(?:dust|hazes?|dust-laden|dusty)\b")),
    Rule("dust_storm", 1.0, 0, "धूल", _r(r"धूल")),
    Rule(
        "strong_winds",
        1.5,
        1,
        "strong winds/gusts/gale",
        _r(r"\b(?:strong winds?|gusts?|gusty|gales?|squalls?)\b"),
    ),
    Rule(
        "strong_winds",
        1.5,
        1,
        "winds at NN kmph",
        _r(r"\bwinds?\s+(?:of\s+|at\s+)?\d{2,3}\s*(?:km/?h|kph|kmph|miles)\b"),
    ),
    Rule("strong_winds", 1.5, 1, "तेज हवा", _r(r"तेज़?\s*हवा|हवा\s*की\s*रफ्तार")),
    Rule("strong_winds", 1.5, 1, "आंधी/तूफान", _r(r"आंधी|तूफान")),
    Rule("strong_winds", 1.0, 0, "storm", _r(r"\bstorm(?:s|y)?\b")),
    Rule("strong_winds", 0.7, 0, "wind", _r(r"\bwind(?:s|y)?\b")),
    Rule("strong_winds", 0.7, 0, "हवा", _r(r"हवा")),
)


@dataclass(slots=True)
class CategoryResult:
    category: str
    confidence: float
    severity: str
    matched_terms: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


def _severity(tier: int, top_weight: float) -> str:
    if tier >= 2:
        return "extreme"
    if tier == 1 or top_weight >= 2.0:
        return "severe"
    if top_weight >= 1.0:
        return "moderate"
    return "mild"


def classify_text(text: str) -> CategoryResult:
    hits: dict[str, float] = {}
    tiers: dict[str, int] = {}
    terms: list[str] = []
    for rule in RULES:
        if rule.pattern.search(text):
            hits[rule.category] = hits.get(rule.category, 0.0) + rule.weight
            tiers[rule.category] = max(tiers.get(rule.category, 0), rule.tier)
            terms.append(rule.term)

    scores = {c: round(hits.get(c, 0.0), 2) for c in CATEGORIES}
    if not hits:
        return CategoryResult("other", 0.3, "unknown", [], scores)

    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    top_cat, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = (top - second) / top if top else 0.0
    confidence = 0.45 + 0.45 * margin + 0.05 * min(top, 3.0) / 3.0
    if top < 1.0:
        confidence = min(confidence, 0.5)
    confidence = round(min(0.97, max(0.3, confidence)), 3)

    return CategoryResult(
        category=top_cat,
        confidence=confidence,
        severity=_severity(tiers[top_cat], top),
        matched_terms=list(dict.fromkeys(terms)),
        scores=scores,
    )
