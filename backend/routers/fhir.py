import hashlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user, require_roles
from services import audit_logger, fhir_builder
from services.fhir_server import authoritative_resource, persist_resource

router = APIRouter(prefix="/fhir", tags=["fhir"])

WORKFLOW_STATES = (
    "REQUESTED",
    "ACCEPTED",
    "ASSIGNED",
    "SPECIMEN_REGISTERED",
    "PROCESSING",
    "RESULTS_SUBMITTED",
    "FINALIZED",
    "PHYSICIAN_REVIEWED",
)


def _has_active_consent(db: Session, patient_id: str, grantee_id: str, resource_type: str) -> bool:
    now = datetime.utcnow()
    consents = db.query(models.Consent).filter(
        models.Consent.patient_id == patient_id,
        models.Consent.grantee_id == grantee_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > now,
    ).all()
    return any(resource_type in consent.resource_types for consent in consents)


def _consented_patient_ids(db: Session, grantee_id: str, resource_type: str) -> list[str]:
    now = datetime.utcnow()
    rows = db.query(models.Consent).filter(
        models.Consent.grantee_id == grantee_id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > now,
    ).all()
    return [consent.patient_id for consent in rows if resource_type in consent.resource_types]


def _get_workflow(db: Session, service_request_id: str) -> models.LaboratoryWorkflow:
    workflow = db.query(models.LaboratoryWorkflow).filter(
        models.LaboratoryWorkflow.service_request_id == service_request_id,
    ).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Laboratory workflow not found")
    return workflow


def _require_state(workflow: models.LaboratoryWorkflow, expected: str) -> None:
    if workflow.status != expected:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid workflow transition: expected {expected}, found {workflow.status}",
        )


def _transition(
    db: Session,
    workflow: models.LaboratoryWorkflow,
    actor_id: str,
    to_status: str,
    note: str | None = None,
) -> None:
    from_status = workflow.status
    workflow.status = to_status
    workflow.updated_at = datetime.utcnow()
    db.add(models.WorkflowTransition(
        workflow_id=workflow.id,
        actor_id=actor_id,
        from_status=from_status,
        to_status=to_status,
        note=note,
    ))
    db.commit()
    audit_logger.log_event(db, actor_id, "LAB_WORKFLOW_TRANSITION", {
        "workflow_id": workflow.id,
        "service_request_id": workflow.service_request_id,
        "from_status": from_status,
        "to_status": to_status,
    })


def _require_laboratory(workflow: models.LaboratoryWorkflow, current_user: models.User) -> None:
    if workflow.laboratory_id != current_user.id:
        raise HTTPException(status_code=403, detail="This request is assigned to another laboratory")


def _load_request(db: Session, workflow: models.LaboratoryWorkflow) -> models.FHIRResource:
    request = db.query(models.FHIRResource).filter(
        models.FHIRResource.id == workflow.service_request_id,
        models.FHIRResource.resource_type == "ServiceRequest",
    ).first()
    if request is None:
        raise HTTPException(status_code=404, detail="ServiceRequest not found")
    return request


@router.get("/Patient/{patient_id}")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    allowed = (
        current_user.id == patient_id
        or (
            current_user.role == "doctor"
            and _has_active_consent(db, patient_id, current_user.id, "Patient")
        )
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="No active consent to view this patient")

    resource = db.query(models.FHIRResource).filter(
        models.FHIRResource.resource_type == "Patient",
        models.FHIRResource.owner_id == patient_id,
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Patient resource not found")

    audit_logger.log_event(db, current_user.id, "DATA_ACCESSED", {
        "resource_type": "Patient",
        "patient_id": patient_id,
        "resource_id": resource.fhir_id,
        "purpose": "Patient profile access",
    })
    return authoritative_resource("Patient", resource.fhir_id, resource.resource_data)


@router.get("/laboratories")
def list_laboratories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    laboratories = db.query(models.User).filter(
        models.User.role.in_(("lab", "lab_supervisor")),
    ).order_by(models.User.full_name.asc()).all()
    return [{"id": lab.id, "name": lab.full_name, "email": lab.email} for lab in laboratories]


@router.get("/physicians")
def list_physicians(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("patient")),
):
    physicians = db.query(models.User).filter(
        models.User.role == "doctor",
    ).order_by(models.User.full_name.asc()).all()
    return [{"id": physician.id, "name": physician.full_name, "email": physician.email} for physician in physicians]


@router.get("/patients/accessible")
def list_accessible_patients(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    now = datetime.utcnow()
    consents = db.query(models.Consent).filter(
        models.Consent.grantee_id == current_user.id,
        models.Consent.revoked_at.is_(None),
        models.Consent.expires_at > now,
    ).all()
    patient_ids = sorted({
        consent.patient_id for consent in consents if "Patient" in consent.resource_types
    })
    patients = db.query(models.User).filter(models.User.id.in_(patient_ids)).all() if patient_ids else []
    result = []
    for patient in patients:
        matching = [
            consent for consent in consents
            if consent.patient_id == patient.id and "Patient" in consent.resource_types
        ]
        latest = max(matching, key=lambda consent: consent.expires_at)
        result.append({
            "id": patient.id,
            "full_name": patient.full_name,
            "email": patient.email,
            "consent_expires_at": latest.expires_at,
            "resource_types": sorted({kind for grant in matching for kind in grant.resource_types}),
        })
    return result


@router.post("/ServiceRequest")
def create_service_request(
    payload: schemas.ServiceRequestCreate,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    patient = db.query(models.User).filter(
        models.User.email == payload.patient_email,
        models.User.role == "patient",
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not _has_active_consent(db, patient.id, current_user.id, "ServiceRequest"):
        raise HTTPException(status_code=403, detail="This patient has not granted you ServiceRequest access")

    laboratory = db.query(models.User).filter(
        models.User.email == payload.lab_email,
        models.User.role.in_(("lab", "lab_supervisor")),
    ).first()
    if not laboratory:
        raise HTTPException(status_code=404, detail="Laboratory not found")

    request_fingerprint = hashlib.sha256(json.dumps({
        "patient_id": patient.id,
        "laboratory_id": laboratory.id,
        "test_code": payload.test_code,
        "test_display": payload.test_display,
        "note": payload.note,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    existing_key = db.query(models.IdempotencyRecord).filter(
        models.IdempotencyRecord.actor_id == current_user.id,
        models.IdempotencyRecord.idempotency_key == idempotency_key,
    ).first()
    if existing_key:
        if existing_key.request_fingerprint != request_fingerprint:
            raise HTTPException(status_code=409, detail="Idempotency-Key was already used for a different request")
        existing_request = db.query(models.FHIRResource).filter(
            models.FHIRResource.id == existing_key.service_request_id,
        ).first()
        existing_workflow = _get_workflow(db, existing_key.service_request_id)
        if existing_request is None:
            raise HTTPException(status_code=409, detail="Original request for this Idempotency-Key is unavailable")
        return {
            "id": existing_request.id,
            "resource": authoritative_resource(
                "ServiceRequest", existing_request.fhir_id, existing_request.resource_data
            ),
            "workflow_status": existing_workflow.status,
        }

    fhir_id = str(uuid.uuid4())
    resource_data = fhir_builder.build_service_request(
        fhir_id, patient.id, current_user.id, payload.test_code, payload.test_display, payload.note
    )
    resource_data["performer"] = [{"reference": f"Organization/{laboratory.fhir_resource_id or laboratory.id}"}]
    resource_data = persist_resource(resource_data)
    record = models.FHIRResource(
        resource_type="ServiceRequest",
        fhir_id=fhir_id,
        resource_data=resource_data,
        owner_id=patient.id,
        created_by=current_user.id,
    )
    db.add(record)
    db.flush()
    workflow = models.LaboratoryWorkflow(
        service_request_id=record.id,
        patient_id=patient.id,
        physician_id=current_user.id,
        laboratory_id=laboratory.id,
        status="REQUESTED",
    )
    db.add(workflow)
    db.flush()
    db.add(models.WorkflowTransition(
        workflow_id=workflow.id,
        actor_id=current_user.id,
        from_status="",
        to_status="REQUESTED",
        note="Request created",
    ))
    db.add(models.IdempotencyRecord(
        actor_id=current_user.id,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        service_request_id=record.id,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_key = db.query(models.IdempotencyRecord).filter(
            models.IdempotencyRecord.actor_id == current_user.id,
            models.IdempotencyRecord.idempotency_key == idempotency_key,
        ).first()
        if existing_key and existing_key.request_fingerprint == request_fingerprint:
            existing_request = db.query(models.FHIRResource).filter(
                models.FHIRResource.id == existing_key.service_request_id,
            ).first()
            existing_workflow = _get_workflow(db, existing_key.service_request_id)
            if existing_request:
                return {
                    "id": existing_request.id,
                    "resource": authoritative_resource(
                        "ServiceRequest", existing_request.fhir_id, existing_request.resource_data
                    ),
                    "workflow_status": existing_workflow.status,
                }
        raise
    db.refresh(record)
    audit_logger.log_event(db, current_user.id, "SERVICE_REQUEST_CREATED", {
        "patient_id": patient.id,
        "fhir_id": fhir_id,
        "laboratory_id": laboratory.id,
    })
    return {"id": record.id, "resource": resource_data, "workflow_status": workflow.status}


@router.get("/ServiceRequest")
def list_service_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.LaboratoryWorkflow)
    if current_user.role == "doctor":
        query = query.filter(
            models.LaboratoryWorkflow.physician_id == current_user.id,
            models.LaboratoryWorkflow.patient_id.in_(
                _consented_patient_ids(db, current_user.id, "ServiceRequest")
            ),
        )
    elif current_user.role == "patient":
        query = query.filter(models.LaboratoryWorkflow.patient_id == current_user.id)
    elif current_user.role in ("lab", "lab_supervisor"):
        query = query.filter(models.LaboratoryWorkflow.laboratory_id == current_user.id)
    elif current_user.role == "lab_technician":
        query = query.filter(models.LaboratoryWorkflow.technician_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Role cannot access laboratory requests")

    workflows = query.order_by(models.LaboratoryWorkflow.created_at.desc()).limit(200).all()
    results = []
    audit_events = []
    for workflow in workflows:
        request = _load_request(db, workflow)
        audit_events.append((current_user.id, "DATA_ACCESSED", {
            "resource_type": "ServiceRequest",
            "patient_id": workflow.patient_id,
            "resource_id": request.fhir_id,
            "purpose": "Laboratory workflow access" if current_user.role.startswith("lab") else "Care coordination",
        }))
        results.append({
            "id": request.id,
            "resource": authoritative_resource("ServiceRequest", request.fhir_id, request.resource_data),
            "created_at": request.created_at,
            "workflow_status": workflow.status,
            "technician_id": workflow.technician_id,
            "specimen_id": workflow.specimen_fhir_id,
            "report_id": workflow.report_fhir_id,
        })
    audit_logger.log_events(db, audit_events)
    return results


@router.post("/ServiceRequest/{service_request_id}/accept")
def accept_service_request(
    service_request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab", "lab_supervisor")),
):
    workflow = _get_workflow(db, service_request_id)
    _require_laboratory(workflow, current_user)
    _require_state(workflow, "REQUESTED")
    _transition(db, workflow, current_user.id, "ACCEPTED")
    return {"status": workflow.status}


@router.post("/ServiceRequest/{service_request_id}/assign")
def assign_technician(
    service_request_id: str,
    payload: schemas.TechnicianAssignment,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab", "lab_supervisor")),
):
    workflow = _get_workflow(db, service_request_id)
    _require_laboratory(workflow, current_user)
    _require_state(workflow, "ACCEPTED")
    technician = db.query(models.User).filter(
        models.User.email == payload.technician_email,
        models.User.role == "lab_technician",
    ).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Laboratory technician not found")
    membership = db.query(models.LaboratoryMembership).filter(
        models.LaboratoryMembership.laboratory_id == current_user.id,
        models.LaboratoryMembership.technician_id == technician.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Technician is not a member of this laboratory")
    workflow.technician_id = technician.id
    _transition(db, workflow, current_user.id, "ASSIGNED")
    return {"status": workflow.status, "technician_id": technician.id}


@router.post("/ServiceRequest/{service_request_id}/specimen")
def register_specimen(
    service_request_id: str,
    payload: schemas.SpecimenCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab_technician")),
):
    workflow = _get_workflow(db, service_request_id)
    if workflow.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")
    _require_state(workflow, "ASSIGNED")
    request = _load_request(db, workflow)
    specimen_id = str(uuid.uuid4())
    specimen_data = fhir_builder.build_specimen(
        specimen_id,
        workflow.patient_id,
        request.fhir_id,
        payload.type_code,
        payload.type_display,
    )
    specimen_data = persist_resource(specimen_data)
    db.add(models.FHIRResource(
        resource_type="Specimen",
        fhir_id=specimen_id,
        resource_data=specimen_data,
        owner_id=workflow.patient_id,
        created_by=current_user.id,
    ))
    workflow.specimen_fhir_id = specimen_id
    db.commit()
    _transition(db, workflow, current_user.id, "SPECIMEN_REGISTERED")
    return {"specimen": specimen_data, "status": workflow.status}


@router.post("/ServiceRequest/{service_request_id}/processing")
def start_processing(
    service_request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab_technician")),
):
    workflow = _get_workflow(db, service_request_id)
    if workflow.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")
    _require_state(workflow, "SPECIMEN_REGISTERED")
    _transition(db, workflow, current_user.id, "PROCESSING")
    return {"status": workflow.status}


@router.post("/DiagnosticReport")
def submit_results(
    payload: schemas.DiagnosticReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab_technician")),
):
    workflow = _get_workflow(db, payload.service_request_id)
    if workflow.technician_id != current_user.id:
        raise HTTPException(status_code=403, detail="This request is not assigned to you")
    _require_state(workflow, "PROCESSING")
    request = _load_request(db, workflow)

    observation_ids = []
    for item in payload.observations:
        observation_id = str(uuid.uuid4())
        observation_data = fhir_builder.build_observation(
            observation_id,
            workflow.patient_id,
            request.fhir_id,
            item.code,
            item.display,
            item.value,
            item.unit,
        )
        observation_data = persist_resource(observation_data)
        db.add(models.FHIRResource(
            resource_type="Observation",
            fhir_id=observation_id,
            resource_data=observation_data,
            owner_id=workflow.patient_id,
            created_by=current_user.id,
        ))
        observation_ids.append(observation_id)

    report_id = str(uuid.uuid4())
    report_data = fhir_builder.build_diagnostic_report(
        report_id,
        workflow.patient_id,
        request.fhir_id,
        observation_ids,
        workflow.laboratory_id,
        payload.conclusion,
        status="preliminary",
    )
    if workflow.specimen_fhir_id:
        report_data["specimen"] = [{"reference": f"Specimen/{workflow.specimen_fhir_id}"}]
    report_data = persist_resource(report_data)
    db.add(models.FHIRResource(
        resource_type="DiagnosticReport",
        fhir_id=report_id,
        resource_data=report_data,
        owner_id=workflow.patient_id,
        created_by=current_user.id,
    ))
    workflow.report_fhir_id = report_id
    db.commit()
    _transition(db, workflow, current_user.id, "RESULTS_SUBMITTED")
    return {"id": report_id, "resource": report_data, "workflow_status": workflow.status}


@router.post("/ServiceRequest/{service_request_id}/finalize")
def finalize_report(
    service_request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("lab", "lab_supervisor")),
):
    workflow = _get_workflow(db, service_request_id)
    _require_laboratory(workflow, current_user)
    _require_state(workflow, "RESULTS_SUBMITTED")
    report = db.query(models.FHIRResource).filter(
        models.FHIRResource.resource_type == "DiagnosticReport",
        models.FHIRResource.fhir_id == workflow.report_fhir_id,
        models.FHIRResource.owner_id == workflow.patient_id,
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Submitted report not found")
    report_data = dict(authoritative_resource(
        "DiagnosticReport", report.fhir_id, report.resource_data
    ))
    report_data["status"] = "final"
    report_data["issued"] = fhir_builder.now_iso()
    report_data = persist_resource(report_data)
    report.resource_data = report_data
    workflow.reviewer_id = current_user.id
    db.commit()
    _transition(db, workflow, current_user.id, "FINALIZED")
    audit_logger.log_event(db, current_user.id, "DIAGNOSTIC_REPORT_FINALIZED", {
        "patient_id": workflow.patient_id,
        "report_id": report.fhir_id,
        "service_request_id": service_request_id,
    })
    return {"status": workflow.status, "resource": report_data}


@router.post("/ServiceRequest/{service_request_id}/physician-review")
def physician_review(
    service_request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("doctor")),
):
    workflow = _get_workflow(db, service_request_id)
    if workflow.physician_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the requesting physician can review this report")
    _require_state(workflow, "FINALIZED")
    if not _has_active_consent(db, workflow.patient_id, current_user.id, "DiagnosticReport"):
        raise HTTPException(status_code=403, detail="Active DiagnosticReport consent is required")
    _transition(db, workflow, current_user.id, "PHYSICIAN_REVIEWED")
    audit_logger.log_event(db, current_user.id, "CLINICAL_REVIEW_RECORDED", {
        "patient_id": workflow.patient_id,
        "service_request_id": service_request_id,
        "report_id": workflow.report_fhir_id,
    })
    return {"status": workflow.status}


@router.get("/DiagnosticReport")
def list_diagnostic_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.FHIRResource).join(
        models.LaboratoryWorkflow,
        models.LaboratoryWorkflow.report_fhir_id == models.FHIRResource.fhir_id,
    ).filter(
        models.FHIRResource.resource_type == "DiagnosticReport",
        models.LaboratoryWorkflow.status.in_(("FINALIZED", "PHYSICIAN_REVIEWED")),
    )
    if current_user.role == "patient":
        query = query.filter(models.FHIRResource.owner_id == current_user.id)
    elif current_user.role == "doctor":
        query = query.filter(
            models.LaboratoryWorkflow.physician_id == current_user.id,
            models.LaboratoryWorkflow.patient_id.in_(
                _consented_patient_ids(db, current_user.id, "DiagnosticReport")
            ),
        )
    elif current_user.role in ("lab", "lab_supervisor"):
        query = query.filter(models.LaboratoryWorkflow.laboratory_id == current_user.id)
    elif current_user.role == "lab_technician":
        query = query.filter(models.LaboratoryWorkflow.technician_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Role cannot access diagnostic reports")

    results = query.order_by(models.FHIRResource.created_at.desc()).limit(200).all()
    audit_logger.log_events(db, [
        (current_user.id, "DATA_ACCESSED", {
            "resource_type": "DiagnosticReport",
            "patient_id": result.owner_id,
            "resource_id": result.fhir_id,
            "purpose": "Clinical review" if current_user.role == "doctor" else "Laboratory workflow access",
        })
        for result in results
    ])
    return [{
        "id": result.id,
        "resource": authoritative_resource("DiagnosticReport", result.fhir_id, result.resource_data),
        "created_at": result.created_at,
    } for result in results]
