"""add healthcare organization, provider, and affiliation registry

Revision ID: 2a7f9c6d4e81
Revises: 8c41d6a2f705
Create Date: 2026-11-26 22:00:00
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "2a7f9c6d4e81"
down_revision: Union[str, None] = "8c41d6a2f705"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "healthcare_organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("legacy_user_id", sa.String(), nullable=True),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("organization_type", sa.String(length=32), nullable=False),
        sa.Column("registration_authority", sa.String(length=160), nullable=True),
        sa.Column("registration_identifier", sa.String(length=160), nullable=True),
        sa.Column("address", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("contact_email", sa.String(length=254), nullable=True),
        sa.Column("contact_phone", sa.String(length=40), nullable=True),
        sa.Column("administrative_contact_name", sa.String(length=120), nullable=False),
        sa.Column("administrative_contact_email", sa.String(length=254), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("fhir_resource_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by_id", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("decision_reason", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "organization_type IN ('HOSPITAL', 'CLINIC', 'DIAGNOSTIC_LABORATORY', 'OTHER')",
            name="ck_healthcare_organization_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED')",
            name="ck_healthcare_organization_status",
        ),
        sa.ForeignKeyConstraint(["legacy_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_user_id"),
        sa.UniqueConstraint(
            "registration_authority",
            "registration_identifier",
            name="uq_healthcare_organization_registration",
        ),
    )
    op.create_index(
        op.f("ix_healthcare_organizations_status"),
        "healthcare_organizations",
        ["status"],
        unique=False,
    )
    op.create_table(
        "organization_applications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("applicant_user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by_id", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("decision_reason", sa.String(length=1000), nullable=True),
        sa.Column("evidence_references", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED')",
            name="ck_organization_application_status",
        ),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_applications_applicant_user_id"), "organization_applications", ["applicant_user_id"])
    op.create_index(op.f("ix_organization_applications_organization_id"), "organization_applications", ["organization_id"])
    op.create_index(op.f("ix_organization_applications_status"), "organization_applications", ["status"])
    op.create_table(
        "organization_review_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("application_id", sa.String(), nullable=True),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('UNDER_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED', 'REINSTATED')",
            name="ck_organization_review_decision",
        ),
        sa.ForeignKeyConstraint(["application_id"], ["organization_applications.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_review_decisions_application_id"), "organization_review_decisions", ["application_id"])
    op.create_index(op.f("ix_organization_review_decisions_created_at"), "organization_review_decisions", ["created_at"])
    op.create_index(op.f("ix_organization_review_decisions_organization_id"), "organization_review_decisions", ["organization_id"])
    op.create_index(op.f("ix_organization_review_decisions_reviewer_id"), "organization_review_decisions", ["reviewer_id"])
    op.create_table(
        "healthcare_providers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("professional_name", sa.String(length=160), nullable=False),
        sa.Column("registration_authority", sa.String(length=160), nullable=True),
        sa.Column("registration_number", sa.String(length=120), nullable=True),
        sa.Column("qualifications", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=True),
        sa.Column("public_profile", sa.String(length=1000), nullable=True),
        sa.Column("public_contact_email", sa.String(length=254), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("fhir_resource_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by_id", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("decision_reason", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED', 'SUSPENDED')",
            name="ck_healthcare_provider_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registration_authority",
            "registration_number",
            name="uq_healthcare_provider_registration",
        ),
    )
    op.create_index(op.f("ix_healthcare_providers_account_id"), "healthcare_providers", ["account_id"], unique=True)
    op.create_index(op.f("ix_healthcare_providers_status"), "healthcare_providers", ["status"])
    op.create_table(
        "provider_applications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("applicant_user_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="PENDING", nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by_id", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("decision_reason", sa.String(length=1000), nullable=True),
        sa.Column("evidence_references", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED')",
            name="ck_provider_application_status",
        ),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_applications_applicant_user_id"), "provider_applications", ["applicant_user_id"])
    op.create_index(op.f("ix_provider_applications_provider_id"), "provider_applications", ["provider_id"])
    op.create_index(op.f("ix_provider_applications_status"), "provider_applications", ["status"])
    op.create_table(
        "provider_verifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("application_id", sa.String(), nullable=True),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("method", sa.String(length=40), server_default="MANUAL_REVIEW", nullable=False),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('UNDER_REVIEW', 'VERIFIED', 'REJECTED', 'SUSPENDED', 'REINSTATED')",
            name="ck_provider_verification_decision",
        ),
        sa.ForeignKeyConstraint(["application_id"], ["provider_applications.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_verifications_application_id"), "provider_verifications", ["application_id"])
    op.create_index(op.f("ix_provider_verifications_created_at"), "provider_verifications", ["created_at"])
    op.create_index(op.f("ix_provider_verifications_provider_id"), "provider_verifications", ["provider_id"])
    op.create_index(op.f("ix_provider_verifications_reviewer_id"), "provider_verifications", ["reviewer_id"])
    op.create_table(
        "organization_affiliations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("organization_role", sa.String(length=40), server_default="PROVIDER", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="INVITED", nullable=False),
        sa.Column("invited_by_id", sa.String(), nullable=False),
        sa.Column("invitation_message", sa.String(length=500), nullable=True),
        sa.Column("decision_by_id", sa.String(), nullable=True),
        sa.Column("decision_reason", sa.String(length=1000), nullable=True),
        sa.Column("invited_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("effective_until", sa.DateTime(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('INVITED', 'PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED', 'ENDED')",
            name="ck_organization_affiliation_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decision_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["healthcare_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_affiliations_account_id"), "organization_affiliations", ["account_id"])
    op.create_index(op.f("ix_organization_affiliations_organization_id"), "organization_affiliations", ["organization_id"])
    op.create_index(op.f("ix_organization_affiliations_provider_id"), "organization_affiliations", ["provider_id"])
    op.create_index(op.f("ix_organization_affiliations_status"), "organization_affiliations", ["status"])
    op.create_index(
        "ix_org_affiliation_org_provider_status",
        "organization_affiliations",
        ["organization_id", "provider_id", "status"],
    )
    op.create_table(
        "organization_role_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("granted_by_id", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_by_id", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "role IN ('ORGANIZATION_ADMIN', 'ORGANIZATION_STAFF')",
            name="ck_organization_role_assignment_role",
        ),
        sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["healthcare_organizations.id"]),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_role_assignments_organization_id"), "organization_role_assignments", ["organization_id"])
    op.create_index(op.f("ix_organization_role_assignments_user_id"), "organization_role_assignments", ["user_id"])
    op.create_index(
        "ix_org_role_assignment_scope",
        "organization_role_assignments",
        ["organization_id", "user_id", "role", "revoked_at"],
    )
    op.create_table(
        "organization_affiliation_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("affiliation_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "to_status IN ('INVITED', 'PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED', 'ENDED')",
            name="ck_organization_affiliation_event_status",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["affiliation_id"], ["organization_affiliations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_affiliation_events_actor_id"), "organization_affiliation_events", ["actor_id"])
    op.create_index(op.f("ix_organization_affiliation_events_affiliation_id"), "organization_affiliation_events", ["affiliation_id"])
    op.create_index(op.f("ix_organization_affiliation_events_created_at"), "organization_affiliation_events", ["created_at"])

    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("email", sa.String()),
        sa.column("role", sa.String()),
        sa.column("fhir_resource_id", sa.String()),
    )
    organizations = sa.table(
        "healthcare_organizations",
        sa.column("id", sa.String()),
        sa.column("legacy_user_id", sa.String()),
        sa.column("legal_name", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("organization_type", sa.String()),
        sa.column("address", sa.JSON()),
        sa.column("contact_email", sa.String()),
        sa.column("administrative_contact_name", sa.String()),
        sa.column("administrative_contact_email", sa.String()),
        sa.column("status", sa.String()),
        sa.column("fhir_resource_id", sa.String()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    providers = sa.table(
        "healthcare_providers",
        sa.column("id", sa.String()),
        sa.column("account_id", sa.String()),
        sa.column("professional_name", sa.String()),
        sa.column("qualifications", sa.JSON()),
        sa.column("status", sa.String()),
        sa.column("fhir_resource_id", sa.String()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    now = sa.func.current_timestamp()
    legacy_orgs = bind.execute(
        sa.select(users.c.id, users.c.full_name, users.c.email, users.c.role, users.c.fhir_resource_id)
        .where(users.c.role.in_(("lab", "lab_supervisor")))
    ).mappings()
    for user in legacy_orgs:
        bind.execute(organizations.insert().values(
            id=str(uuid.uuid4()),
            legacy_user_id=user["id"],
            legal_name=user["full_name"],
            display_name=user["full_name"],
            organization_type="DIAGNOSTIC_LABORATORY",
            address={},
            contact_email=user["email"],
            administrative_contact_name=user["full_name"],
            administrative_contact_email=user["email"],
            status="PENDING",
            fhir_resource_id=user["fhir_resource_id"],
            created_at=now,
            updated_at=now,
        ))
    legacy_providers = bind.execute(
        sa.select(users.c.id, users.c.full_name, users.c.fhir_resource_id)
        .where(users.c.role == "doctor")
    ).mappings()
    for user in legacy_providers:
        bind.execute(providers.insert().values(
            id=str(uuid.uuid4()),
            account_id=user["id"],
            professional_name=user["full_name"],
            qualifications=[],
            status="PENDING",
            fhir_resource_id=user["fhir_resource_id"],
            created_at=now,
            updated_at=now,
        ))


def downgrade() -> None:
    bind = op.get_bind()
    organizations = sa.table(
        "healthcare_organizations",
        sa.column("legacy_user_id", sa.String()),
    )
    providers = sa.table(
        "healthcare_providers",
        sa.column("account_id", sa.String()),
    )
    legacy_org_ids = bind.execute(
        sa.select(organizations.c.legacy_user_id)
        .where(organizations.c.legacy_user_id.is_not(None))
    ).scalars().all()
    legacy_provider_ids = bind.execute(
        sa.select(providers.c.account_id)
    ).scalars().all()
    if legacy_org_ids or legacy_provider_ids:
        raise RuntimeError(
            "Registry downgrade would remove compatibility mappings; "
            "restore the disposable database from its pre-migration backup instead."
        )
    op.drop_index(op.f("ix_organization_affiliation_events_created_at"), table_name="organization_affiliation_events")
    op.drop_index(op.f("ix_organization_affiliation_events_affiliation_id"), table_name="organization_affiliation_events")
    op.drop_index(op.f("ix_organization_affiliation_events_actor_id"), table_name="organization_affiliation_events")
    op.drop_table("organization_affiliation_events")
    op.drop_index("ix_org_role_assignment_scope", table_name="organization_role_assignments")
    op.drop_index(op.f("ix_organization_role_assignments_user_id"), table_name="organization_role_assignments")
    op.drop_index(op.f("ix_organization_role_assignments_organization_id"), table_name="organization_role_assignments")
    op.drop_table("organization_role_assignments")
    op.drop_index("ix_org_affiliation_org_provider_status", table_name="organization_affiliations")
    op.drop_index(op.f("ix_organization_affiliations_status"), table_name="organization_affiliations")
    op.drop_index(op.f("ix_organization_affiliations_provider_id"), table_name="organization_affiliations")
    op.drop_index(op.f("ix_organization_affiliations_organization_id"), table_name="organization_affiliations")
    op.drop_index(op.f("ix_organization_affiliations_account_id"), table_name="organization_affiliations")
    op.drop_table("organization_affiliations")
    op.drop_index(op.f("ix_provider_verifications_reviewer_id"), table_name="provider_verifications")
    op.drop_index(op.f("ix_provider_verifications_provider_id"), table_name="provider_verifications")
    op.drop_index(op.f("ix_provider_verifications_created_at"), table_name="provider_verifications")
    op.drop_index(op.f("ix_provider_verifications_application_id"), table_name="provider_verifications")
    op.drop_table("provider_verifications")
    op.drop_index(op.f("ix_provider_applications_status"), table_name="provider_applications")
    op.drop_index(op.f("ix_provider_applications_provider_id"), table_name="provider_applications")
    op.drop_index(op.f("ix_provider_applications_applicant_user_id"), table_name="provider_applications")
    op.drop_table("provider_applications")
    op.drop_index(op.f("ix_healthcare_providers_status"), table_name="healthcare_providers")
    op.drop_index(op.f("ix_healthcare_providers_account_id"), table_name="healthcare_providers")
    op.drop_table("healthcare_providers")
    op.drop_index(op.f("ix_organization_review_decisions_reviewer_id"), table_name="organization_review_decisions")
    op.drop_index(op.f("ix_organization_review_decisions_organization_id"), table_name="organization_review_decisions")
    op.drop_index(op.f("ix_organization_review_decisions_created_at"), table_name="organization_review_decisions")
    op.drop_index(op.f("ix_organization_review_decisions_application_id"), table_name="organization_review_decisions")
    op.drop_table("organization_review_decisions")
    op.drop_index(op.f("ix_organization_applications_status"), table_name="organization_applications")
    op.drop_index(op.f("ix_organization_applications_organization_id"), table_name="organization_applications")
    op.drop_index(op.f("ix_organization_applications_applicant_user_id"), table_name="organization_applications")
    op.drop_table("organization_applications")
    op.drop_index(op.f("ix_healthcare_organizations_status"), table_name="healthcare_organizations")
    op.drop_table("healthcare_organizations")
