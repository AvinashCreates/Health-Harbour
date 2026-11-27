from datetime import datetime

from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

import models
from services.registry import provider_is_eligible


def _active_consent_query(
    db: Session,
    grantee_id: str,
    purpose: str,
):
    active_legacy_membership = exists().where(
        models.OrganizationMembership.organization_id == models.Consent.organization_id,
        models.OrganizationMembership.practitioner_id == models.Consent.grantee_id,
        models.OrganizationMembership.active.is_(True),
        models.OrganizationMembership.created_at <= models.Consent.granted_at,
    )
    active_registry_affiliation = exists().where(
        models.OrganizationAffiliation.organization_id == models.Consent.organization_id,
        models.OrganizationAffiliation.account_id == models.Consent.grantee_id,
        models.OrganizationAffiliation.provider_id == db.query(models.HealthcareProvider.id).filter(
            models.HealthcareProvider.account_id == models.Consent.grantee_id,
            models.HealthcareProvider.status == "VERIFIED",
        ).scalar_subquery(),
        models.OrganizationAffiliation.status == "ACTIVE",
        models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
        models.HealthcareOrganization.status == "APPROVED",
        or_(
            models.OrganizationAffiliation.effective_from.is_(None),
            models.OrganizationAffiliation.effective_from <= models.Consent.granted_at,
        ),
        or_(
            models.OrganizationAffiliation.effective_until.is_(None),
            models.OrganizationAffiliation.effective_until > datetime.utcnow(),
        ),
    )
    return db.query(models.Consent).filter(
        models.Consent.grantee_id == grantee_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > datetime.utcnow(),
        models.Consent.purpose == purpose,
        or_(
            models.Consent.organization_id.is_(None),
            active_legacy_membership,
            active_registry_affiliation,
        ),
    )


def consent_is_active(db: Session, consent: models.Consent) -> bool:
    if consent.revoked_at is not None or consent.expires_at <= datetime.utcnow():
        return False
    if consent.organization_id is None:
        return provider_is_eligible(db, consent.grantee_id)

    legacy = db.query(models.OrganizationMembership.id).filter(
        models.OrganizationMembership.organization_id == consent.organization_id,
        models.OrganizationMembership.practitioner_id == consent.grantee_id,
        models.OrganizationMembership.active.is_(True),
        models.OrganizationMembership.created_at <= consent.granted_at,
    ).first()
    if legacy:
        return provider_is_eligible(db, consent.grantee_id)

    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == consent.grantee_id,
        models.HealthcareProvider.status == "VERIFIED",
    ).first()
    if provider is None:
        return False
    affiliation = db.query(models.OrganizationAffiliation.id).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
    ).filter(
        models.OrganizationAffiliation.organization_id == consent.organization_id,
        models.OrganizationAffiliation.provider_id == provider.id,
        models.OrganizationAffiliation.account_id == consent.grantee_id,
        models.OrganizationAffiliation.status == "ACTIVE",
        models.HealthcareOrganization.status == "APPROVED",
        or_(
            models.OrganizationAffiliation.effective_from.is_(None),
            models.OrganizationAffiliation.effective_from <= consent.granted_at,
        ),
        or_(
            models.OrganizationAffiliation.effective_until.is_(None),
            models.OrganizationAffiliation.effective_until > datetime.utcnow(),
        ),
    ).first()
    return affiliation is not None


def has_active_consent(
    db: Session,
    patient_id: str,
    grantee_id: str,
    resource_type: str,
    purpose: str = "TREATMENT",
) -> bool:
    if not provider_is_eligible(db, grantee_id):
        return False
    grants = _active_consent_query(db, grantee_id, purpose).filter(
        models.Consent.patient_id == patient_id,
    ).all()
    return any(resource_type in (consent.resource_types or []) for consent in grants)


def consented_patient_ids(
    db: Session,
    grantee_id: str,
    resource_type: str,
    purpose: str = "TREATMENT",
) -> list[str]:
    if not provider_is_eligible(db, grantee_id):
        return []
    grants = _active_consent_query(db, grantee_id, purpose).all()
    return sorted({
        consent.patient_id
        for consent in grants
        if resource_type in (consent.resource_types or [])
    })
