from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import require_roles
from services import audit_logger, fhir_builder
from services.fhir_sync import queue_fhir_resource
from services.document_storage import EncryptionConfigurationError, get_document_storage
from services.registry import require_verified_provider

router = APIRouter(prefix="/api/v1", tags=["cross-hospital exchange"])


def _exchange_out(db: Session, exchange: models.CrossHospitalExchangeRequest) -> dict:
    patient = db.query(models.User).filter(models.User.id == exchange.patient_id).first()
    requester_org = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == exchange.requesting_organization_id).first()
    source_org = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == exchange.source_organization_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == exchange.requesting_provider_id).first()
    return {
        "id": exchange.id,
        "patient_id": exchange.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "requesting_organization_id": exchange.requesting_organization_id,
        "requesting_organization_name": requester_org.display_name if requester_org else "Organization",
        "requesting_provider_id": exchange.requesting_provider_id,
        "requesting_provider_name": provider.professional_name if provider else "Provider",
        "source_organization_id": exchange.source_organization_id,
        "source_organization_name": source_org.display_name if source_org else "Organization",
        "resource_types": exchange.resource_types or [],
        "purpose": exchange.purpose,
        "requested_duration_days": exchange.requested_duration_days,
        "reason": exchange.reason,
        "status": exchange.status,
        "consent_id": exchange.consent_id,
        "response_reason": exchange.response_reason,
        "requested_at": exchange.requested_at,
        "responded_at": exchange.responded_at,
        "expires_at": exchange.expires_at,
    }


def _require_requesting_provider(db: Session, user: models.User, exchange: models.CrossHospitalExchangeRequest) -> models.HealthcareProvider:
    provider = require_verified_provider(db, user, exchange.requesting_organization_id)
    if provider.id != exchange.requesting_provider_id:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    return provider


@router.post("/cross-hospital/exchange-requests", response_model=schemas.CrossHospitalExchangeOut, status_code=201)
def create_exchange_request(
    payload: schemas.CrossHospitalExchangeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user, payload.requesting_organization_id)
    if payload.requesting_organization_id == payload.source_organization_id:
        raise HTTPException(status_code=422, detail="Requesting and source organizations must differ")
    patient = db.query(models.User).filter(models.User.id == payload.patient_id, models.User.role == "patient").first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    requesting = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == payload.requesting_organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    source = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == payload.source_organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if requesting is None or source is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    existing = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.patient_id == patient.id,
        models.CrossHospitalExchangeRequest.requesting_provider_id == provider.id,
        models.CrossHospitalExchangeRequest.requesting_organization_id == requesting.id,
        models.CrossHospitalExchangeRequest.source_organization_id == source.id,
        models.CrossHospitalExchangeRequest.status == "REQUESTED",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A pending exchange request already exists")

    exchange = models.CrossHospitalExchangeRequest(
        patient_id=patient.id,
        requesting_organization_id=requesting.id,
        requesting_provider_id=provider.id,
        source_organization_id=source.id,
        resource_types=payload.resource_types,
        purpose="TREATMENT",
        requested_duration_days=payload.requested_duration_days,
        reason=payload.reason,
        status="REQUESTED",
    )
    db.add(exchange)
    db.flush()
    audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_EXCHANGE_REQUESTED", {
        "exchange_request_id": exchange.id,
        "patient_id": patient.id,
        "requesting_organization_id": requesting.id,
        "source_organization_id": source.id,
        "requesting_provider_id": provider.id,
        "resource_types": payload.resource_types,
        "purpose": "TREATMENT",
    })
    return _exchange_out(db, exchange)


@router.get("/cross-hospital/exchange-requests/me/patient", response_model=list[schemas.CrossHospitalExchangeOut])
def patient_exchange_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    rows = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.patient_id == current_user.id,
    ).order_by(models.CrossHospitalExchangeRequest.requested_at.desc()).offset(offset).limit(limit).all()
    return [_exchange_out(db, row) for row in rows]


@router.get("/cross-hospital/exchange-requests/me/provider", response_model=list[schemas.CrossHospitalExchangeOut])
def provider_exchange_requests(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    provider = require_verified_provider(db, current_user)
    rows = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.requesting_provider_id == provider.id,
    ).order_by(models.CrossHospitalExchangeRequest.requested_at.desc()).offset(offset).limit(limit).all()
    return [_exchange_out(db, row) for row in rows]


@router.post("/cross-hospital/exchange-requests/{exchange_id}/patient-decision", response_model=schemas.CrossHospitalExchangeOut)
def decide_exchange_request(
    exchange_id: str,
    payload: schemas.CrossHospitalExchangeDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    exchange = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.id == exchange_id,
        models.CrossHospitalExchangeRequest.patient_id == current_user.id,
    ).with_for_update().first()
    if exchange is None:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    if payload.decision == "REVOKED":
        if exchange.status != "APPROVED" or exchange.consent_id is None:
            raise HTTPException(status_code=409, detail="Only approved exchange consent can be revoked")
        consent = db.query(models.Consent).filter(
            models.Consent.id == exchange.consent_id,
            models.Consent.patient_id == current_user.id,
        ).with_for_update().first()
        if consent:
            consent.revoked_at = datetime.utcnow()
            fhir_consent = fhir_builder.build_consent(
                consent.id,
                current_user.fhir_resource_id or current_user.id,
                db.query(models.User).filter(models.User.id == consent.grantee_id).one().fhir_resource_id or consent.grantee_id,
                consent.resource_types,
                consent.granted_at,
                consent.expires_at,
                active=False,
                organization_ref=consent.organization_id,
                purpose="TREATMENT",
            )
            fhir_consent["status"] = "inactive"
            queue_fhir_resource(db, "Consent", consent.id, fhir_consent)
        exchange.status = "REVOKED"
        exchange.response_reason = payload.reason
        exchange.responded_at = datetime.utcnow()
        exchange.expires_at = exchange.responded_at
        audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_CONSENT_REVOKED", {
            "exchange_request_id": exchange.id,
            "consent_id": exchange.consent_id,
            "patient_id": current_user.id,
            "requesting_organization_id": exchange.requesting_organization_id,
            "source_organization_id": exchange.source_organization_id,
        })
        return _exchange_out(db, exchange)

    if exchange.status != "REQUESTED":
        raise HTTPException(status_code=409, detail="This exchange request has already been decided")
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == exchange.requesting_provider_id).first()
    if provider is None:
        raise HTTPException(status_code=409, detail="Requesting provider is unavailable")
    if payload.decision == "APPROVED":
        account = db.query(models.User).filter(models.User.id == provider.account_id).first()
        if account is None:
            raise HTTPException(status_code=409, detail="Requesting provider account is unavailable")
        requesting = db.query(models.HealthcareOrganization).filter(
            models.HealthcareOrganization.id == exchange.requesting_organization_id,
            models.HealthcareOrganization.status == "APPROVED",
        ).first()
        if requesting is None:
            raise HTTPException(status_code=409, detail="Requesting organization is not approved")
        now = datetime.utcnow()
        consent = models.Consent(
            patient_id=current_user.id,
            grantee_id=account.id,
            organization_id=requesting.id,
            resource_types=exchange.resource_types,
            purpose="TREATMENT",
            granted_at=now,
            expires_at=now + timedelta(days=exchange.requested_duration_days),
        )
        db.add(consent)
        db.flush()
        fhir_consent = fhir_builder.build_consent(
            consent.id,
            current_user.fhir_resource_id or current_user.id,
            account.fhir_resource_id or account.id,
            consent.resource_types,
            consent.granted_at,
            consent.expires_at,
            organization_ref=requesting.id,
            purpose="TREATMENT",
        )
        queue_fhir_resource(db, "Consent", consent.id, fhir_consent)
        exchange.consent_id = consent.id
        exchange.status = "APPROVED"
        exchange.expires_at = consent.expires_at
        event_type = "CROSS_HOSPITAL_CONSENT_GRANTED"
    else:
        exchange.status = "REJECTED"
        event_type = "CROSS_HOSPITAL_CONSENT_REJECTED"
    exchange.response_reason = payload.reason
    exchange.responded_at = datetime.utcnow()
    audit_logger.log_event(db, current_user.id, event_type, {
        "exchange_request_id": exchange.id,
        "consent_id": exchange.consent_id,
        "patient_id": current_user.id,
        "requesting_organization_id": exchange.requesting_organization_id,
        "source_organization_id": exchange.source_organization_id,
        "requesting_provider_id": exchange.requesting_provider_id,
        "resource_types": exchange.resource_types,
    })
    return _exchange_out(db, exchange)


@router.get("/cross-hospital/exchange-requests/{exchange_id}/documents", response_model=list[dict])
def exchange_documents(
    exchange_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    exchange = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.id == exchange_id,
    ).first()
    if exchange is None:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    _require_requesting_provider(db, current_user, exchange)
    if exchange.status != "APPROVED" or exchange.consent_id is None:
        raise HTTPException(status_code=403, detail="Approved exchange consent is required")
    source_org = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == exchange.source_organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if source_org is None:
        raise HTTPException(status_code=403, detail="Source organization is not approved")
    consent = db.query(models.Consent).filter(
        models.Consent.id == exchange.consent_id,
        models.Consent.patient_id == exchange.patient_id,
        models.Consent.grantee_id == current_user.id,
        models.Consent.organization_id == exchange.requesting_organization_id,
        models.Consent.revoked_at.is_(None),
    ).with_for_update().first()
    if consent is None or consent.expires_at <= datetime.utcnow() or "Document" not in (consent.resource_types or []):
        raise HTTPException(status_code=403, detail="Document consent is expired or out of scope")

    files = db.query(models.ClinicalFile).filter(
        models.ClinicalFile.patient_id == exchange.patient_id,
        models.ClinicalFile.deleted_at.is_(None),
        models.ClinicalFile.processing_status == "CLEAN",
        models.ClinicalFile.source_organization_id == exchange.source_organization_id,
    ).all()
    return [{
        "id": file.id,
        "filename": file.filename,
        "category": file.category,
        "media_type": file.media_type,
        "size_bytes": file.size_bytes,
        "sha256": file.sha256,
        "source_organization_id": file.source_organization_id,
        "custodian_organization_id": file.custodian_organization_id,
        "created_at": file.created_at,
    } for file in files]


@router.get("/cross-hospital/exchange-requests/{exchange_id}/documents/{document_id}/download")
def download_cross_hospital_document(
    exchange_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    exchange = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.id == exchange_id,
    ).first()
    if exchange is None:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    provider = _require_requesting_provider(db, current_user, exchange)
    if exchange.status != "APPROVED" or exchange.consent_id is None:
        audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_DOCUMENT_ACCESS_DENIED", {
            "exchange_request_id": exchange.id,
            "document_id": document_id,
            "patient_id": exchange.patient_id,
            "requesting_organization_id": exchange.requesting_organization_id,
            "source_organization_id": exchange.source_organization_id,
            "outcome": "denied",
        })
        raise HTTPException(status_code=403, detail="Approved exchange consent is required")
    source_org = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == exchange.source_organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if source_org is None:
        raise HTTPException(status_code=403, detail="Source organization is not approved")
    consent = db.query(models.Consent).filter(
        models.Consent.id == exchange.consent_id,
        models.Consent.patient_id == exchange.patient_id,
        models.Consent.grantee_id == current_user.id,
        models.Consent.organization_id == exchange.requesting_organization_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.purpose == "TREATMENT",
    ).with_for_update().first()
    if consent is None or consent.expires_at <= datetime.utcnow() or "Document" not in (consent.resource_types or []):
        audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_DOCUMENT_ACCESS_DENIED", {
            "exchange_request_id": exchange.id,
            "document_id": document_id,
            "patient_id": exchange.patient_id,
            "requesting_organization_id": exchange.requesting_organization_id,
            "source_organization_id": exchange.source_organization_id,
            "outcome": "denied",
        })
        raise HTTPException(status_code=403, detail="Document consent is expired, revoked, or out of scope")

    consent = db.query(models.Consent).filter(
        models.Consent.id == exchange.consent_id,
        models.Consent.patient_id == exchange.patient_id,
        models.Consent.grantee_id == current_user.id,
        models.Consent.organization_id == exchange.requesting_organization_id,
        models.Consent.revoked_at.is_(None),
    ).with_for_update().first()
    if consent is None or consent.expires_at <= datetime.utcnow() or "Document" not in (consent.resource_types or []):
        audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_DOCUMENT_ACCESS_DENIED", {
            "exchange_request_id": exchange.id,
            "document_id": document_id,
            "outcome": "denied",
            "reason": "authorization_rechecked",
        })
        raise HTTPException(status_code=403, detail="Document consent is expired, revoked, or out of scope")

    source_file = db.query(models.ClinicalFile).filter(
        models.ClinicalFile.id == document_id,
        models.ClinicalFile.patient_id == exchange.patient_id,
        models.ClinicalFile.deleted_at.is_(None),
        models.ClinicalFile.processing_status == "CLEAN",
        models.ClinicalFile.source_organization_id == exchange.source_organization_id,
    ).first()
    if source_file is None:
        raise HTTPException(status_code=404, detail="Source document not found")

    storage = get_document_storage()
    try:
        content = storage.read_authorized(
            source_file.storage_key,
            getattr(source_file, "encryption_version", None),
            getattr(source_file, "encryption_key_id", None),
        )
    except EncryptionConfigurationError as exc:
        audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_DOCUMENT_ACCESS_DENIED", {
            "exchange_request_id": exchange.id,
            "document_id": document_id,
            "patient_id": exchange.patient_id,
            "outcome": "denied",
            "reason": "encrypted_document_unavailable",
        })
        raise HTTPException(status_code=503, detail="The stored document could not be decrypted") from exc

    audit_logger.log_event(db, current_user.id, "CROSS_HOSPITAL_DOCUMENT_RETRIEVED", {
        "exchange_request_id": exchange.id,
        "document_id": source_file.id,
        "patient_id": exchange.patient_id,
        "requesting_organization_id": exchange.requesting_organization_id,
        "source_organization_id": exchange.source_organization_id,
        "requesting_provider_id": provider.id,
        "consent_id": consent.id,
        "resource_type": "DocumentReference",
        "outcome": "granted",
    })
    safe_filename = source_file.filename.replace("\\", "_").replace('"', "_").replace("%", "_")
    return Response(
        content=content,
        media_type=source_file.media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(len(content)),
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
        },
    )


@router.post("/cross-hospital/exchange-requests/{exchange_id}/documents/{document_id}/import", response_model=schemas.CrossOrganizationDocumentImportOut)
def import_exchange_document(
    exchange_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    exchange = db.query(models.CrossHospitalExchangeRequest).filter(
        models.CrossHospitalExchangeRequest.id == exchange_id,
    ).first()
    if exchange is None:
        raise HTTPException(status_code=404, detail="Exchange request not found")
    provider = _require_requesting_provider(db, current_user, exchange)
    if exchange.status != "APPROVED" or exchange.consent_id is None:
        raise HTTPException(status_code=403, detail="Approved exchange consent is required")
    source_org = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == exchange.source_organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if source_org is None:
        raise HTTPException(status_code=403, detail="Source organization is not approved")
    consent = db.query(models.Consent).filter(
        models.Consent.id == exchange.consent_id,
        models.Consent.patient_id == exchange.patient_id,
        models.Consent.grantee_id == current_user.id,
        models.Consent.organization_id == exchange.requesting_organization_id,
        models.Consent.revoked_at.is_(None),
    ).with_for_update().first()
    if consent is None or consent.expires_at <= datetime.utcnow() or "Document" not in (consent.resource_types or []):
        raise HTTPException(status_code=403, detail="Document consent is expired or out of scope")

    consent = db.query(models.Consent).filter(
        models.Consent.id == exchange.consent_id,
        models.Consent.patient_id == exchange.patient_id,
        models.Consent.grantee_id == current_user.id,
        models.Consent.organization_id == exchange.requesting_organization_id,
        models.Consent.revoked_at.is_(None),
    ).with_for_update().first()
    if consent is None or consent.expires_at <= datetime.utcnow() or "Document" not in (consent.resource_types or []):
        raise HTTPException(status_code=403, detail="Document consent is expired or out of scope")

    source_file = db.query(models.ClinicalFile).filter(
        models.ClinicalFile.id == document_id,
        models.ClinicalFile.patient_id == exchange.patient_id,
        models.ClinicalFile.deleted_at.is_(None),
        models.ClinicalFile.processing_status == "CLEAN",
        models.ClinicalFile.source_organization_id == exchange.source_organization_id,
    ).first()
    if source_file is None:
        raise HTTPException(status_code=404, detail="Source document not found")

    existing = db.query(models.CrossOrganizationDocumentImport).filter(
        models.CrossOrganizationDocumentImport.exchange_request_id == exchange.id,
        models.CrossOrganizationDocumentImport.source_document_id == source_file.id,
    ).first()
    if existing:
        return _import_out(existing)

    import_record = models.CrossOrganizationDocumentImport(
        exchange_request_id=exchange.id,
        source_document_id=source_file.id,
        source_organization_id=exchange.source_organization_id,
        receiving_organization_id=exchange.requesting_organization_id,
        importing_provider_id=provider.id,
        consent_id=consent.id,
        checksum=source_file.sha256,
        integrity_verified=bool(source_file.sha256 and len(source_file.sha256) == 64),
        status="IMPORTED",
        imported_at=datetime.utcnow(),
    )
    db.add(import_record)
    db.flush()
    audit_logger.log_event(db, current_user.id, "CROSS_ORGANIZATION_DOCUMENT_IMPORTED", {
        "exchange_request_id": exchange.id,
        "import_id": import_record.id,
        "source_document_id": source_file.id,
        "source_organization_id": exchange.source_organization_id,
        "receiving_organization_id": exchange.requesting_organization_id,
        "consent_id": consent.id,
        "checksum": source_file.sha256,
        "integrity_verified": import_record.integrity_verified,
    })
    return _import_out(import_record)


def _import_out(record: models.CrossOrganizationDocumentImport) -> dict:
    return {
        "id": record.id,
        "exchange_request_id": record.exchange_request_id,
        "source_document_id": record.source_document_id,
        "source_organization_id": record.source_organization_id,
        "receiving_organization_id": record.receiving_organization_id,
        "importing_provider_id": record.importing_provider_id,
        "consent_id": record.consent_id,
        "checksum": record.checksum,
        "integrity_verified": record.integrity_verified,
        "status": record.status,
        "failure_reason": record.failure_reason,
        "imported_at": record.imported_at,
        "created_at": record.created_at,
    }
