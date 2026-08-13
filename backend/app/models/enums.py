from enum import StrEnum


class Category(StrEnum):
    ELECTRONICS = "electronics"
    SOFTWARE = "software"
    CLOTHING = "clothing"
    FOOD_BEVERAGE = "food_beverage"
    HEALTH_BEAUTY = "health_beauty"
    HOME_GARDEN = "home_garden"
    AUTOMOTIVE = "automotive"
    SERVICES = "services"
    OTHER = "other"


class Strategy(StrEnum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    PREMIUM = "premium"


class PricingMode(StrEnum):
    RETAIL = "retail"
    SERVICE = "service"


class DemandLevel(StrEnum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarketTrend(StrEnum):
    DECLINING = "declining"
    STABLE = "stable"
    GROWING = "growing"
    SURGING = "surging"


class PricingBasis(StrEnum):
    BASELINE_DRIVEN = "baseline_driven"
    MARKET_ALIGNED = "market_aligned"
    MARKET_DRIVEN = "market_driven"


class RecommendationMode(StrEnum):
    BASELINE_LED = "baseline_led"
    MARKET_LED = "market_led"
    FEASIBILITY_OVERRIDE = "feasibility_override"


class CompetitorAvgStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE_INSUFFICIENT_DATA = "unavailable_insufficient_data"
    UNAVAILABLE_SUPPRESSED_NEAR_BASELINE = "unavailable_suppressed_near_baseline"
    UNAVAILABLE_SERVICE_MODE = "unavailable_service_mode"


class BaselineStatus(StrEnum):
    PLAUSIBLE = "plausible"
    IMPLAUSIBLE = "implausible"


class RetrievalMode(StrEnum):
    PRIMARY = "primary"
    STAGE2_SUCCESS = "stage2_success"
    STAGE2_INSUFFICIENT = "stage2_insufficient"
    STAGE3_SUCCESS = "stage3_success"
    EXHAUSTED = "exhausted"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SimulationType(StrEnum):
    DECREASE = "decrease"
    INCREASE = "increase"
    CUSTOM = "custom"
