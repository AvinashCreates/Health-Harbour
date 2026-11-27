from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased

import models
import schemas
from database import get_db
from deps import require_roles
from services import audit_logger
from services import fhir_builder
from services.fhir_server import authoritative_resource, fhir_mode, persist_resource
from services.consent_access import consent_is_active
from services.registry import provider_has_active_affiliation

router = APIRouter(prefix="/consent", tags=["consent"])


def _serialize(c: models.Consent, db: Session) -> schemas.ConsentOut:
    is_active = consent_is_active(db, c)
    return schemas.ConsentOut(
        id=c.id, patient_id=c.patient_id, grantee_id=c.grantee_id,
        organization_id=c.organization_id, purpose=c.purpose,
        resource_types=c.resource_types, granted_at=c.granted_at,
        expires_at=c.expires_at, revoked_at=c.revoked_at,
        is_active=is_active,
    )


@router.post("/grant", response_model=schemas.ConsentOut)
def grant_consent(payload: schemas.ConsentGrant, db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("patient"))):
    doctor = db.query(models.User).filter(models.User.email == payload.doctor_email, models.User.role == "doctor").first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    organization = None
    if payload.organization_id:
        legacy_organization = db.query(models.User).filter(
            models.User.id == payload.organization_id,
            models.User.role == "lab",
        ).first()
        registry_organization = db.query(models.HealthcareOrganization).filter(
            models.HealthcareOrganization.id == payload.organization_id,
            models.HealthcareOrganization.status == "APPROVED",
        ).first()
        if legacy_organization:
            membership = db.query(models.OrganizationMembership).filter(
                models.OrganizationMembership.organization_id == legacy_organization.id,
                models.OrganizationMembership.practitioner_id == doctor.id,
                models.OrganizationMembership.active.is_(True),
            ).first()
            if membership is None:
                raise HTTPException(
                    status_code=403,
                    detail="The named physician is not an active member of this organization",
                )
            organization = legacy_organization
        elif registry_organization:
            provider = db.query(models.HealthcareProvider).filter(
                models.HealthcareProvider.account_id == doctor.id,
                models.HealthcareProvider.status == "VERIFIED",
            ).first()
            if provider is None or not provider_has_active_affiliation(db, provider.id, registry_organization.id):
                raise HTTPException(
                    status_code=403,
                    detail="The named physician is not an active verified member of this organization",
                )
            organization = registry_organization
        else:
            raise HTTPException(status_code=404, detail="Healthcare organization not found")

    granted_at = datetime.utcnow()
    consent = models.Consent(
        patient_id=current_user.id,
        grantee_id=doctor.id,
        organization_id=organization.id if organization else None,
        purpose="TREATMENT",
        resource_types=payload.resource_types,
        granted_at=granted_at,
        expires_at=granted_at + timedelta(days=payload.duration_days),
    )
    db.add(consent)
    db.flush()
    fhir_consent = fhir_builder.build_consent(
        consent.id,
        current_user.fhir_resource_id or current_user.id,
        doctor.fhir_resource_id or doctor.id,
        payload.resource_types,
        consent.granted_at,
        consent.expires_at,
        organization_ref=(
            organization.fhir_resource_id or organization.id
            if organization else None
        ),
        purpose=consent.purpose,
    )
    persist_resource(fhir_consent)
    db.commit()
    db.refresh(consent)

    audit_logger.log_event(db, current_user.id, "CONSENT_GRANTED", {
        "consent_id": consent.id, "grantee_id": doctor.id,
        "organization_id": consent.organization_id, "purpose": consent.purpose,
        "resource_types": payload.resource_types,
        "expires_at": consent.expires_at.isoformat(),
    })
    return _serialize(consent, db)


@router.get("/organizations")
def list_consent_organizations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    organization_user = aliased(models.User)
    practitioner_user = aliased(models.User)
    rows = db.query(
        organization_user,
        practitioner_user,
    ).join(
        models.OrganizationMembership,
        models.OrganizationMembership.organization_id == organization_user.id,
    ).join(
        practitioner_user,
        practitioner_user.id == models.OrganizationMembership.practitioner_id,
    ).filter(
        organization_user.role == "lab",
        practitioner_user.role == "doctor",
        models.OrganizationMembership.active.is_(True),
    ).order_by(
        organization_user.full_name.asc(),
        practitioner_user.full_name.asc(),
    ).all()
    organizations = {}
    for organization, practitioner in rows:
        entry = organizations.setdefault(organization.id, {
            "id": organization.id,
            "name": organization.full_name,
            "email": organization.email,
            "practitioners": [],
        })
        entry["practitioners"].append({
            "id": practitioner.id,
            "name": practitioner.full_name,
            "email": practitioner.email,
        })

    registry_rows = db.query(
        models.HealthcareOrganization,
        models.HealthcareProvider,
        models.User,
    ).join(
        models.OrganizationAffiliation,
        models.OrganizationAffiliation.organization_id == models.HealthcareOrganization.id,
    ).join(
        models.HealthcareProvider,
        models.HealthcareProvider.id == models.OrganizationAffiliation.provider_id,
    ).join(
        models.User,
        models.User.id == models.HealthcareProvider.account_id,
    ).filter(
        models.HealthcareOrganization.status == "APPROVED",
        models.HealthcareProvider.status == "VERIFIED",
        models.OrganizationAffiliation.status == "ACTIVE",
    ).all()
    now = datetime.utcnow()
    for organization, provider, practitioner in registry_rows:
        affiliation = db.query(models.OrganizationAffiliation).filter(
            models.OrganizationAffiliation.organization_id == organization.id,
            models.OrganizationAffiliation.provider_id == provider.id,
            models.OrganizationAffiliation.status == "ACTIVE",
        ).first()
        if affiliation and (
            affiliation.effective_from is None or affiliation.effective_from <= now
        ) and (
            affiliation.effective_until is None or affiliation.effective_until > now
        ):
            entry = organizations.setdefault(organization.id, {
                "id": organization.id,
                "name": organization.display_name,
                "email": organization.contact_email,
                "practitioners": [],
            })
            if not any(item["id"] == practitioner.id for item in entry["practitioners"]):
                entry["practitioners"].append({
                    "id": practitioner.id,
                    "name": practitioner.full_name,
                    "email": practitioner.email,
                })
    return list(organizations.values())


@router.post("/revoke/{consent_id}", response_model=schemas.ConsentOut)
def revoke_consent(consent_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("patient"))):
    consent = db.query(models.Consent).filter(
        models.Consent.id == consent_id, models.Consent.patient_id == current_user.id
    ).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")

    if consent.revoked_at is None:
        consent.revoked_at = datetime.utcnow()
        doctor = db.query(models.User).filter(models.User.id == consent.grantee_id).first()
        if doctor is None:
            raise HTTPException(status_code=409, detail="Consent grantee profile is unavailable")
        if fhir_mode() == "hapi":
            fhir_consent = authoritative_resource("Consent", consent.id, {})
        else:
            fhir_consent = fhir_builder.build_consent(
                consent.id,
                current_user.fhir_resource_id or current_user.id,
                doctor.fhir_resource_id or doctor.id,
                consent.resource_types,
                consent.granted_at,
                consent.expires_at,
                active=False,
            )
        fhir_consent["status"] = "inactive"
        persist_resource(fhir_consent)
        db.commit()
        db.refresh(consent)
        audit_logger.log_event(db, current_user.id, "CONSENT_REVOKED", {
            "consent_id": consent_id,
            "grantee_id": consent.grantee_id,
            "organization_id": consent.organization_id,
            "purpose": consent.purpose,
        })
    return _serialize(consent, db)


@router.get("/active", response_model=list[schemas.ConsentOut])
def list_my_consents(db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("patient"))):
    consents = db.query(models.Consent).filter(
        models.Consent.patient_id == current_user.id
    ).order_by(models.Consent.granted_at.desc()).all()
    return [_serialize(c, db) for c in consents]


@router.get("/access-history")
def list_access_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    events = db.query(models.AuditLog).filter(
        models.AuditLog.event_type == "DATA_ACCESSED",
        models.AuditLog.event_payload["patient_id"].as_string() == current_user.id,
        models.AuditLog.actor_id != current_user.id,
    ).order_by(models.AuditLog.created_at.desc()).limit(500).all()

    history = []
    for event in events:
        actor = db.query(models.User).filter(models.User.id == event.actor_id).first()
        history.append({
            "actor_name": actor.full_name if actor else "Unknown user",
            "actor_role": actor.role if actor else "unknown",
            "resource_type": event.event_payload.get("resource_type"),
            "resource_id": event.event_payload.get("resource_id"),
            "purpose": event.event_payload.get("purpose", "Record access"),
            "accessed_at": event.created_at,
        })
    return history
