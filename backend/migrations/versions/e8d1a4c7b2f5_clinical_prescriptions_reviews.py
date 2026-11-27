"""add prescriptions and physician clinical reviews

Revision ID: e8d1a4c7b2f5
Revises: d4e8b2a1c9f7
Create Date: 2026-11-27 10:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8d1a4c7b2f5"
down_revision: Union[str, None] = "d4e8b2a1c9f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("medication_name", sa.String(length=200), nullable=False),
        sa.Column("dosage", sa.String(length=120), nullable=False),
        sa.Column("route", sa.String(length=80), nullable=True),
        sa.Column("frequency", sa.String(length=120), nullable=False),
        sa.Column("duration", sa.String(length=120), nullable=True),
        sa.Column("quantity", sa.String(length=120), nullable=True),
        sa.Column("instructions", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="DRAFT", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'CANCELLED', 'COMPLETED', 'STOPPED')", name="ck_prescription_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"])
    op.create_index("ix_prescriptions_provider_id", "prescriptions", ["provider_id"])
    op.create_index("ix_prescriptions_organization_id", "prescriptions", ["organization_id"])
    op.create_index("ix_prescriptions_status", "prescriptions", ["status"])
    op.create_index("ix_prescription_patient_status", "prescriptions", ["patient_id", "status"])
    op.create_index("ix_prescription_provider_status", "prescriptions", ["provider_id", "status"])

    op.create_table(
        "prescription_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("prescription_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("to_status IN ('DRAFT', 'ACTIVE', 'CANCELLED', 'COMPLETED', 'STOPPED')", name="ck_prescription_history_status"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prescription_history_prescription_id", "prescription_history", ["prescription_id"])
    op.create_index("ix_prescription_history_actor_id", "prescription_history", ["actor_id"])

    op.create_table(
        "physician_clinical_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("diagnostic_report_id", sa.String(), nullable=True),
        sa.Column("service_request_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("clinical_note", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'REVIEWED', 'FOLLOW_UP_REQUIRED')", name="ck_physician_clinical_review_status"),
        sa.ForeignKeyConstraint(["diagnostic_report_id"], ["fhir_resources.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.ForeignKeyConstraint(["service_request_id"], ["fhir_resources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_physician_clinical_reviews_patient_id", "physician_clinical_reviews", ["patient_id"])
    op.create_index("ix_physician_clinical_reviews_provider_id", "physician_clinical_reviews", ["provider_id"])
    op.create_index("ix_physician_clinical_reviews_organization_id", "physician_clinical_reviews", ["organization_id"])
    op.create_index("ix_physician_clinical_reviews_diagnostic_report_id", "physician_clinical_reviews", ["diagnostic_report_id"])
    op.create_index("ix_physician_clinical_reviews_service_request_id", "physician_clinical_reviews", ["service_request_id"])
    op.create_index("ix_physician_clinical_reviews_status", "physician_clinical_reviews", ["status"])
    op.create_index("ix_clinical_review_patient_status", "physician_clinical_reviews", ["patient_id", "status"])
    op.create_index("ix_clinical_review_provider_status", "physician_clinical_reviews", ["provider_id", "status"])


    op.create_table(
        "laboratory_report_amendments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("report_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("previous_conclusion", sa.String(length=2000), nullable=True),
        sa.Column("conclusion", sa.String(length=2000), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["fhir_resources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_laboratory_report_amendments_report_id", "laboratory_report_amendments", ["report_id"])
    op.create_index("ix_laboratory_report_amendments_actor_id", "laboratory_report_amendments", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_laboratory_report_amendments_actor_id", table_name="laboratory_report_amendments")
    op.drop_index("ix_laboratory_report_amendments_report_id", table_name="laboratory_report_amendments")
    op.drop_table("laboratory_report_amendments")
    op.drop_index("ix_clinical_review_provider_status", table_name="physician_clinical_reviews")
    op.drop_index("ix_clinical_review_patient_status", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_status", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_service_request_id", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_diagnostic_report_id", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_organization_id", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_provider_id", table_name="physician_clinical_reviews")
    op.drop_index("ix_physician_clinical_reviews_patient_id", table_name="physician_clinical_reviews")
    op.drop_table("physician_clinical_reviews")

    op.drop_index("ix_prescription_history_actor_id", table_name="prescription_history")
    op.drop_index("ix_prescription_history_prescription_id", table_name="prescription_history")
    op.drop_table("prescription_history")

    op.drop_index("ix_prescription_provider_status", table_name="prescriptions")
    op.drop_index("ix_prescription_patient_status", table_name="prescriptions")
    op.drop_index("ix_prescriptions_status", table_name="prescriptions")
    op.drop_index("ix_prescriptions_organization_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_provider_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_patient_id", table_name="prescriptions")
    op.drop_table("prescriptions")
