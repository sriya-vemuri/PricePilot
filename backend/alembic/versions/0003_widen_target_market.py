"""Widen target_market columns to 500 characters.

Revision ID: 0003_widen_target_market
Revises: 0002_add_analysis_user_id
Create Date: 2026-08-20

Aligns DB columns with CreateAnalysisRequest TARGET_MARKET_MAX_LENGTH.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_widen_target_market"
down_revision: Union[str, Sequence[str], None] = "0002_add_analysis_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.alter_column(
            "target_market",
            existing_type=sa.String(length=100),
            type_=sa.String(length=500),
            existing_nullable=False,
        )
    with op.batch_alter_table("market_cache") as batch_op:
        batch_op.alter_column(
            "target_market",
            existing_type=sa.String(length=100),
            type_=sa.String(length=500),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.alter_column(
            "target_market",
            existing_type=sa.String(length=500),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
    with op.batch_alter_table("market_cache") as batch_op:
        batch_op.alter_column(
            "target_market",
            existing_type=sa.String(length=500),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
