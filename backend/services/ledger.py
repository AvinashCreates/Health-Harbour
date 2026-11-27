import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session

import models

LEDGER_EVENT_TYPES = {
    "CONSENT_GRANTED",
    "CONSENT_REVOKED",
    "SERVICE_REQUEST_CREATED",
    "SPECIMEN_REGISTERED",
    "DIAGNOSTIC_REPORT_FINALIZED",
    "CLINICAL_REVIEW_RECORDED",
    "LAB_REPORT_FINALIZED",
    "PHYSICIAN_REVIEW_RECORDED",
    "DATA_ACCESSED",
    "DOCUMENT_UPLOADED",
    "DOCUMENT_DELETED",
    "DOCUMENT_ACCESS_DENIED",
    "DOCUMENT_UPLOAD_REJECTED",
    "CROSS_HOSPITAL_EXCHANGE_REQUESTED",
    "CROSS_HOSPITAL_CONSENT_GRANTED",
    "CROSS_HOSPITAL_CONSENT_REJECTED",
    "CROSS_HOSPITAL_CONSENT_REVOKED",
    "CROSS_ORGANIZATION_DOCUMENT_IMPORTED",
}


def ledger_enabled() -> bool:
    value = os.getenv("FABRIC_ENABLED", "false").strip().lower()
    if value not in {"true", "false"}:
        raise RuntimeError("FABRIC_ENABLED must be either 'true' or 'false'")
    if value == "false":
        return False
    gateway_url = os.getenv("FABRIC_GATEWAY_URL", "")
    gateway_token = os.getenv("FABRIC_GATEWAY_TOKEN", "")
    pseudonym_key = os.getenv("FABRIC_PSEUDONYM_KEY", "")
    parsed_gateway_url = urlparse(gateway_url)
    if parsed_gateway_url.scheme not in {"http", "https"} or not parsed_gateway_url.netloc:
        raise RuntimeError("Fabric is enabled but FABRIC_GATEWAY_URL is invalid")
    if len(gateway_token.encode("utf-8")) < 32:
        raise RuntimeError("FABRIC_GATEWAY_TOKEN must contain at least 32 bytes when Fabric is enabled")
    if len(pseudonym_key.encode("utf-8")) < 32:
        raise RuntimeError("FABRIC_PSEUDONYM_KEY must contain at least 32 bytes when Fabric is enabled")
    return True


def _pseudonym(value: str | None) -> str | None:
    key = os.getenv("FABRIC_PSEUDONYM_KEY", "")
    if len(key.encode("utf-8")) < 32:
        raise RuntimeError("FABRIC_PSEUDONYM_KEY must contain at least 32 bytes when Fabric is enabled")
    if value is None:
        return None
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def queue_ledger_event(
    db: Session,
    actor_id: str | None,
    event_type: str,
    audit_payload: dict,
    created_at: datetime,
) -> None:
    if not ledger_enabled() or event_type not in LEDGER_EVENT_TYPES:
        return
    if not os.getenv("FABRIC_GATEWAY_URL") or not os.getenv("FABRIC_GATEWAY_TOKEN"):
        raise RuntimeError("Fabric is enabled but FABRIC_GATEWAY_URL or FABRIC_GATEWAY_TOKEN is missing")

    subject_id = next(
        (audit_payload[key] for key in ("patient_id", "subject_id", "owner_id") if audit_payload.get(key)),
        actor_id if event_type in {"CONSENT_GRANTED", "CONSENT_REVOKED"} else None,
    )
    resource_id = next(
        (audit_payload[key] for key in (
            "resource_id", "service_request_id", "consent_id", "fhir_id", "report_id"
        ) if audit_payload.get(key)),
        None,
    )
    event_id = models.gen_uuid()
    canonical_payload = json.dumps(audit_payload, sort_keys=True, separators=(",", ":"), default=str)
    payload_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
    event_payload = {
        "eventId": event_id,
        "eventType": event_type,
        "actorRef": _pseudonym(actor_id),
        "subjectRef": _pseudonym(subject_id),
        "resourceRef": _pseudonym(str(resource_id)) if resource_id is not None else None,
        "resourceType": audit_payload.get("resource_type"),
        "occurredAt": created_at.isoformat() + "Z",
        "payloadHash": payload_hash,
    }
    db.add(models.LedgerOutbox(
        id=event_id,
        event_type=event_type,
        event_payload=event_payload,
        payload_hash=payload_hash,
        status="PENDING",
    ))


def process_pending_events(batch_size: int = 10) -> int:
    import httpx

    if not ledger_enabled():
        return 0
    from database import SessionLocal

    completed = 0
    db: Session = SessionLocal()
    try:
        events = (
            db.query(models.LedgerOutbox)
            .filter(
                models.LedgerOutbox.status == "PENDING",
                models.LedgerOutbox.next_attempt_at <= datetime.utcnow(),
            )
            .order_by(models.LedgerOutbox.created_at.asc())
            .limit(batch_size)
            .all()
        )
        for event in events:
            event.attempt_count += 1
            db.commit()
            try:
                response = httpx.post(
                    os.environ["FABRIC_GATEWAY_URL"].rstrip("/") + "/events",
                    json=event.event_payload,
                    headers={"Authorization": "Bearer " + os.environ["FABRIC_GATEWAY_TOKEN"]},
                    timeout=httpx.Timeout(30.0, connect=3.0),
                )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise RuntimeError("Fabric Gateway returned an invalid commit response")
                transaction_id = body.get("transactionId")
                if not isinstance(transaction_id, str) or not transaction_id:
                    raise RuntimeError("Fabric Gateway did not confirm a transaction ID")
                event.transaction_id = transaction_id
                event.status = "COMMITTED"
                event.committed_at = datetime.utcnow()
                event.last_error = None
                completed += 1
            except (httpx.HTTPError, ValueError, RuntimeError, KeyError) as exc:
                event.last_error = str(exc)[:500]
                if event.attempt_count >= 8:
                    event.status = "FAILED"
                else:
                    event.next_attempt_at = datetime.utcnow() + timedelta(
                        seconds=min(2 ** event.attempt_count, 300)
                    )
            db.commit()
        return completed
    finally:
        db.close()
