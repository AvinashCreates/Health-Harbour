"""persist login rate limits across API instances

Revision ID: 8c41d6a2f705
Revises: 71b6c4a2d9e1
Create Date: 2026-11-27 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c41d6a2f705"
down_revision: Union[str, None] = "71b6c4a2d9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_rate_limits",
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key_hash"),
    )
    op.create_index(
        op.f("ix_login_rate_limits_updated_at"),
        "login_rate_limits",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_login_rate_limits_updated_at"),
        table_name="login_rate_limits",
    )
    op.drop_table("login_rate_limits")
