from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from deps import require_roles
from services import audit_logger

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/log")
def get_audit_log(db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("admin"))):
    entries = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(200).all()
    return [
        {
            "id": e.id, "actor_id": e.actor_id, "event_type": e.event_type,
            "event_payload": e.event_payload, "prev_hash": e.prev_hash,
            "curr_hash": e.curr_hash, "created_at": e.created_at,
        }
        for e in entries
    ]


@router.get("/verify")
def verify_audit_chain(db: Session = Depends(get_db), current_user: models.User = Depends(require_roles("admin"))):
    ok, broken_at = audit_logger.verify_chain(db)
    return {"chain_valid": ok, "broken_at_id": broken_at}


@router.get("/ledger")
def get_ledger_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    events = db.query(models.LedgerOutbox).order_by(
        models.LedgerOutbox.created_at.desc()
    ).limit(200).all()
    return [{
        "id": event.id,
        "event_type": event.event_type,
        "payload_hash": event.payload_hash,
        "status": event.status,
        "transaction_id": event.transaction_id,
        "attempt_count": event.attempt_count,
        "last_error": event.last_error,
        "created_at": event.created_at,
        "committed_at": event.committed_at,
    } for event in events]
