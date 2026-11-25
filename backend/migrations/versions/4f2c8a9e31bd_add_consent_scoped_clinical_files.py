"""add consent-scoped clinical file metadata

Revision ID: 4f2c8a9e31bd
Revises: 99a9dcb916e5
Create Date: 2026-11-25 17:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f2c8a9e31bd"
down_revision: Union[str, None] = "99a9dcb916e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_files",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("uploaded_by_id", sa.String(), nullable=False),
        sa.Column("service_request_id", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("size_bytes > 0", name="ck_clinical_file_size_positive"),
        sa.CheckConstraint("size_bytes <= 10485760", name="ck_clinical_file_size_limit"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_request_id"], ["fhir_resources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(op.f("ix_clinical_files_created_at"), "clinical_files", ["created_at"], unique=False)
    op.create_index(op.f("ix_clinical_files_patient_id"), "clinical_files", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_files_service_request_id"), "clinical_files", ["service_request_id"], unique=False)
    op.create_index(op.f("ix_clinical_files_uploaded_by_id"), "clinical_files", ["uploaded_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clinical_files_uploaded_by_id"), table_name="clinical_files")
    op.drop_index(op.f("ix_clinical_files_service_request_id"), table_name="clinical_files")
    op.drop_index(op.f("ix_clinical_files_patient_id"), table_name="clinical_files")
    op.drop_index(op.f("ix_clinical_files_created_at"), table_name="clinical_files")
    op.drop_table("clinical_files")
