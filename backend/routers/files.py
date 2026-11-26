import base64
import hashlib
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
from database import get_db
from deps import get_current_user
from services import audit_logger, fhir_builder
from services.consent_access import consented_patient_ids, has_active_consent
from services.fhir_server import authoritative_resource, fhir_mode, persist_resource

router = APIRouter(prefix="/files", tags=["clinical files"])
logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt", ".csv"}
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
    ".csv": "text/csv",
}
CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,39}$")


def _storage_root() -> Path:
    configured = os.getenv("FILE_STORAGE_PATH", "uploads")
    path = Path(configured)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path.resolve()


def _active_document_consent(db: Session, patient_id: str, physician_id: str) -> bool:
    return has_active_consent(db, patient_id, physician_id, "Document")


def _workflow_for_file(
    db: Session,
    file_record: models.ClinicalFile,
) -> models.LaboratoryWorkflow | None:
    if not file_record.service_request_id:
        return None
    return db.query(models.LaboratoryWorkflow).filter(
        models.LaboratoryWorkflow.service_request_id == file_record.service_request_id,
        models.LaboratoryWorkflow.patient_id == file_record.patient_id,
    ).first()


def _can_access(
    db: Session,
    file_record: models.ClinicalFile,
    user: models.User,
) -> bool:
    if file_record.deleted_at is not None:
        return False
    if user.role == "patient":
        return user.id == file_record.patient_id
    if user.role == "doctor":
        return _active_document_consent(db, file_record.patient_id, user.id)
    workflow = _workflow_for_file(db, file_record)
    if workflow is None:
        return False
    if user.role in {"lab", "lab_supervisor"}:
        return workflow.laboratory_id == user.id
    if user.role == "lab_technician":
        return workflow.technician_id == user.id
    return False


def _metadata(
    file_record: models.ClinicalFile,
    db: Session,
    user: models.User,
    workflow: models.LaboratoryWorkflow | None = None,
    users_by_id: dict[str, models.User] | None = None,
) -> dict:
    if users_by_id is None:
        patient = db.query(models.User).filter(models.User.id == file_record.patient_id).first()
        uploader = db.query(models.User).filter(models.User.id == file_record.uploaded_by_id).first()
    else:
        patient = users_by_id.get(file_record.patient_id)
        uploader = users_by_id.get(file_record.uploaded_by_id)
    return {
        "id": file_record.id,
        "patient_id": file_record.patient_id,
        "patient_name": patient.full_name if patient else "Patient",
        "filename": file_record.filename,
        "media_type": file_record.media_type,
        "size_bytes": file_record.size_bytes,
        "category": file_record.category,
        "uploaded_by_id": file_record.uploaded_by_id,
        "uploaded_by_name": uploader.full_name if uploader else "Care team",
        "uploaded_by_role": uploader.role if uploader else "unknown",
        "service_request_id": file_record.service_request_id,
        "workflow_status": workflow.status if workflow else None,
        "created_at": file_record.created_at,
        "can_delete": user.role == "patient" and file_record.patient_id == user.id,
    }


def _accessible_file_or_404(
    db: Session,
    file_id: str,
    user: models.User,
) -> models.ClinicalFile:
    file_record = db.query(models.ClinicalFile).filter(
        models.ClinicalFile.id == file_id,
        models.ClinicalFile.deleted_at.is_(None),
    ).first()
    if file_record is None or not _can_access(db, file_record, user):
        raise HTTPException(status_code=404, detail="File not found")
    return file_record


def _validate_file_content(filename: str, content: bytes) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="File type not supported. Upload PDF, JPG, PNG, TXT, or CSV files.",
        )
    if not content:
        raise HTTPException(status_code=422, detail="The selected file is empty")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The file content does not match a PDF document")
    if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=415, detail="The file content does not match a JPEG image")
    if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail="The file content does not match a PNG image")
    if extension in {".txt", ".csv"}:
        if b"\x00" in content:
            raise HTTPException(status_code=415, detail="Text files cannot contain binary data")
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="Text files must use UTF-8 encoding") from exc
    return extension, MEDIA_TYPES[extension]


def _safe_filename(filename: str | None) -> str:
    candidate = (filename or "clinical-file").replace("\\", "/").rsplit("/", 1)[-1]
    candidate = "".join(
        char for char in candidate
        if char.isprintable() and char not in {'"', "'", "\r", "\n"}
    ).strip()
    if not candidate or len(candidate) > 180:
        raise HTTPException(status_code=422, detail="Filename must be between 1 and 180 characters")
    return candidate


def _build_document_reference(
    file_record: models.ClinicalFile,
    patient: models.User,
    uploader: models.User,
    workflow: models.LaboratoryWorkflow | None,
    service_request: models.FHIRResource | None,
) -> dict:
    public_api_url = os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    resource = {
        "resourceType": "DocumentReference",
        "id": file_record.id,
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "34108-1",
                "display": "Outpatient Note",
            }]
        },
        "category": [{
            "coding": [{
                "system": "urn:healthharbor:document-category",
                "code": file_record.category,
                "display": file_record.category.replace("-", " ").title(),
            }]
        }],
        "subject": {"reference": f"Patient/{patient.fhir_resource_id or patient.id}"},
        "date": file_record.created_at.isoformat() + "Z",
        "content": [{
            "attachment": {
                "contentType": file_record.media_type,
                "url": f"{public_api_url}/files/{file_record.id}/download",
                "title": file_record.filename,
                "size": file_record.size_bytes,
                "hash": base64.b64encode(bytes.fromhex(file_record.sha256)).decode("ascii"),
            }
        }],
    }
    if uploader.role == "patient":
        resource["author"] = [{"reference": f"Patient/{uploader.fhir_resource_id or uploader.id}"}]
    elif uploader.role == "doctor" and uploader.fhir_resource_id:
        resource["author"] = [{"reference": f"Practitioner/{uploader.fhir_resource_id}"}]
    elif uploader.role in {"lab", "lab_supervisor"} and uploader.fhir_resource_id:
        resource["author"] = [{"reference": f"Organization/{uploader.fhir_resource_id}"}]
    if workflow and service_request:
        resource["context"] = {
            "related": [{"reference": f"ServiceRequest/{service_request.fhir_id}"}],
        }
    return resource


@router.get("")
def list_files(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.ClinicalFile).filter(models.ClinicalFile.deleted_at.is_(None))
    lab_workflow_scope = None
    if current_user.role == "patient":
        query = query.filter(models.ClinicalFile.patient_id == current_user.id)
    elif current_user.role == "doctor":
        patient_ids = consented_patient_ids(db, current_user.id, "Document")
        if not patient_ids:
            return []
        query = query.filter(models.ClinicalFile.patient_id.in_(patient_ids))
    elif current_user.role in {"lab", "lab_supervisor", "lab_technician"}:
        lab_workflow_scope = db.query(models.LaboratoryWorkflow).filter(
            models.LaboratoryWorkflow.technician_id == current_user.id
            if current_user.role == "lab_technician"
            else models.LaboratoryWorkflow.laboratory_id == current_user.id
        )
        query = query.filter(
            models.ClinicalFile.service_request_id.in_(
                lab_workflow_scope.with_entities(models.LaboratoryWorkflow.service_request_id)
            )
        )
    else:
        raise HTTPException(status_code=403, detail="This account cannot view clinical files")

    files = query.order_by(models.ClinicalFile.created_at.desc()).limit(250).all()
    if not files:
        return []

    user_ids = {
        user_id
        for file_record in files
        for user_id in (file_record.patient_id, file_record.uploaded_by_id)
    }
    users_by_id = {
        user.id: user
        for user in db.query(models.User).filter(models.User.id.in_(user_ids)).all()
    }

    request_ids = {
        file_record.service_request_id
        for file_record in files
        if file_record.service_request_id
    }
    workflows_by_file: dict[tuple[str, str], models.LaboratoryWorkflow] = {}
    if request_ids:
        workflows = db.query(models.LaboratoryWorkflow).filter(
            models.LaboratoryWorkflow.service_request_id.in_(request_ids)
        )
        if lab_workflow_scope is not None:
            workflows = workflows.filter(
                models.LaboratoryWorkflow.technician_id == current_user.id
                if current_user.role == "lab_technician"
                else models.LaboratoryWorkflow.laboratory_id == current_user.id
            )
        workflows_by_file = {
            (workflow.service_request_id, workflow.patient_id): workflow
            for workflow in workflows.all()
        }

    result = []
    for file_record in files:
        workflow = workflows_by_file.get(
            (file_record.service_request_id, file_record.patient_id)
        ) if file_record.service_request_id else None
        if lab_workflow_scope is not None and workflow is None:
            continue
        result.append(_metadata(
            file_record,
            db,
            current_user,
            workflow,
            users_by_id,
        ))
    return result


@router.get("/patients")
def list_document_patients(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only physicians can select patients for file uploads")
    patient_ids = consented_patient_ids(db, current_user.id, "Document")
    if not patient_ids:
        return []
    patients = db.query(models.User).filter(
        models.User.id.in_(patient_ids),
        models.User.role == "patient",
    ).order_by(models.User.full_name.asc()).all()
    return [{"id": patient.id, "full_name": patient.full_name, "email": patient.email} for patient in patients]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: Annotated[UploadFile, File()],
    patient_id: Annotated[str | None, Form()] = None,
    service_request_id: Annotated[str | None, Form()] = None,
    category: Annotated[str, Form()] = "clinical-record",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not CATEGORY_PATTERN.fullmatch(category):
        raise HTTPException(status_code=422, detail="Invalid file category")
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Administrators cannot upload clinical files")

    workflow = None
    request_resource = None
    if service_request_id:
        workflow = db.query(models.LaboratoryWorkflow).filter(
            models.LaboratoryWorkflow.service_request_id == service_request_id,
        ).first()
        if workflow is None:
            request_resource = db.query(models.FHIRResource).filter(
                models.FHIRResource.id == service_request_id,
                models.FHIRResource.resource_type == "ServiceRequest",
            ).first()
            if request_resource is not None:
                workflow = db.query(models.LaboratoryWorkflow).filter(
                    models.LaboratoryWorkflow.service_request_id == request_resource.id,
                ).first()
        if workflow is None:
            raise HTTPException(status_code=404, detail="Laboratory workflow not found")
        if request_resource is None:
            request_resource = db.query(models.FHIRResource).filter(
                models.FHIRResource.id == workflow.service_request_id,
                models.FHIRResource.resource_type == "ServiceRequest",
            ).first()
        patient_id = workflow.patient_id

    if current_user.role == "patient":
        patient_id = current_user.id
        if workflow and workflow.patient_id != current_user.id:
            raise HTTPException(status_code=404, detail="Laboratory workflow not found")
    elif current_user.role == "doctor":
        if not patient_id:
            raise HTTPException(status_code=422, detail="Select the patient for this file")
        if not _active_document_consent(db, patient_id, current_user.id):
            raise HTTPException(status_code=403, detail="Active Document consent is required to share files")
        if workflow and workflow.physician_id != current_user.id:
            raise HTTPException(status_code=403, detail="This request belongs to another physician")
    elif current_user.role in {"lab", "lab_supervisor"}:
        if workflow is None or workflow.laboratory_id != current_user.id:
            raise HTTPException(status_code=403, detail="Files must be attached to your laboratory's request")
    elif current_user.role == "lab_technician":
        if workflow is None or workflow.technician_id != current_user.id:
            raise HTTPException(status_code=403, detail="Files must be attached to your assigned request")
    else:
        raise HTTPException(status_code=403, detail="This account cannot upload clinical files")

    patient = db.query(models.User).filter(
        models.User.id == patient_id,
        models.User.role == "patient",
    ).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    original_filename = _safe_filename(file.filename)
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller")
    _, media_type = _validate_file_content(original_filename, content)
    file_id = str(uuid.uuid4())
    storage_key = f"{uuid.uuid4().hex}.blob"
    storage_root = _storage_root()
    storage_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    storage_path = storage_root / storage_key
    digest = hashlib.sha256(content).hexdigest()
    timestamp = datetime.utcnow()
    file_record = models.ClinicalFile(
        id=file_id,
        patient_id=patient.id,
        uploaded_by_id=current_user.id,
        service_request_id=workflow.service_request_id if workflow else None,
        filename=original_filename,
        storage_key=storage_key,
        media_type=media_type,
        category=category,
        size_bytes=len(content),
        sha256=digest,
        created_at=timestamp,
    )
    service_request = request_resource
    if workflow and service_request is None:
        service_request = db.query(models.FHIRResource).filter(
            models.FHIRResource.id == workflow.service_request_id,
            models.FHIRResource.resource_type == "ServiceRequest",
        ).first()
    document_reference = _build_document_reference(
        file_record, patient, current_user, workflow, service_request,
    )

    persisted_reference = None
    try:
        with storage_path.open("xb") as stored:
            stored.write(content)
        storage_path.chmod(0o600)
        persisted_reference = persist_resource(document_reference)
        db.add(file_record)
        db.add(models.FHIRResource(
            resource_type="DocumentReference",
            fhir_id=file_id,
            resource_data=persisted_reference,
            owner_id=patient.id,
            created_by=current_user.id,
        ))
        db.commit()
        db.refresh(file_record)
    except Exception:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        if persisted_reference is not None and fhir_mode() == "hapi":
            try:
                persist_resource({**persisted_reference, "status": "entered-in-error"})
            except Exception:
                logger.exception("Could not mark the FHIR DocumentReference after file upload rollback")
        raise

    audit_logger.log_event(db, current_user.id, "DOCUMENT_UPLOADED", {
        "patient_id": patient.id,
        "resource_id": file_id,
        "resource_type": "DocumentReference",
        "category": category,
        "size_bytes": len(content),
    })
    return _metadata(file_record, db, current_user, workflow)


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    file_record = _accessible_file_or_404(db, file_id, current_user)
    storage_path = _storage_root() / file_record.storage_key
    if not storage_path.is_file():
        raise HTTPException(status_code=410, detail="The file is no longer available")
    audit_logger.log_event(db, current_user.id, "DATA_ACCESSED", {
        "patient_id": file_record.patient_id,
        "resource_id": file_record.id,
        "resource_type": "DocumentReference",
        "purpose": "Clinical file download",
    })
    return FileResponse(
        storage_path,
        media_type=file_record.media_type,
        filename=file_record.filename,
        content_disposition_type="attachment",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(file_record.size_bytes),
        },
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    file_record = db.query(models.ClinicalFile).filter(
        models.ClinicalFile.id == file_id,
        models.ClinicalFile.deleted_at.is_(None),
    ).first()
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found")
    if current_user.role != "patient" or file_record.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the patient can remove this file")

    document_row = db.query(models.FHIRResource).filter(
        models.FHIRResource.resource_type == "DocumentReference",
        models.FHIRResource.fhir_id == file_record.id,
    ).first()
    if document_row is None:
        raise HTTPException(status_code=409, detail="File metadata is unavailable")
    previous_reference = dict(document_row.resource_data)
    if fhir_mode() == "hapi":
        previous_reference = authoritative_resource(
            "DocumentReference", file_record.id, previous_reference,
        )
    deleted_reference = {**previous_reference, "status": "entered-in-error"}
    storage_path = _storage_root() / file_record.storage_key
    tombstone_path = storage_path.with_name(f".{file_record.id}.deleting")
    if storage_path.exists():
        try:
            os.replace(storage_path, tombstone_path)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Unable to remove the stored file") from exc
    try:
        persisted_reference = persist_resource(deleted_reference)
    except Exception:
        if tombstone_path.exists():
            try:
                os.replace(tombstone_path, storage_path)
            except OSError:
                logger.exception("Could not restore file bytes after FHIR deletion failed")
        raise
    file_record.deleted_at = datetime.utcnow()
    document_row.resource_data = persisted_reference
    try:
        db.commit()
    except Exception:
        db.rollback()
        if tombstone_path.exists():
            try:
                os.replace(tombstone_path, storage_path)
            except OSError:
                logger.exception("Could not restore file bytes after database deletion failed")
        if fhir_mode() == "hapi":
            try:
                remote_reference = authoritative_resource(
                    "DocumentReference", file_record.id, previous_reference,
                )
                previous_status = previous_reference.get("status", "current")
                if isinstance(previous_status, str):
                    remote_reference["status"] = previous_status
                    persist_resource(remote_reference)
            except Exception:
                logger.exception("Could not restore the FHIR DocumentReference after file deletion rollback")
        raise
    try:
        audit_logger.log_event(db, current_user.id, "DOCUMENT_DELETED", {
            "patient_id": file_record.patient_id,
            "resource_id": file_record.id,
            "resource_type": "DocumentReference",
        })
    finally:
        tombstone_path.unlink(missing_ok=True)
    return {"status": "deleted", "id": file_id}
