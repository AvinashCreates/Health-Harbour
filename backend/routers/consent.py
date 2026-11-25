from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import require_roles
from services import audit_logger
from services import fhir_builder
from services.fhir_server import authoritative_resource, fhir_mode, persist_resource

router = APIRouter(prefix="/consent", tags=["consent"])


def _serialize(c: models.Consent) -> schemas.ConsentOut:
    now = datetime.utcnow()
    return schemas.ConsentOut(
        id=c.id, patient_id=c.patient_id, grantee_id=c.grantee_id,
        resource_types=c.resource_types, granted_at=c.granted_at,
        expires_at=c.expires_at, revoked_at=c.revoked_at,
        is_active=(c.revoked_at is None and c.expires_at > now),
    )


@router.post("/grant", response_model=schemas.ConsentOut)
def grant_consent(payload: schemas.ConsentGrant, db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("patient"))):
    doctor = db.query(models.User).filter(models.User.email == payload.doctor_email, models.User.role == "doctor").first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    granted_at = datetime.utcnow()
    consent = models.Consent(
        patient_id=current_user.id,
        grantee_id=doctor.id,
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
    )
    persist_resource(fhir_consent)
    db.commit()
    db.refresh(consent)

    audit_logger.log_event(db, current_user.id, "CONSENT_GRANTED", {
        "consent_id": consent.id, "grantee_id": doctor.id, "resource_types": payload.resource_types,
        "expires_at": consent.expires_at.isoformat(),
    })
    return _serialize(consent)


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
            "consent_id": consent_id, "grantee_id": consent.grantee_id,
        })
    return _serialize(consent)


@router.get("/active", response_model=list[schemas.ConsentOut])
def list_my_consents(db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("patient"))):
    consents = db.query(models.Consent).filter(
        models.Consent.patient_id == current_user.id
    ).order_by(models.Consent.granted_at.desc()).all()
    return [_serialize(c) for c in consents]


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
