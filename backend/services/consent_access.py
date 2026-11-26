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
    active_membership = exists().where(
        models.OrganizationMembership.organization_id == models.Consent.organization_id,
        models.OrganizationMembership.practitioner_id == models.Consent.grantee_id,
        models.OrganizationMembership.active.is_(True),
        models.OrganizationMembership.created_at <= models.Consent.granted_at,
    )
    return db.query(models.Consent).filter(
        models.Consent.grantee_id == grantee_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > datetime.utcnow(),
        models.Consent.purpose == purpose,
        or_(models.Consent.organization_id.is_(None), active_membership),
    )


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
