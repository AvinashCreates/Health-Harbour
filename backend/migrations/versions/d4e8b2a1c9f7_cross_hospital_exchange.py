"""add cross-hospital exchange and document provenance

Revision ID: d4e8b2a1c9f7
Revises: c7f3a9d1e4b2
Create Date: 2026-11-27 08:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8b2a1c9f7"
down_revision: Union[str, None] = "c7f3a9d1e4b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clinical_files") as batch_op:
        batch_op.add_column(sa.Column("source_organization_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("custodian_organization_id", sa.String(), nullable=True))
        batch_op.create_index("ix_clinical_files_source_organization_id", ["source_organization_id"])
        batch_op.create_index("ix_clinical_files_custodian_organization_id", ["custodian_organization_id"])
        batch_op.create_foreign_key("fk_clinical_files_source_org", "healthcare_organizations", ["source_organization_id"], ["id"])
        batch_op.create_foreign_key("fk_clinical_files_custodian_org", "healthcare_organizations", ["custodian_organization_id"], ["id"])

    op.create_table(
        "cross_hospital_exchange_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("requesting_organization_id", sa.String(), nullable=False),
        sa.Column("requesting_provider_id", sa.String(), nullable=False),
        sa.Column("source_organization_id", sa.String(), nullable=False),
        sa.Column("resource_types", sa.JSON(), nullable=False),
        sa.Column("purpose", sa.String(length=24), server_default="TREATMENT", nullable=False),
        sa.Column("requested_duration_days", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="REQUESTED", nullable=False),
        sa.Column("consent_id", sa.String(), nullable=True),
        sa.Column("response_reason", sa.String(length=1000), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'REVOKED', 'EXPIRED')", name="ck_cross_hospital_exchange_status"),
        sa.CheckConstraint("requested_duration_days >= 1 AND requested_duration_days <= 30", name="ck_cross_exchange_duration"),
        sa.ForeignKeyConstraint(["consent_id"], ["consents.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requesting_organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["requesting_provider_id"], ["healthcare_providers.id"]),
        sa.ForeignKeyConstraint(["source_organization_id"], ["healthcare_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cross_hospital_exchange_requests_patient_id", "cross_hospital_exchange_requests", ["patient_id"])
    op.create_index("ix_cross_hospital_exchange_requests_requesting_organization_id", "cross_hospital_exchange_requests", ["requesting_organization_id"])
    op.create_index("ix_cross_hospital_exchange_requests_requesting_provider_id", "cross_hospital_exchange_requests", ["requesting_provider_id"])
    op.create_index("ix_cross_hospital_exchange_requests_source_organization_id", "cross_hospital_exchange_requests", ["source_organization_id"])
    op.create_index("ix_cross_hospital_exchange_requests_status", "cross_hospital_exchange_requests", ["status"])
    op.create_index("ix_cross_hospital_exchange_requests_consent_id", "cross_hospital_exchange_requests", ["consent_id"])
    op.create_index("ix_cross_exchange_patient_status", "cross_hospital_exchange_requests", ["patient_id", "status"])
    op.create_index("ix_cross_exchange_requesting_org_status", "cross_hospital_exchange_requests", ["requesting_organization_id", "status"])
    op.create_index("ix_cross_exchange_source_org_status", "cross_hospital_exchange_requests", ["source_organization_id", "status"])

    op.create_table(
        "cross_org_document_imports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("exchange_request_id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_organization_id", sa.String(), nullable=False),
        sa.Column("receiving_organization_id", sa.String(), nullable=False),
        sa.Column("importing_provider_id", sa.String(), nullable=False),
        sa.Column("consent_id", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("integrity_verified", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'IMPORTED', 'FAILED')", name="ck_cross_org_document_import_status"),
        sa.ForeignKeyConstraint(["consent_id"], ["consents.id"]),
        sa.ForeignKeyConstraint(["exchange_request_id"], ["cross_hospital_exchange_requests.id"]),
        sa.ForeignKeyConstraint(["importing_provider_id"], ["healthcare_providers.id"]),
        sa.ForeignKeyConstraint(["receiving_organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["source_document_id"], ["clinical_files.id"]),
        sa.ForeignKeyConstraint(["source_organization_id"], ["healthcare_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange_request_id", "source_document_id", name="uq_exchange_document_import"),
    )
    op.create_index("ix_cross_org_document_imports_exchange_request_id", "cross_org_document_imports", ["exchange_request_id"])
    op.create_index("ix_cross_org_document_imports_source_document_id", "cross_org_document_imports", ["source_document_id"])
    op.create_index("ix_cross_org_document_imports_source_organization_id", "cross_org_document_imports", ["source_organization_id"])
    op.create_index("ix_cross_org_document_imports_receiving_organization_id", "cross_org_document_imports", ["receiving_organization_id"])
    op.create_index("ix_cross_org_document_imports_importing_provider_id", "cross_org_document_imports", ["importing_provider_id"])
    op.create_index("ix_cross_org_document_imports_consent_id", "cross_org_document_imports", ["consent_id"])
    op.create_index("ix_cross_org_document_imports_status", "cross_org_document_imports", ["status"])
    op.create_index("ix_cross_doc_import_receiving_org", "cross_org_document_imports", ["receiving_organization_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_cross_doc_import_receiving_org", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_status", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_consent_id", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_importing_provider_id", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_receiving_organization_id", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_source_organization_id", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_source_document_id", table_name="cross_org_document_imports")
    op.drop_index("ix_cross_org_document_imports_exchange_request_id", table_name="cross_org_document_imports")
    op.drop_table("cross_org_document_imports")

    op.drop_index("ix_cross_exchange_source_org_status", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_exchange_requesting_org_status", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_exchange_patient_status", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_consent_id", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_status", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_source_organization_id", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_requesting_provider_id", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_requesting_organization_id", table_name="cross_hospital_exchange_requests")
    op.drop_index("ix_cross_hospital_exchange_requests_patient_id", table_name="cross_hospital_exchange_requests")
    op.drop_table("cross_hospital_exchange_requests")

    with op.batch_alter_table("clinical_files") as batch_op:
        batch_op.drop_index("ix_clinical_files_custodian_organization_id")
        batch_op.drop_index("ix_clinical_files_source_organization_id")
        batch_op.drop_constraint("fk_clinical_files_custodian_org", type_="foreignkey")
        batch_op.drop_constraint("fk_clinical_files_source_org", type_="foreignkey")
        batch_op.drop_column("custodian_organization_id")
        batch_op.drop_column("source_organization_id")
