from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import require_roles
from services import audit_logger, fhir_builder
from services.fhir_server import persist_resource
from services.registry import provider_has_active_affiliation, require_verified_provider

router = APIRouter(prefix="/api/v1", tags=["patient-provider care"])


def _eligible_affiliation(db: Session, provider: models.HealthcareProvider, organization_id: str) -> models.HealthcareOrganization:
    if provider.status != "VERIFIED":
        raise HTTPException(status_code=403, detail="Provider is not currently verified")
    organization = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Healthcare organization not found")
    if not provider_has_active_affiliation(db, provider.id, organization.id):
        raise HTTPException(status_code=403, detail="Provider is not eligible for this organization")
    return organization


def _provider_for_account(db: Session, account_id: str) -> models.HealthcareProvider:
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == account_id,
    ).first()
    if provider is None:
        raise HTTPException(status_code=403, detail="A verified provider profile is required")
    return provider


def _connection_out(db: Session, connection: models.CareConnection) -> dict:
    patient = db.query(models.User).filter(models.User.id == connection.patient_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == connection.provider_id).first()
    organization = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == connection.organization_id).first()
    return {
        "id": connection.id,
        "patient_id": connection.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "provider_id": connection.provider_id,
        "provider_name": provider.professional_name if provider else "Provider",
        "organization_id": connection.organization_id,
        "organization_name": organization.display_name if organization else "Organization",
        "status": connection.status,
        "reason": connection.reason,
        "provider_response": connection.provider_response,
        "initiated_at": connection.initiated_at,
        "responded_at": connection.responded_at,
        "closed_at": connection.closed_at,
    }


def _record_request_out(db: Session, request: models.ProviderRecordRequest) -> dict:
    patient = db.query(models.User).filter(models.User.id == request.patient_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == request.provider_id).first()
    organization = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == request.organization_id).first()
    return {
        "id": request.id,
        "patient_id": request.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "provider_id": request.provider_id,
        "provider_name": provider.professional_name if provider else "Provider",
        "organization_id": request.organization_id,
        "organization_name": organization.display_name if organization else "Organization",
        "resource_types": request.resource_types or [],
        "purpose": request.purpose,
        "requested_duration_days": request.requested_duration_days,
        "reason": request.reason,
        "status": request.status,
        "response_reason": request.response_reason,
        "consent_id": request.consent_id,
        "requested_at": request.requested_at,
        "responded_at": request.responded_at,
    }


@router.post("/care-connections", response_model=schemas.CareConnectionOut, status_code=201)
def initiate_care_connection(
    payload: schemas.CareConnectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == payload.provider_id,
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Verified provider not found")
    _eligible_affiliation(db, provider, payload.organization_id)

    connection = db.query(models.CareConnection).filter(
        models.CareConnection.patient_id == current_user.id,
        models.CareConnection.provider_id == provider.id,
        models.CareConnection.organization_id == payload.organization_id,
    ).with_for_update().first()
    now = datetime.utcnow()
    if connection:
        if connection.status in {"INITIATED", "ACCEPTED"}:
            raise HTTPException(status_code=409, detail="A care connection is already active")
        connection.status = "INITIATED"
        connection.reason = payload.reason
        connection.provider_response = None
        connection.responded_at = None
        connection.closed_at = None
        connection.initiated_at = now
    else:
        connection = models.CareConnection(
            patient_id=current_user.id,
            provider_id=provider.id,
            organization_id=payload.organization_id,
            status="INITIATED",
            reason=payload.reason,
            initiated_at=now,
        )
        db.add(connection)
        db.flush()
    audit_logger.log_event(db, current_user.id, "CARE_CONNECTION_INITIATED", {
        "connection_id": connection.id,
        "provider_id": provider.id,
        "organization_id": payload.organization_id,
    })
    return _connection_out(db, connection)


@router.get("/care-connections/me/patient", response_model=list[schemas.CareConnectionOut])
def patient_care_connections(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    connections = db.query(models.CareConnection).filter(
        models.CareConnection.patient_id == current_user.id,
    ).order_by(models.CareConnection.initiated_at.desc()).offset(offset).limit(limit).all()
    return [_connection_out(db, item) for item in connections]


@router.get("/care-connections/me/provider", response_model=list[schemas.CareConnectionOut])
def provider_care_connections(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    connections = db.query(models.CareConnection).filter(
        models.CareConnection.provider_id == provider.id,
    ).order_by(models.CareConnection.initiated_at.desc()).offset(offset).limit(limit).all()
    return [_connection_out(db, item) for item in connections]


@router.post("/care-connections/{connection_id}/provider-response", response_model=schemas.CareConnectionOut)
def respond_to_care_connection(
    connection_id: str,
    payload: schemas.CareConnectionResponse,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    connection = db.query(models.CareConnection).filter(
        models.CareConnection.id == connection_id,
        models.CareConnection.provider_id == provider.id,
    ).with_for_update().first()
    if connection is None:
        raise HTTPException(status_code=404, detail="Care connection not found")
    if payload.decision == "CLOSED":
        if connection.status != "ACCEPTED":
            raise HTTPException(status_code=409, detail="Only accepted connections can be closed")
        connection.closed_at = datetime.utcnow()
        connection.status = "CLOSED"
    else:
        if connection.status != "INITIATED":
            raise HTTPException(status_code=409, detail="This care connection is no longer awaiting a response")
        connection.status = payload.decision
        connection.responded_at = datetime.utcnow()
    connection.provider_response = payload.response
    audit_logger.log_event(db, current_user.id, f"CARE_CONNECTION_{connection.status}", {
        "connection_id": connection.id,
        "patient_id": connection.patient_id,
        "provider_id": provider.id,
        "organization_id": connection.organization_id,
    })
    return _connection_out(db, connection)


@router.post("/record-requests", response_model=schemas.ProviderRecordRequestOut, status_code=201)
def create_record_request(
    payload: schemas.ProviderRecordRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    organization = _eligible_affiliation(db, provider, payload.organization_id)
    patient = db.query(models.User).filter(
        models.User.id == payload.patient_id,
        models.User.role == "patient",
    ).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    duplicate = db.query(models.ProviderRecordRequest.id).filter(
        models.ProviderRecordRequest.patient_id == patient.id,
        models.ProviderRecordRequest.provider_id == provider.id,
        models.ProviderRecordRequest.organization_id == organization.id,
        models.ProviderRecordRequest.status == "REQUESTED",
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A record request is already awaiting this patient's decision")
    request = models.ProviderRecordRequest(
        patient_id=patient.id,
        provider_id=provider.id,
        organization_id=organization.id,
        resource_types=payload.resource_types,
        purpose="TREATMENT",
        requested_duration_days=payload.requested_duration_days,
        reason=payload.reason,
        status="REQUESTED",
    )
    db.add(request)
    db.flush()
    audit_logger.log_event(db, current_user.id, "RECORD_ACCESS_REQUESTED", {
        "record_request_id": request.id,
        "patient_id": patient.id,
        "provider_id": provider.id,
        "organization_id": organization.id,
        "resource_types": payload.resource_types,
        "purpose": "TREATMENT",
        "requested_duration_days": payload.requested_duration_days,
    })
    return _record_request_out(db, request)


@router.get("/record-requests/me/provider", response_model=list[schemas.ProviderRecordRequestOut])
def provider_record_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    requests = db.query(models.ProviderRecordRequest).filter(
        models.ProviderRecordRequest.provider_id == provider.id,
    ).order_by(models.ProviderRecordRequest.requested_at.desc()).offset(offset).limit(limit).all()
    return [_record_request_out(db, item) for item in requests]


@router.get("/record-requests/me/patient", response_model=list[schemas.ProviderRecordRequestOut])
def patient_record_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    requests = db.query(models.ProviderRecordRequest).filter(
        models.ProviderRecordRequest.patient_id == current_user.id,
    ).order_by(models.ProviderRecordRequest.requested_at.desc()).offset(offset).limit(limit).all()
    return [_record_request_out(db, item) for item in requests]


@router.post("/record-requests/{request_id}/patient-decision", response_model=schemas.ProviderRecordRequestOut)
def decide_record_request(
    request_id: str,
    payload: schemas.ProviderRecordRequestDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    request = db.query(models.ProviderRecordRequest).filter(
        models.ProviderRecordRequest.id == request_id,
        models.ProviderRecordRequest.patient_id == current_user.id,
    ).with_for_update().first()
    if request is None:
        raise HTTPException(status_code=404, detail="Record request not found")
    if request.status != "REQUESTED":
        raise HTTPException(status_code=409, detail="This record request has already been decided")

    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == request.provider_id,
    ).first()
    if provider is None:
        raise HTTPException(status_code=409, detail="Provider profile is unavailable")
    if payload.decision == "APPROVED":
        _eligible_affiliation(db, provider, request.organization_id)
        account = db.query(models.User).filter(models.User.id == provider.account_id).first()
        if account is None:
            raise HTTPException(status_code=409, detail="Provider account is unavailable")
        now = datetime.utcnow()
        consent = models.Consent(
            patient_id=current_user.id,
            grantee_id=account.id,
            organization_id=request.organization_id,
            resource_types=request.resource_types,
            purpose="TREATMENT",
            granted_at=now,
            expires_at=now + timedelta(days=request.requested_duration_days),
        )
        db.add(consent)
        db.flush()
        fhir_consent = fhir_builder.build_consent(
            consent.id,
            current_user.fhir_resource_id or current_user.id,
            account.fhir_resource_id or account.id,
            request.resource_types,
            consent.granted_at,
            consent.expires_at,
            organization_ref=request.organization_id,
            purpose="TREATMENT",
        )
        persist_resource(fhir_consent)
        request.consent_id = consent.id
        request.status = "APPROVED"
    else:
        request.status = "REJECTED"
    request.response_reason = payload.response_reason
    request.responded_at = datetime.utcnow()
    audit_logger.log_event(db, current_user.id, f"RECORD_ACCESS_REQUEST_{request.status}", {
        "record_request_id": request.id,
        "patient_id": current_user.id,
        "provider_id": provider.id,
        "organization_id": request.organization_id,
        "consent_id": request.consent_id,
        "resource_types": request.resource_types,
        "requested_duration_days": request.requested_duration_days,
        "purpose": "TREATMENT",
    })
    return _record_request_out(db, request)


@router.post("/record-requests/{request_id}/cancel", response_model=schemas.ProviderRecordRequestOut)
def cancel_record_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    request = db.query(models.ProviderRecordRequest).filter(
        models.ProviderRecordRequest.id == request_id,
        models.ProviderRecordRequest.provider_id == provider.id,
    ).with_for_update().first()
    if request is None:
        raise HTTPException(status_code=404, detail="Record request not found")
    if request.status != "REQUESTED":
        raise HTTPException(status_code=409, detail="Only pending record requests can be cancelled")
    request.status = "CANCELLED"
    request.response_reason = "Cancelled by provider"
    request.responded_at = datetime.utcnow()
    audit_logger.log_event(db, current_user.id, "RECORD_ACCESS_REQUEST_CANCELLED", {
        "record_request_id": request.id,
        "patient_id": request.patient_id,
        "provider_id": provider.id,
        "organization_id": request.organization_id,
    })
    return _record_request_out(db, request)
