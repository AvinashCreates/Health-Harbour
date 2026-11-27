"""add reliable FHIR synchronization outbox

Revision ID: c7f3a9d1e4b2
Revises: a31e7c9d2f10
Create Date: 2026-11-27 07:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f3a9d1e4b2"
down_revision: Union[str, None] = "a31e7c9d2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fhir_sync_outbox",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("resource_payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SYNCED', 'FAILED', 'PERMANENT_FAILED')",
            name="ck_fhir_sync_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_type", "resource_id", name="uq_fhir_sync_resource"),
    )
    op.create_index("ix_fhir_sync_outbox_resource_type", "fhir_sync_outbox", ["resource_type"])
    op.create_index("ix_fhir_sync_outbox_resource_id", "fhir_sync_outbox", ["resource_id"])
    op.create_index("ix_fhir_sync_outbox_payload_hash", "fhir_sync_outbox", ["payload_hash"])
    op.create_index("ix_fhir_sync_outbox_status", "fhir_sync_outbox", ["status"])
    op.create_index("ix_fhir_sync_outbox_next_attempt_at", "fhir_sync_outbox", ["next_attempt_at"])
    op.create_index("ix_fhir_sync_status_next_attempt", "fhir_sync_outbox", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_fhir_sync_status_next_attempt", table_name="fhir_sync_outbox")
    op.drop_index("ix_fhir_sync_outbox_next_attempt_at", table_name="fhir_sync_outbox")
    op.drop_index("ix_fhir_sync_outbox_status", table_name="fhir_sync_outbox")
    op.drop_index("ix_fhir_sync_outbox_payload_hash", table_name="fhir_sync_outbox")
    op.drop_index("ix_fhir_sync_outbox_resource_id", table_name="fhir_sync_outbox")
    op.drop_index("ix_fhir_sync_outbox_resource_type", table_name="fhir_sync_outbox")
    op.drop_table("fhir_sync_outbox")
