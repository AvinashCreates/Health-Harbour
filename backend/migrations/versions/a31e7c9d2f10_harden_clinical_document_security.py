"""add clinical document processing and encryption metadata

Revision ID: a31e7c9d2f10
Revises: f4c1a6d2e9b7
Create Date: 2026-11-27 07:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a31e7c9d2f10"
down_revision: Union[str, None] = "f4c1a6d2e9b7"
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clinical_files") as batch_op:
        batch_op.add_column(sa.Column("processing_status", sa.String(length=24), server_default="CLEAN", nullable=False))
        batch_op.add_column(sa.Column("scan_status", sa.String(length=24), server_default="NOT_REQUIRED", nullable=False))
        batch_op.add_column(sa.Column("scan_detail", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("encryption_version", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("encryption_key_id", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_clinical_files_processing_status", ["processing_status"])
        batch_op.create_index("ix_clinical_files_scan_status", ["scan_status"])
        batch_op.create_check_constraint(
            "ck_clinical_file_processing_status",
            "processing_status IN ('RECEIVED', 'QUARANTINED', 'SCANNING', 'CLEAN', 'REJECTED', 'SCAN_FAILED')",
        )
        batch_op.create_check_constraint(
            "ck_clinical_file_scan_status",
            "scan_status IN ('NOT_REQUIRED', 'CLEAN', 'MALICIOUS', 'UNSUPPORTED', 'UNAVAILABLE', 'TIMEOUT')",
        )


def downgrade() -> None:
    with op.batch_alter_table("clinical_files") as batch_op:
        batch_op.drop_constraint("ck_clinical_file_scan_status", type_="check")
        batch_op.drop_constraint("ck_clinical_file_processing_status", type_="check")
        batch_op.drop_index("ix_clinical_files_scan_status")
        batch_op.drop_index("ix_clinical_files_processing_status")
        batch_op.drop_column("encryption_key_id")
        batch_op.drop_column("encryption_version")
        batch_op.drop_column("scan_detail")
        batch_op.drop_column("scan_status")
        batch_op.drop_column("processing_status")
