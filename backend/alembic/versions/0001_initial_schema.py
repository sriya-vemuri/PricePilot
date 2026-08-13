"""Initial analyses, market_data, and market_cache tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

money = sa.Numeric(12, 2)
margin = sa.Numeric(5, 2)


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("cost", money, nullable=False),
        sa.Column("target_margin", margin, nullable=False),
        sa.Column("target_market", sa.String(length=100), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("pricing_mode", sa.String(length=20), nullable=False),
        sa.Column("baseline_price", money, nullable=False),
        sa.Column("recommended_price", money, nullable=False),
        sa.Column("price_range_low", money, nullable=False),
        sa.Column("price_range_high", money, nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=False),
        sa.Column("pricing_basis", sa.String(length=50), nullable=False),
        sa.Column("recommendation_mode", sa.String(length=50), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("demand_signal", sa.String(length=50), nullable=False),
        sa.Column("competitor_avg_price", money, nullable=True),
        sa.Column("competitor_avg_status", sa.String(length=80), nullable=False),
        sa.Column("trace_tavily_query", sa.Text(), nullable=True),
        sa.Column("trace_prices_found", sa.Integer(), nullable=False),
        sa.Column("trace_filtered_low", money, nullable=True),
        sa.Column("trace_filtered_high", money, nullable=True),
        sa.Column("trace_filtered_count", sa.Integer(), nullable=False),
        sa.Column("trace_used_fallback", sa.Boolean(), nullable=False),
        sa.Column("trace_market_trend", sa.String(length=50), nullable=False),
        sa.Column("trace_demand_level", sa.String(length=50), nullable=False),
        sa.Column("trace_competitor_avg_used", money, nullable=True),
        sa.Column("price_variance", sa.Float(), nullable=True),
        sa.Column("sanity_triggered", sa.Boolean(), nullable=False),
        sa.Column("baseline_status", sa.String(length=50), nullable=False),
        sa.Column("baseline_conflict", sa.Boolean(), nullable=False),
        sa.Column("baseline_conflict_reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "market_data",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tavily_query", sa.Text(), nullable=True),
        sa.Column("market_trend", sa.String(length=50), nullable=False),
        sa.Column("demand_level", sa.String(length=50), nullable=False),
        sa.Column("pricing_mode", sa.String(length=20), nullable=False),
        sa.Column("competitor_price_1", money, nullable=True),
        sa.Column("competitor_price_2", money, nullable=True),
        sa.Column("competitor_price_3", money, nullable=True),
        sa.Column("comparable_prices", sa.JSON(), nullable=False),
        sa.Column("filtered_range_low", money, nullable=True),
        sa.Column("filtered_range_high", money, nullable=True),
        sa.Column("raw_prices_found", sa.Integer(), nullable=False),
        sa.Column("filtered_prices_count", sa.Integer(), nullable=False),
        sa.Column("outliers_removed", sa.Integer(), nullable=False),
        sa.Column("has_reliable_data", sa.Boolean(), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=50), nullable=False),
        sa.Column("data_trust", sa.String(length=20), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("analysis_id"),
    )

    op.create_table(
        "market_cache",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cache_key", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("target_market", sa.String(length=100), nullable=False),
        sa.Column("pricing_mode", sa.String(length=20), nullable=False),
        sa.Column("candidate_prices", sa.JSON(), nullable=False),
        sa.Column("competitor_price_1", money, nullable=True),
        sa.Column("competitor_price_2", money, nullable=True),
        sa.Column("competitor_price_3", money, nullable=True),
        sa.Column("comparable_prices", sa.JSON(), nullable=False),
        sa.Column("filtered_range_low", money, nullable=True),
        sa.Column("filtered_range_high", money, nullable=True),
        sa.Column("raw_prices_found", sa.Integer(), nullable=False),
        sa.Column("filtered_prices_count", sa.Integer(), nullable=False),
        sa.Column("outliers_removed", sa.Integer(), nullable=False),
        sa.Column("has_reliable_data", sa.Boolean(), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=50), nullable=False),
        sa.Column("market_trend", sa.String(length=50), nullable=False),
        sa.Column("demand_level", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tavily_query", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_trust", sa.String(length=20), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_market_cache_cache_key", "market_cache", ["cache_key"])


def downgrade() -> None:
    op.drop_index("ix_market_cache_cache_key", table_name="market_cache")
    op.drop_table("market_cache")
    op.drop_table("market_data")
    op.drop_table("analyses")
