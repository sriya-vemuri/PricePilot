"""Centralized pricing-engine constants."""

from app.models.enums import DemandLevel, MarketTrend, Strategy

# Strategy anchor positions within the observed market range (fraction from low).
RETAIL_STRATEGY_POSITION = {
    Strategy.AGGRESSIVE: 0.20,
    Strategy.BALANCED: 0.50,
    Strategy.PREMIUM: 0.80,
}
SERVICE_STRATEGY_POSITION = {
    Strategy.AGGRESSIVE: 0.25,
    Strategy.BALANCED: 0.50,
    Strategy.PREMIUM: 0.75,
}

# Retail blend weights (market share of final price).
RETAIL_BLEND_WEIGHT_DEFAULT = 0.50
RETAIL_BLEND_WEIGHT_TIGHT_5 = 0.65
RETAIL_BLEND_WEIGHT_TIGHT_10 = 0.75
RETAIL_BLEND_SPREAD_TIGHT_5 = 0.30
RETAIL_BLEND_SPREAD_TIGHT_10 = 0.20

# Service blend weights.
SERVICE_BLEND_WEIGHT_DEFAULT = 0.40
SERVICE_BLEND_WEIGHT_5_PLUS = 0.55

# Demand adjustments (fractional change).
RETAIL_DEMAND_ADJ = {
    DemandLevel.VERY_HIGH: 0.12,
    DemandLevel.HIGH: 0.06,
    DemandLevel.MODERATE: 0.0,
    DemandLevel.LOW: -0.06,
    DemandLevel.VERY_LOW: -0.12,
}
SERVICE_DEMAND_ADJ = {
    DemandLevel.VERY_HIGH: 0.10,
    DemandLevel.HIGH: 0.05,
    DemandLevel.MODERATE: 0.0,
    DemandLevel.LOW: -0.05,
    DemandLevel.VERY_LOW: -0.10,
}

# Trend adjustments.
RETAIL_TREND_ADJ = {
    MarketTrend.SURGING: 0.05,
    MarketTrend.GROWING: 0.03,
    MarketTrend.STABLE: 0.0,
    MarketTrend.DECLINING: -0.04,
}
SERVICE_TREND_ADJ = {
    MarketTrend.SURGING: 0.04,
    MarketTrend.GROWING: 0.02,
    MarketTrend.STABLE: 0.0,
    MarketTrend.DECLINING: -0.03,
}

# Price-range bands around the recommended price.
RETAIL_RANGE_PCT = {
    Strategy.AGGRESSIVE: 0.06,
    Strategy.BALANCED: 0.08,
    Strategy.PREMIUM: 0.10,
}
SERVICE_RANGE_PCT = {
    Strategy.AGGRESSIVE: 0.12,
    Strategy.BALANCED: 0.15,
    Strategy.PREMIUM: 0.18,
}

# Sanity-check multipliers.
RETAIL_SANITY = {
    "above_market_high": 1.3,
    "below_market_low": 0.7,
    "above_baseline": 2.0,
}
SERVICE_SANITY = {
    "above_market_high": 1.6,
    "below_market_low": 0.5,
    "above_baseline": 3.0,
}

SANITY_BLEND_CURRENT = 0.40
SANITY_BLEND_BASELINE = 0.60

# Market-vs-baseline plausibility multipliers.
RETAIL_MARKET_ABOVE_MULT = 3.0
RETAIL_MARKET_BELOW_MULT = 0.2
SERVICE_MARKET_ABOVE_MULT = 5.0
SERVICE_MARKET_BELOW_MULT = 0.1

# Competitor-average suppression.
NEAR_BASELINE_PCT = 0.01
TIGHT_CV_THRESHOLD = 0.05
MIN_PRICES_FOR_COMPETITOR_AVG = 3
MIN_PRICES_FOR_SUPPRESSED_MEDIAN = 5

# Confidence bounds.
CONFIDENCE_MIN = 18
CONFIDENCE_MAX = 88

MIN_MARKET_PRICES = 3
