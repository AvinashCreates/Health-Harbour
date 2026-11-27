"""add patient-provider connections and record access requests

Revision ID: f4c1a6d2e9b7
Revises: 2a7f9c6d4e81
Create Date: 2026-11-27 06:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c1a6d2e9b7"
down_revision: Union[str, None] = "2a7f9c6d4e81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "care_connections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="INITIATED", nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("provider_response", sa.String(length=1000), nullable=True),
        sa.Column("initiated_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('INITIATED', 'ACCEPTED', 'DECLINED', 'CLOSED')",
            name="ck_care_connection_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "patient_id", "provider_id", "organization_id",
            name="uq_care_connection_patient_provider_org",
        ),
    )
    op.create_index("ix_care_connection_patient_status", "care_connections", ["patient_id", "status"], unique=False)
    op.create_index("ix_care_connection_provider_status", "care_connections", ["provider_id", "status"], unique=False)
    op.create_index(op.f("ix_care_connections_patient_id"), "care_connections", ["patient_id"], unique=False)
    op.create_index(op.f("ix_care_connections_provider_id"), "care_connections", ["provider_id"], unique=False)
    op.create_index(op.f("ix_care_connections_organization_id"), "care_connections", ["organization_id"], unique=False)
    op.create_index(op.f("ix_care_connections_status"), "care_connections", ["status"], unique=False)

    op.create_table(
        "provider_record_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("resource_types", sa.JSON(), nullable=False),
        sa.Column("purpose", sa.String(length=24), server_default="TREATMENT", nullable=False),
        sa.Column("requested_duration_days", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="REQUESTED", nullable=False),
        sa.Column("response_reason", sa.String(length=1000), nullable=True),
        sa.Column("consent_id", sa.String(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_provider_record_request_status",
        ),
        sa.CheckConstraint("requested_duration_days >= 1 AND requested_duration_days <= 30", name="ck_record_request_duration"),
        sa.ForeignKeyConstraint(["consent_id"], ["consents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_record_request_patient_status", "provider_record_requests", ["patient_id", "status"], unique=False)
    op.create_index("ix_record_request_provider_status", "provider_record_requests", ["provider_id", "status"], unique=False)
    op.create_index(op.f("ix_provider_record_requests_patient_id"), "provider_record_requests", ["patient_id"], unique=False)
    op.create_index(op.f("ix_provider_record_requests_provider_id"), "provider_record_requests", ["provider_id"], unique=False)
    op.create_index(op.f("ix_provider_record_requests_organization_id"), "provider_record_requests", ["organization_id"], unique=False)
    op.create_index(op.f("ix_provider_record_requests_status"), "provider_record_requests", ["status"], unique=False)
    op.create_index(op.f("ix_provider_record_requests_consent_id"), "provider_record_requests", ["consent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_provider_record_requests_consent_id"), table_name="provider_record_requests")
    op.drop_index(op.f("ix_provider_record_requests_status"), table_name="provider_record_requests")
    op.drop_index(op.f("ix_provider_record_requests_organization_id"), table_name="provider_record_requests")
    op.drop_index(op.f("ix_provider_record_requests_provider_id"), table_name="provider_record_requests")
    op.drop_index(op.f("ix_provider_record_requests_patient_id"), table_name="provider_record_requests")
    op.drop_index("ix_record_request_provider_status", table_name="provider_record_requests")
    op.drop_index("ix_record_request_patient_status", table_name="provider_record_requests")
    op.drop_table("provider_record_requests")

    op.drop_index(op.f("ix_care_connections_status"), table_name="care_connections")
    op.drop_index(op.f("ix_care_connections_organization_id"), table_name="care_connections")
    op.drop_index(op.f("ix_care_connections_provider_id"), table_name="care_connections")
    op.drop_index(op.f("ix_care_connections_patient_id"), table_name="care_connections")
    op.drop_index("ix_care_connection_provider_status", table_name="care_connections")
    op.drop_index("ix_care_connection_patient_status", table_name="care_connections")
    op.drop_table("care_connections")
