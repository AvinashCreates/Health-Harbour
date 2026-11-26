from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


def require_organization_admin(
    db: Session,
    user: models.User,
    organization_id: str,
) -> models.HealthcareOrganization:
    organization = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    assignment = db.query(models.OrganizationRoleAssignment.id).filter(
        models.OrganizationRoleAssignment.organization_id == organization.id,
        models.OrganizationRoleAssignment.user_id == user.id,
        models.OrganizationRoleAssignment.role == "ORGANIZATION_ADMIN",
        models.OrganizationRoleAssignment.revoked_at.is_(None),
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def provider_has_active_affiliation(
    db: Session,
    provider_id: str,
    organization_id: str | None = None,
) -> bool:
    now = datetime.utcnow()
    query = db.query(models.OrganizationAffiliation.id).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
    ).filter(
        models.OrganizationAffiliation.provider_id == provider_id,
        models.OrganizationAffiliation.status == "ACTIVE",
        models.HealthcareOrganization.status == "APPROVED",
        (
            models.OrganizationAffiliation.effective_from.is_(None)
            | (models.OrganizationAffiliation.effective_from <= now)
        ),
        (
            models.OrganizationAffiliation.effective_until.is_(None)
            | (models.OrganizationAffiliation.effective_until > now)
        ),
    )
    if organization_id:
        query = query.filter(models.OrganizationAffiliation.organization_id == organization_id)
    return query.first() is not None


def provider_is_eligible(db: Session, account_id: str) -> bool:
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == account_id,
        models.HealthcareProvider.status == "VERIFIED",
    ).first()
    return bool(provider and provider_has_active_affiliation(db, provider.id))


def require_verified_provider(
    db: Session,
    user: models.User,
    organization_id: str | None = None,
) -> models.HealthcareProvider:
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == user.id,
        models.HealthcareProvider.status == "VERIFIED",
    ).first()
    if provider is None or not provider_has_active_affiliation(
        db, provider.id, organization_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="An active verified provider affiliation is required",
        )
    return provider


def add_affiliation_event(
    db: Session,
    affiliation: models.OrganizationAffiliation,
    actor_id: str,
    previous_status: str | None,
    new_status: str,
    reason: str,
) -> None:
    db.add(models.OrganizationAffiliationEvent(
        affiliation_id=affiliation.id,
        actor_id=actor_id,
        from_status=previous_status,
        to_status=new_status,
        reason=reason,
    ))
