import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models
from services.fhir_server import (
    FHIRIntegrationError,
    fhir_mode,
    persist_resource,
    retrieve_resource,
)

MAX_ATTEMPTS = 8


def _hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def queue_fhir_resource(db: Session, resource_type: str, resource_id: str, payload: dict) -> models.FHIRSyncOutbox:
    payload_hash = _hash(payload)
    event = db.query(models.FHIRSyncOutbox).filter(
        models.FHIRSyncOutbox.resource_type == resource_type,
        models.FHIRSyncOutbox.resource_id == resource_id,
    ).with_for_update().first()
    if event is None:
        event = models.FHIRSyncOutbox(
            resource_type=resource_type,
            resource_id=resource_id,
            resource_payload=payload,
            payload_hash=payload_hash,
            status="PENDING",
            attempt_count=0,
            next_attempt_at=datetime.utcnow(),
        )
        db.add(event)
        db.flush()
        return event
    if event.payload_hash != payload_hash:
        event.resource_payload = payload
        event.payload_hash = payload_hash
        event.status = "PENDING"
        event.attempt_count = 0
        event.next_attempt_at = datetime.utcnow()
        event.last_error = None
        event.last_error_category = None
    elif event.status in {"FAILED", "PERMANENT_FAILED"}:
        event.status = "PENDING"
        event.next_attempt_at = datetime.utcnow()
    db.flush()
    return event


def _store_local_mirror(db: Session, event: models.FHIRSyncOutbox, payload: dict) -> None:
    mirror = db.query(models.FHIRResource).filter(
        models.FHIRResource.resource_type == event.resource_type,
        models.FHIRResource.fhir_id == event.resource_id,
    ).first()
    if mirror is None:
        mirror = models.FHIRResource(
            resource_type=event.resource_type,
            fhir_id=event.resource_id,
            resource_data=payload,
            owner_id=None,
            created_by=None,
        )
        db.add(mirror)
    else:
        mirror.resource_data = payload


def process_fhir_sync(db: Session | None = None, batch_size: int = 20) -> dict:
    owns_session = db is None
    if db is None:
        from database import SessionLocal
        db = SessionLocal()
    try:
        now = datetime.utcnow()
        events = db.query(models.FHIRSyncOutbox).filter(
            models.FHIRSyncOutbox.status.in_({"PENDING", "FAILED"}),
            models.FHIRSyncOutbox.next_attempt_at <= now,
        ).order_by(models.FHIRSyncOutbox.created_at.asc()).limit(batch_size).all()
        synced = 0
        failed = 0
        permanent = 0
        for event in events:
            event.attempt_count += 1
            try:
                payload = dict(event.resource_payload)
                if fhir_mode() == "local":
                    persisted = payload
                else:
                    persisted = persist_resource(payload)
                _store_local_mirror(db, event, persisted)
                event.status = "SYNCED"
                event.last_error = None
                event.last_error_category = None
                event.last_synced_at = datetime.utcnow()
                synced += 1
            except FHIRIntegrationError as exc:
                permanent_statuses = {400, 401, 403, 404, 409, 422}
                upstream_status = getattr(exc, "upstream_status_code", None)
                category = (
                    "permanent"
                    if upstream_status in permanent_statuses or exc.status_code in permanent_statuses
                    else "retryable"
                )
                event.last_error_category = category
                event.last_error = str(exc)[:500]
                if category == "permanent" or event.attempt_count >= MAX_ATTEMPTS:
                    event.status = "PERMANENT_FAILED" if category == "permanent" else "FAILED"
                    permanent += 1 if event.status == "PERMANENT_FAILED" else 0
                else:
                    event.status = "FAILED"
                    event.next_attempt_at = datetime.utcnow() + timedelta(seconds=min(2 ** event.attempt_count, 300))
                failed += 1
            except Exception as exc:
                event.last_error_category = "retryable"
                event.last_error = type(exc).__name__[:500]
                if event.attempt_count >= MAX_ATTEMPTS:
                    event.status = "FAILED"
                else:
                    event.status = "FAILED"
                    event.next_attempt_at = datetime.utcnow() + timedelta(seconds=min(2 ** event.attempt_count, 300))
                failed += 1
            db.commit()
        return {"synced": synced, "failed": failed, "permanent_failed": permanent, "processed": len(events)}
    finally:
        if owns_session:
            db.close()


def reconcile_fhir(db: Session) -> dict:
    totals = {
        "pending": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "PENDING").count(),
        "synced": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "SYNCED").count(),
        "failed": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "FAILED").count(),
        "permanent_failed": db.query(models.FHIRSyncOutbox).filter(models.FHIRSyncOutbox.status == "PERMANENT_FAILED").count(),
    }
    discrepancies = []
    if fhir_mode() == "hapi":
        events = db.query(models.FHIRSyncOutbox).all()
        for event in events:
            try:
                remote = retrieve_resource(event.resource_type, event.resource_id)
            except FHIRIntegrationError:
                discrepancies.append({"resource_type": event.resource_type, "resource_id": event.resource_id, "issue": "HAPI_UNAVAILABLE_OR_UNCHECKABLE"})
                continue
            if remote is None:
                discrepancies.append({"resource_type": event.resource_type, "resource_id": event.resource_id, "issue": "FHIR_RESOURCE_MISSING"})
            elif event.payload_hash != _hash(remote):
                discrepancies.append({"resource_type": event.resource_type, "resource_id": event.resource_id, "issue": "FHIR_RESOURCE_DIFFERS"})
    totals["discrepancies"] = discrepancies
    return totals
