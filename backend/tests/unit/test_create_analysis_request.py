from pydantic import ValidationError

import pytest

from app.models.enums import Category, Strategy
from app.models.requests import TARGET_MARKET_MAX_LENGTH, CreateAnalysisRequest


def _payload(**overrides):
    data = {
        "product_name": "Widget",
        "category": Category.ELECTRONICS,
        "cost": 10,
        "target_margin": 30,
        "target_market": "United States",
        "strategy": Strategy.BALANCED,
    }
    data.update(overrides)
    return data


class TestCreateAnalysisRequestTargetMarket:
    def test_accepts_exactly_500_characters(self):
        market = "a" * TARGET_MARKET_MAX_LENGTH
        req = CreateAnalysisRequest(**_payload(target_market=market))
        assert req.target_market == market
        assert len(req.target_market) == 500

    def test_rejects_over_500_characters(self):
        with pytest.raises(ValidationError) as exc_info:
            CreateAnalysisRequest(**_payload(target_market="a" * (TARGET_MARKET_MAX_LENGTH + 1)))
        assert "Target market must be 500 characters or fewer." in str(exc_info.value)

    def test_empty_defaults_to_united_states(self):
        req = CreateAnalysisRequest(**_payload(target_market="   "))
        assert req.target_market == "United States"

    def test_strips_whitespace(self):
        req = CreateAnalysisRequest(**_payload(target_market="  North America retail  "))
        assert req.target_market == "North America retail"
