"""Read-only forensic check for the first audit-chain mismatch."""

import sys

from sqlalchemy import text

import models
from database import SessionLocal
from services.audit_logger import GENESIS_HASH, _compute_hash


def main() -> int:
    db = SessionLocal()
    try:
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            db.execute(text("SET TRANSACTION READ ONLY"))
        elif dialect == "sqlite":
            db.execute(text("PRAGMA query_only = ON"))

        entries = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
        print(f"database_dialect={dialect}")
        print(f"audit_entry_count={len(entries)}")

        previous_hash = GENESIS_HASH
        for entry in entries:
            timestamp_iso = entry.created_at.isoformat()
            recomputed_hash = _compute_hash(
                previous_hash,
                entry.actor_id,
                entry.event_type,
                entry.event_payload,
                timestamp_iso,
            )
            previous_link_matches = entry.prev_hash == previous_hash
            current_hash_matches = entry.curr_hash == recomputed_hash
            if not previous_link_matches or not current_hash_matches:
                hash_from_stored_link = _compute_hash(
                    entry.prev_hash,
                    entry.actor_id,
                    entry.event_type,
                    entry.event_payload,
                    timestamp_iso,
                )
                print("chain_valid=false")
                print(f"first_mismatch_id={entry.id}")
                print(f"event_type={entry.event_type}")
                print(f"created_at={timestamp_iso}")
                print(f"previous_link_matches={str(previous_link_matches).lower()}")
                print(f"stored_prev_hash={entry.prev_hash}")
                print(f"expected_prev_hash={previous_hash}")
                print(f"current_hash_matches={str(current_hash_matches).lower()}")
                print(
                    "current_hash_matches_stored_prev="
                    f"{str(entry.curr_hash == hash_from_stored_link).lower()}"
                )
                print(f"stored_curr_hash={entry.curr_hash}")
                print(f"recomputed_curr_hash_from_stored_prev={hash_from_stored_link}")
                print(f"recomputed_curr_hash={recomputed_hash}")
                return 2
            previous_hash = entry.curr_hash

        print("chain_valid=true")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
