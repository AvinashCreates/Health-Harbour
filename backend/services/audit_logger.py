"""Simulated permissioned-ledger layer.

This is NOT Hyperledger Fabric and does not claim to be: there is no
multi-peer consensus and no separate organizations each holding a copy.
What it does provide, honestly, is the specific property the abstract
asks the blockchain layer for -- tamper-evident provenance: every audit
entry's hash commits to the previous entry's hash plus its own content,
so editing any past row (e.g. an admin trying to quietly erase a
CONSENT_REVOKED event directly in the database) changes that row's
correct hash and breaks the chain for every entry after it. /audit/verify
recomputes the whole chain and reports exactly where it breaks, if it does.

Swapping this for real Hyperledger Fabric later would add decentralized
trust across separate organizations -- call that out as a future
enhancement rather than something already built.
"""

import hashlib
import json
import threading
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

import models
from services.ledger import queue_ledger_event

GENESIS_HASH = "0" * 64
_CHAIN_LOCK = threading.RLock()
_POSTGRES_CHAIN_LOCK_ID = 731942681


def _compute_hash(prev_hash: str, actor_id, event_type: str, payload: dict, timestamp_iso: str) -> str:
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{prev_hash}|{actor_id}|{event_type}|{payload_str}|{timestamp_iso}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def log_event(db: Session, actor_id, event_type: str, payload: dict) -> models.AuditLog:
    return log_events(db, [(actor_id, event_type, payload)])[0]


def log_events(db: Session, events: list[tuple[str | None, str, dict]]) -> list[models.AuditLog]:
    if not events:
        return []
    with _CHAIN_LOCK:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": _POSTGRES_CHAIN_LOCK_ID},
            )
        last = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).first()
        prev_hash = last.curr_hash if last else GENESIS_HASH
        entries = []
        timestamp = datetime.utcnow()
        for index, (actor_id, event_type, payload) in enumerate(events):
            created_at = timestamp + timedelta(microseconds=index)
            curr_hash = _compute_hash(prev_hash, actor_id, event_type, payload, created_at.isoformat())
            entry = models.AuditLog(
                actor_id=actor_id,
                event_type=event_type,
                event_payload=payload,
                prev_hash=prev_hash,
                curr_hash=curr_hash,
                created_at=created_at,
            )
            entries.append(entry)
            db.add(entry)
            queue_ledger_event(db, actor_id, event_type, payload, created_at)
            prev_hash = curr_hash
        db.commit()
        for entry in entries:
            db.refresh(entry)
        return entries


def verify_chain(db: Session):
    """Recomputes every hash from genesis and compares. Returns
    (True, None) if intact, or (False, <id of first broken entry>)."""
    entries = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
    prev_hash = GENESIS_HASH
    for entry in entries:
        expected = _compute_hash(prev_hash, entry.actor_id, entry.event_type, entry.event_payload, entry.created_at.isoformat())
        if expected != entry.curr_hash or entry.prev_hash != prev_hash:
            return False, entry.id
        prev_hash = entry.curr_hash
    return True, None
