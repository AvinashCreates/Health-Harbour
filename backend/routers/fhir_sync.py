from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
from database import get_db
from deps import require_roles
from services.fhir_sync import process_fhir_sync, reconcile_fhir

router = APIRouter(prefix="/api/v1/admin/fhir", tags=["FHIR interoperability"])


@router.get("/sync/status")
def fhir_sync_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    return {
        "pending": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "PENDING").count(),
        "synced": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "SYNCED").count(),
        "failed": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "FAILED").count(),
        "permanent_failed": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "PERMANENT_FAILED").count(),
    }


@router.post("/sync/process")
def fhir_sync_process(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    return process_fhir_sync(db, limit)


@router.post("/sync/reconcile")
def fhir_sync_reconcile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    return reconcile_fhir(db)
