"""add named-practitioner organization consent

Revision ID: 71b6c4a2d9e1
Revises: 4f2c8a9e31bd
Create Date: 2026-11-27 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "71b6c4a2d9e1"
down_revision: Union[str, None] = "4f2c8a9e31bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("consents") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column(
            "purpose",
            sa.String(),
            nullable=False,
            server_default="TREATMENT",
        ))
        batch_op.create_foreign_key(
            "fk_consents_organization_id_users",
            "users",
            ["organization_id"],
            ["id"],
        )
    op.create_index(
        op.f("ix_consents_organization_id"),
        "consents",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("practitioner_id", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["practitioner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "practitioner_id", name="uq_org_practitioner"),
    )
    op.create_index(
        op.f("ix_organization_memberships_organization_id"),
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_memberships_practitioner_id"),
        "organization_memberships",
        ["practitioner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_memberships_practitioner_id"),
        table_name="organization_memberships",
    )
    op.drop_index(
        op.f("ix_organization_memberships_organization_id"),
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_index(op.f("ix_consents_organization_id"), table_name="consents")
    with op.batch_alter_table("consents") as batch_op:
        batch_op.drop_constraint("fk_consents_organization_id_users", type_="foreignkey")
        batch_op.drop_column("purpose")
        batch_op.drop_column("organization_id")
