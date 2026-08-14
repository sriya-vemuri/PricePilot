"""Add nullable analyses.user_id for per-user ownership.

Revision ID: 0002_add_analysis_user_id
Revises: 0001_initial_schema
Create Date: 2026-08-13

Existing rows stay NULL. New authenticated creates must set user_id in the app.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_analysis_user_id"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_analyses_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_index("ix_analyses_user_id")
        batch_op.drop_column("user_id")
