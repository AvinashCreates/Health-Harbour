import hashlib
import hmac
import logging
import math
from datetime import datetime, timedelta

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models
from auth_utils import SECRET_KEY

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
LOCKOUT_SECONDS = 60
STALE_RECORD_RETENTION = timedelta(days=1)


class RateLimitStoreError(RuntimeError):
    """Raised when the shared login rate-limit state cannot be accessed."""


def _key(identifier: str) -> str:
    normalized = identifier.lower().strip().encode("utf-8")
    return hmac.new(SECRET_KEY.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


def _raise_store_error(operation: str, error: SQLAlchemyError) -> RateLimitStoreError:
    logger.error(
        "Shared login rate-limit store %s failed (%s)",
        operation,
        type(error).__name__,
    )
    return RateLimitStoreError("Shared login rate-limit storage is unavailable")


def _rollback_after_error(db: Session, operation: str) -> None:
    try:
        db.rollback()
    except SQLAlchemyError as error:
        logger.error(
            "Shared login rate-limit store rollback failed after %s (%s)",
            operation,
            type(error).__name__,
        )


def is_locked_out(
    db: Session,
    identifier: str,
    *,
    now: datetime | None = None,
) -> float:
    """Return rounded seconds remaining in a shared account lockout."""
    now = now or datetime.utcnow()
    try:
        record = db.execute(
            select(models.LoginRateLimit).where(
                models.LoginRateLimit.key_hash == _key(identifier),
            ).execution_options(populate_existing=True)
        ).scalar_one_or_none()
    except SQLAlchemyError as error:
        _rollback_after_error(db, "read")
        raise _raise_store_error("read", error) from error
    if record is None or record.locked_until is None:
        return 0
    remaining = (record.locked_until - now).total_seconds()
    return float(math.ceil(remaining)) if remaining > 0 else 0


def record_failure(
    db: Session,
    identifier: str,
    *,
    now: datetime | None = None,
) -> None:
    """Atomically record a failed login across workers and API instances."""
    now = now or datetime.utcnow()
    try:
        dialect = db.get_bind().dialect.name
    except SQLAlchemyError as error:
        _rollback_after_error(db, "bind")
        raise _raise_store_error("bind", error) from error
    if dialect == "postgresql":
        insert = postgresql_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        logger.error("Shared login rate limiting does not support database dialect %s", dialect)
        raise RateLimitStoreError(
            f"Shared login rate limiting does not support database dialect {dialect!r}"
        )

    table = models.LoginRateLimit.__table__
    expired_window = table.c.window_started_at <= now - timedelta(seconds=WINDOW_SECONDS)
    next_failure_count = case(
        (expired_window, 1),
        else_=table.c.failure_count + 1,
    )
    statement = insert(table).values(
        key_hash=_key(identifier),
        failure_count=1,
        window_started_at=now,
        locked_until=None,
        updated_at=now,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[table.c.key_hash],
        set_={
            "failure_count": next_failure_count,
            "window_started_at": case(
                (expired_window, now),
                else_=table.c.window_started_at,
            ),
            "locked_until": case(
                (expired_window, None),
                (next_failure_count >= MAX_ATTEMPTS, now + timedelta(seconds=LOCKOUT_SECONDS)),
                else_=table.c.locked_until,
            ),
            "updated_at": now,
        },
    )
    try:
        db.execute(statement)
        db.execute(delete(table).where(
            table.c.updated_at < now - STALE_RECORD_RETENTION,
        ))
        db.commit()
    except SQLAlchemyError as error:
        _rollback_after_error(db, "write")
        raise _raise_store_error("write", error) from error


def record_success(db: Session, identifier: str) -> None:
    """Clear prior failures after a successful login."""
    try:
        db.execute(delete(models.LoginRateLimit).where(
            models.LoginRateLimit.key_hash == _key(identifier),
        ))
        db.commit()
    except SQLAlchemyError as error:
        _rollback_after_error(db, "clear")
        raise _raise_store_error("clear", error) from error
