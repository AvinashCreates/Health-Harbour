from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import require_roles
from services import audit_logger, fhir_builder
from services.fhir_sync import queue_fhir_resource
from services.registry import require_verified_provider

router = APIRouter(prefix="/api/v1", tags=["clinical workflows"])


def _prescription_out(db: Session, prescription: models.Prescription) -> dict:
    patient = db.query(models.User).filter(models.User.id == prescription.patient_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == prescription.provider_id).first()
    organization = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == prescription.organization_id).first()
    return {
        "id": prescription.id,
        "patient_id": prescription.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "provider_id": prescription.provider_id,
        "provider_name": provider.professional_name if provider else "Provider",
        "organization_id": prescription.organization_id,
        "organization_name": organization.display_name if organization else "Organization",
        "medication_name": prescription.medication_name,
        "dosage": prescription.dosage,
        "route": prescription.route,
        "frequency": prescription.frequency,
        "duration": prescription.duration,
        "quantity": prescription.quantity,
        "instructions": prescription.instructions,
        "status": prescription.status,
        "created_at": prescription.created_at,
        "updated_at": prescription.updated_at,
    }


def _review_out(db: Session, review: models.PhysicianClinicalReview) -> dict:
    patient = db.query(models.User).filter(models.User.id == review.patient_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == review.provider_id).first()
    organization = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == review.organization_id).first()
    return {
        "id": review.id,
        "patient_id": review.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "provider_id": review.provider_id,
        "provider_name": provider.professional_name if provider else "Provider",
        "organization_id": review.organization_id,
        "organization_name": organization.display_name if organization else "Organization",
        "diagnostic_report_id": review.diagnostic_report_id,
        "service_request_id": review.service_request_id,
        "status": review.status,
        "clinical_note": review.clinical_note,
        "reviewed_at": review.reviewed_at,
        "created_at": review.created_at,
    }


def _active_consent(db: Session, patient_id: str, provider_account_id: str, resource_type: str, organization_id: str | None = None) -> bool:
    consent = db.query(models.Consent).filter(
        models.Consent.patient_id == patient_id,
        models.Consent.grantee_id == provider_account_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > datetime.utcnow(),
    )
    if organization_id:
        consent = consent.filter(or_(models.Consent.organization_id.is_(None), models.Consent.organization_id == organization_id))
    return any(resource_type in (item.resource_types or []) for item in consent.all())


@router.post("/prescriptions", response_model=schemas.PrescriptionOut, status_code=201)
def create_prescription(
    payload: schemas.PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user, payload.organization_id)
    patient = db.query(models.User).filter(models.User.id == payload.patient_id, models.User.role == "patient").first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _active_consent(db, patient.id, current_user.id, "MedicationRequest", payload.organization_id):
        raise HTTPException(status_code=403, detail="Patient consent for MedicationRequest access is required")

    prescription = models.Prescription(
        patient_id=patient.id,
        provider_id=provider.id,
        organization_id=payload.organization_id,
        medication_name=payload.medication_name,
        dosage=payload.dosage,
        route=payload.route,
        frequency=payload.frequency,
        duration=payload.duration,
        quantity=payload.quantity,
        instructions=payload.instructions,
        status="ACTIVE" if payload.activate else "DRAFT",
    )
    db.add(prescription)
    db.flush()
    db.add(models.PrescriptionHistory(
        prescription_id=prescription.id,
        actor_id=current_user.id,
        from_status=None,
        to_status=prescription.status,
        reason="Prescription created",
    ))

    medication_request = {
        "resourceType": "MedicationRequest",
        "id": prescription.id,
        "status": "active" if prescription.status == "ACTIVE" else "draft",
        "intent": "order",
        "medicationCodeableConcept": {"text": prescription.medication_name},
        "subject": {"reference": f"Patient/{patient.fhir_resource_id or patient.id}"},
        "requester": {"reference": f"Practitioner/{provider.fhir_resource_id or provider.id}"},
        "dosageInstruction": [{
            "text": " ".join(value for value in (prescription.dosage, prescription.route, prescription.frequency, prescription.instructions) if value),
        }],
    }
    queue_fhir_resource(db, "MedicationRequest", prescription.id, medication_request)
    audit_logger.log_event(db, current_user.id, "PRESCRIPTION_CREATED", {
        "prescription_id": prescription.id,
        "patient_id": patient.id,
        "provider_id": provider.id,
        "organization_id": payload.organization_id,
        "medication_name": prescription.medication_name,
    })
    return _prescription_out(db, prescription)


@router.post("/prescriptions/{prescription_id}/transition", response_model=schemas.PrescriptionOut)
def transition_prescription(
    prescription_id: str,
    payload: schemas.PrescriptionTransition,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    prescription = db.query(models.Prescription).filter(
        models.Prescription.id == prescription_id,
        models.Prescription.provider_id == provider.id,
    ).with_for_update().first()
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if prescription.status in {"CANCELLED", "COMPLETED", "STOPPED"}:
        raise HTTPException(status_code=409, detail="This prescription is already terminal")
    previous = prescription.status
    prescription.status = payload.status
    prescription.updated_at = datetime.utcnow()
    db.add(models.PrescriptionHistory(
        prescription_id=prescription.id,
        actor_id=current_user.id,
        from_status=previous,
        to_status=payload.status,
        reason=payload.reason,
    ))
    audit_logger.log_event(db, current_user.id, f"PRESCRIPTION_{payload.status}", {
        "prescription_id": prescription.id,
        "patient_id": prescription.patient_id,
        "provider_id": prescription.provider_id,
        "organization_id": prescription.organization_id,
    })
    return _prescription_out(db, prescription)


@router.get("/prescriptions/me/patient", response_model=list[schemas.PrescriptionOut])
def patient_prescriptions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    rows = db.query(models.Prescription).filter(
        models.Prescription.patient_id == current_user.id,
    ).order_by(models.Prescription.created_at.desc()).offset(offset).limit(limit).all()
    return [_prescription_out(db, row) for row in rows]


@router.get("/prescriptions/me/provider", response_model=list[schemas.PrescriptionOut])
def provider_prescriptions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    rows = db.query(models.Prescription).filter(
        models.Prescription.provider_id == provider.id,
    ).order_by(models.Prescription.created_at.desc()).offset(offset).limit(limit).all()
    return [_prescription_out(db, row) for row in rows]


@router.post("/clinical-reviews", response_model=schemas.PhysicianClinicalReviewOut, status_code=201)
def create_clinical_review(
    payload: schemas.PhysicianClinicalReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user, payload.organization_id)
    patient = db.query(models.User).filter(models.User.id == payload.patient_id, models.User.role == "patient").first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _active_consent(db, patient.id, current_user.id, "DiagnosticReport", payload.organization_id):
        raise HTTPException(status_code=403, detail="Patient consent for DiagnosticReport access is required")

    if payload.diagnostic_report_id:
        report = db.query(models.FHIRResource).filter(
            models.FHIRResource.resource_type == "DiagnosticReport",
            models.FHIRResource.owner_id == patient.id,
            ((models.FHIRResource.id == payload.diagnostic_report_id) | (models.FHIRResource.fhir_id == payload.diagnostic_report_id)),
        ).first()
        if report is None:
            raise HTTPException(status_code=404, detail="Diagnostic report not found")
    if payload.service_request_id:
        request = db.query(models.FHIRResource).filter(
            models.FHIRResource.resource_type == "ServiceRequest",
            models.FHIRResource.owner_id == patient.id,
            ((models.FHIRResource.id == payload.service_request_id) | (models.FHIRResource.fhir_id == payload.service_request_id)),
        ).first()
        if request is None:
            raise HTTPException(status_code=404, detail="Laboratory order not found")

    review = models.PhysicianClinicalReview(
        patient_id=patient.id,
        provider_id=provider.id,
        organization_id=payload.organization_id,
        diagnostic_report_id=payload.diagnostic_report_id,
        service_request_id=payload.service_request_id,
        status=payload.status,
        clinical_note=payload.clinical_note,
        reviewed_at=datetime.utcnow(),
    )
    db.add(review)
    db.flush()
    audit_logger.log_event(db, current_user.id, "PHYSICIAN_CLINICAL_REVIEW_RECORDED", {
        "review_id": review.id,
        "patient_id": patient.id,
        "provider_id": provider.id,
        "organization_id": payload.organization_id,
        "diagnostic_report_id": payload.diagnostic_report_id,
        "service_request_id": payload.service_request_id,
        "status": payload.status,
    })
    return _review_out(db, review)


@router.get("/clinical-reviews/me/patient", response_model=list[schemas.PhysicianClinicalReviewOut])
def patient_clinical_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    rows = db.query(models.PhysicianClinicalReview).filter(
        models.PhysicianClinicalReview.patient_id == current_user.id,
    ).order_by(models.PhysicianClinicalReview.created_at.desc()).offset(offset).limit(limit).all()
    return [_review_out(db, row) for row in rows]


@router.get("/clinical-reviews/me/provider", response_model=list[schemas.PhysicianClinicalReviewOut])
def provider_clinical_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    rows = db.query(models.PhysicianClinicalReview).filter(
        models.PhysicianClinicalReview.provider_id == provider.id,
    ).order_by(models.PhysicianClinicalReview.created_at.desc()).offset(offset).limit(limit).all()
    return [_review_out(db, row) for row in rows]
