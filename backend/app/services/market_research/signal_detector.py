"""Deterministic trend and demand detectors.

Scoring replaces the legacy first-regex-wins behavior. A single weak token
does not dominate mixed evidence, and more specific phrases are applied
before overlapping weaker ones.
"""

from __future__ import annotations

import re

from app.models.enums import DemandLevel, MarketTrend

_SLOW_LOGISTICS_RE = re.compile(
    r"\bslow\s+(shipping|delivery|transit|freight)\b",
    re.IGNORECASE,
)

_TREND_SURGING = [
    (re.compile(r"\bsurging\b", re.I), 3),
    (re.compile(r"\bbooming\b", re.I), 3),
    (re.compile(r"\bskyrocketing\b", re.I), 3),
    (re.compile(r"\bskyrocket(?:s|ed|ing)?\b", re.I), 3),
    (re.compile(r"\brapid(?:ly)?\s+growth\b", re.I), 3),
    (re.compile(r"\brapidly\s+growing\b", re.I), 3),
]
_TREND_GROWING = [
    (re.compile(r"\bgrowing\b", re.I), 2),
    (re.compile(r"\brising\b", re.I), 2),
    (re.compile(r"\bincreasing\b", re.I), 2),
    (re.compile(r"\buptick\b", re.I), 2),
    (re.compile(r"\bupward\b", re.I), 2),
]
_TREND_DECLINING = [
    (re.compile(r"\bdeclining\b", re.I), 2),
    (re.compile(r"\bshrinking\b", re.I), 2),
    (re.compile(r"\bfalling\b", re.I), 2),
    (re.compile(r"\bdecreasing\b", re.I), 2),
    (re.compile(r"\bdeclined\b", re.I), 2),
    (re.compile(r"\bshrank\b", re.I), 2),
]

_DEMAND_VERY_HIGH = [
    (re.compile(r"\bvery high demand\b", re.I), 4),
    (re.compile(r"\bhuge demand\b", re.I), 4),
    (re.compile(r"\bselling fast\b", re.I), 4),
    (re.compile(r"\bextremely popular\b", re.I), 4),
]
_DEMAND_VERY_LOW = [
    (re.compile(r"\bvery low demand\b", re.I), 4),
    (re.compile(r"\blittle interest\b", re.I), 4),
    (re.compile(r"\bminimal demand\b", re.I), 4),
]
_DEMAND_HIGH = [
    (re.compile(r"\bhigh demand\b", re.I), 2),
    (re.compile(r"\bstrong demand\b", re.I), 2),
    (re.compile(r"\bwidely sought\b", re.I), 2),
    (re.compile(r"\bpopular\b", re.I), 1),
]
_DEMAND_LOW = [
    (re.compile(r"\blow demand\b", re.I), 2),
    (re.compile(r"\blimited demand\b", re.I), 2),
    (re.compile(r"\bniche\b", re.I), 2),
]


def detect_trend(text: str) -> MarketTrend:
    if not text or not text.strip():
        return MarketTrend.STABLE

    remaining = text
    surging, remaining = _score_and_mask(remaining, _TREND_SURGING)
    growing, remaining = _score_and_mask(remaining, _TREND_GROWING)
    declining, remaining = _score_and_mask(remaining, _TREND_DECLINING)

    positive = surging + growing
    if positive == 0 and declining == 0:
        return MarketTrend.STABLE
    if positive > 0 and declining > 0 and abs(positive - declining) <= 1:
        return MarketTrend.STABLE
    if declining > positive:
        return MarketTrend.DECLINING
    if surging > growing:
        return MarketTrend.SURGING
    if growing > 0:
        return MarketTrend.GROWING
    return MarketTrend.STABLE


def detect_demand(text: str) -> DemandLevel:
    if not text or not text.strip():
        return DemandLevel.MODERATE

    remaining = _SLOW_LOGISTICS_RE.sub(" ", text)
    very_high, remaining = _score_and_mask(remaining, _DEMAND_VERY_HIGH)
    very_low, remaining = _score_and_mask(remaining, _DEMAND_VERY_LOW)
    high, remaining = _score_and_mask(remaining, _DEMAND_HIGH)
    low, remaining = _score_and_mask(remaining, _DEMAND_LOW)

    positive = very_high + high
    negative = very_low + low
    if positive == 0 and negative == 0:
        return DemandLevel.MODERATE
    if positive > 0 and negative > 0 and abs(positive - negative) <= 1:
        return DemandLevel.MODERATE
    if negative > positive:
        return DemandLevel.VERY_LOW if very_low >= low else DemandLevel.LOW
    if very_high >= high and very_high > 0:
        return DemandLevel.VERY_HIGH
    if high > 0:
        return DemandLevel.HIGH
    return DemandLevel.MODERATE


def build_summary(
    pricing_text: str | None,
    trend_text: str | None,
    demand_text: str | None,
) -> str:
    parts: list[str] = []
    if pricing_text and pricing_text.strip():
        parts.append(f"Pricing: {pricing_text.strip()}")
    if trend_text and trend_text.strip():
        parts.append(f"Trend: {trend_text.strip()}")
    if demand_text and demand_text.strip():
        parts.append(f"Demand: {demand_text.strip()}")
    return " | ".join(parts)


def _score_and_mask(text: str, patterns: list[tuple[re.Pattern[str], int]]) -> tuple[int, str]:
    score = 0
    remaining = text
    for pattern, weight in patterns:
        matches = list(pattern.finditer(remaining))
        score += weight * len(matches)
        for match in reversed(matches):
            remaining = (
                remaining[: match.start()]
                + (" " * (match.end() - match.start()))
                + remaining[match.end() :]
            )
    return score, remaining
