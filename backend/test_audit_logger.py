import multiprocessing
import os
import queue
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

import database
import models
from services import audit_logger


def _postgres_writer_a(ready, release, result_queue):
    database.engine.dispose(close=False)
    try:
        with database.SessionLocal() as db:
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": audit_logger._POSTGRES_CHAIN_LOCK_ID},
            )
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            ready.set()
            if not release.wait(20):
                raise TimeoutError("Writer A was not released")
            entry = audit_logger.log_event(
                db, None, "PG_CONCURRENT_A", {"writer": "A"},
            )
            result_queue.put(("A", entry.id, backend_pid))
    except Exception as error:
        result_queue.put(("A_ERROR", type(error).__name__, str(error)))
    finally:
        database.engine.dispose(close=False)


def _postgres_writer_b(ready, result_queue):
    database.engine.dispose(close=False)
    try:
        with database.SessionLocal() as db:
            user = db.query(models.User).filter(
                models.User.email == "audit-concurrency@example.test",
            ).one()
            backend_pid = db.execute(text("SELECT pg_backend_pid()")).scalar_one()
            isolation = db.execute(text("SHOW transaction_isolation")).scalar_one()
            result_queue.put((
                "B_SNAPSHOT",
                user.id,
                backend_pid,
                isolation,
                db.in_transaction(),
            ))
            ready.set()
            entry = audit_logger.log_event(
                db, None, "PG_CONCURRENT_B", {"writer": "B"},
            )
            result_queue.put(("B", entry.id, backend_pid))
    except Exception as error:
        result_queue.put(("B_ERROR", type(error).__name__, str(error)))
    finally:
        database.engine.dispose(close=False)


class AuditLoggerConcurrencyTests(unittest.TestCase):
    def test_concurrent_events_preserve_hash_chain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine(f"sqlite:///{Path(temp_dir) / 'audit.db'}")
            models.Base.metadata.create_all(engine)
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
            barrier = threading.Barrier(12)

            def write_event(index):
                with session_factory() as db:
                    barrier.wait()
                    audit_logger.log_event(db, None, "CONCURRENCY_TEST", {"index": index})

            try:
                with patch.object(audit_logger, "queue_ledger_event"):
                    with ThreadPoolExecutor(max_workers=12) as executor:
                        list(executor.map(write_event, range(12)))

                with session_factory() as db:
                    valid, broken_at = audit_logger.verify_chain(db)
                    self.assertTrue(valid, f"Hash chain broke at audit row {broken_at}")
                    self.assertEqual(db.query(models.AuditLog).count(), 12)
            finally:
                engine.dispose()

    @unittest.skipUnless(
        os.getenv("AUDIT_TEST_POSTGRES") == "1",
        "Set AUDIT_TEST_POSTGRES=1 with DATABASE_URL targeting a disposable PostgreSQL test DB",
    )
    def test_postgresql_repeatable_read_server_default_serializes_appends(self):
        test_url = make_url(database.DATABASE_URL)
        self.assertEqual(test_url.get_backend_name(), "postgresql")
        self.assertIn(test_url.host, {"localhost", "127.0.0.1", "::1"})
        self.assertTrue(
            (test_url.database or "").startswith("audit_test_"),
            "PostgreSQL audit tests require a database named audit_test_*",
        )
        self.assertEqual(
            test_url.port,
            55439,
            "PostgreSQL audit tests require the isolated review server on port 55439",
        )

        with database.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SHOW transaction_isolation")).scalar_one().lower(),
                "read committed",
            )
        import psycopg2

        raw_connection = psycopg2.connect(
            host=test_url.host,
            port=test_url.port,
            dbname=test_url.database,
            user=test_url.username,
            password=test_url.password,
        )
        try:
            with raw_connection.cursor() as cursor:
                cursor.execute("SHOW default_transaction_isolation")
                server_default = cursor.fetchone()[0]
        finally:
            raw_connection.close()
        expected_default = os.getenv(
            "AUDIT_TEST_SERVER_DEFAULT",
            "repeatable read",
        ).lower()
        self.assertEqual(server_default.lower(), expected_default)

        self.addCleanup(database.engine.dispose)
        models.Base.metadata.create_all(database.engine)
        with database.SessionLocal() as db:
            self.assertEqual(db.query(models.AuditLog).count(), 0)
            self.assertEqual(db.query(models.User).count(), 0)
            db.add(models.User(
                full_name="Synthetic Audit Test User",
                email="audit-concurrency@example.test",
                hashed_password="not-a-login-credential",
                role="admin",
            ))
            db.commit()
            self.assertFalse(db.in_transaction())
            user = db.query(models.User).filter(
                models.User.email == "audit-concurrency@example.test",
            ).one()
            self.assertTrue(db.in_transaction())
            transaction_isolation = db.execute(
                text("SHOW transaction_isolation"),
            ).scalar_one()
            self.assertEqual(user.email, "audit-concurrency@example.test")
            self.assertEqual(transaction_isolation.lower(), "read committed")

        context = multiprocessing.get_context("fork")
        writer_a_ready = context.Event()
        writer_a_release = context.Event()
        writer_b_ready = context.Event()
        result_queue = context.Queue()
        writer_a = context.Process(
            target=_postgres_writer_a,
            args=(writer_a_ready, writer_a_release, result_queue),
        )
        writer_b = None
        try:
            writer_a.start()
            self.assertTrue(
                writer_a_ready.wait(15),
                "Writer A did not acquire its advisory lock",
            )

            writer_b = context.Process(
                target=_postgres_writer_b,
                args=(writer_b_ready, result_queue),
            )
            writer_b.start()
            self.assertTrue(
                writer_b_ready.wait(15),
                "Writer B did not establish its transaction",
            )
            b_snapshot = result_queue.get(timeout=5)
            self.assertEqual(b_snapshot[0], "B_SNAPSHOT", b_snapshot)
            self.assertEqual(b_snapshot[3].lower(), "read committed")
            self.assertTrue(b_snapshot[4])

            deadline = time.monotonic() + 15
            b_waiting_on_advisory_lock = False
            while time.monotonic() < deadline:
                with database.engine.connect() as connection:
                    wait_event = connection.execute(
                        text(
                            "SELECT wait_event_type, wait_event "
                            "FROM pg_stat_activity WHERE pid = :pid"
                        ),
                        {"pid": b_snapshot[2]},
                    ).one_or_none()
                if wait_event and (
                    wait_event.wait_event_type == "Lock"
                    and wait_event.wait_event == "advisory"
                ):
                    b_waiting_on_advisory_lock = True
                    break
                time.sleep(0.05)
            self.assertTrue(
                b_waiting_on_advisory_lock,
                "Writer B did not wait for Writer A's PostgreSQL advisory lock",
            )
        finally:
            writer_a_release.set()
            writer_a.join(20)
            if writer_b is not None:
                writer_b.join(20)
            for process in (writer_a, writer_b):
                if process is not None and process.is_alive():
                    process.terminate()
                    process.join()
        self.assertFalse(writer_a.is_alive(), "Writer A did not finish")
        self.assertIsNotNone(writer_b)
        self.assertFalse(writer_b.is_alive(), "Writer B did not finish")

        worker_results = [b_snapshot]
        while True:
            try:
                worker_results.append(result_queue.get_nowait())
            except queue.Empty:
                break
        errors = [result for result in worker_results if result[0].endswith("_ERROR")]
        self.assertEqual(errors, [], worker_results)
        writer_a_result = next(result for result in worker_results if result[0] == "A")
        writer_b_result = next(result for result in worker_results if result[0] == "B")
        self.assertNotEqual(writer_a_result[2], writer_b_result[2])
        self.assertLess(writer_a_result[1], writer_b_result[1])

        with database.SessionLocal() as db:
            entries = db.query(models.AuditLog).filter(
                models.AuditLog.event_type.in_(["PG_CONCURRENT_A", "PG_CONCURRENT_B"]),
            ).order_by(models.AuditLog.id.asc()).all()
            self.assertEqual([entry.event_type for entry in entries], [
                "PG_CONCURRENT_A",
                "PG_CONCURRENT_B",
            ])
            all_entries = db.query(models.AuditLog).order_by(
                models.AuditLog.id.asc(),
            ).all()
            by_id = {entry.id: index for index, entry in enumerate(all_entries)}
            for entry in entries:
                entry_index = by_id[entry.id]
                expected_prev_hash = (
                    audit_logger.GENESIS_HASH
                    if entry_index == 0
                    else all_entries[entry_index - 1].curr_hash
                )
                self.assertEqual(entry.prev_hash, expected_prev_hash)
                expected_hash = audit_logger._compute_hash(
                    entry.prev_hash,
                    entry.actor_id,
                    entry.event_type,
                    entry.event_payload,
                    entry.created_at.isoformat(),
                )
                self.assertEqual(entry.curr_hash, expected_hash)

            previous_tail = all_entries[-1]
            discontinuous_prev_hash = "f" * 64
            discontinuous_created_at = datetime.utcnow()
            discontinuous_payload = {"synthetic": "historical discontinuity"}
            discontinuous_hash = audit_logger._compute_hash(
                discontinuous_prev_hash,
                None,
                "PG_SYNTHETIC_DISCONTINUITY",
                discontinuous_payload,
                discontinuous_created_at.isoformat(),
            )
            discontinuity = models.AuditLog(
                actor_id=None,
                event_type="PG_SYNTHETIC_DISCONTINUITY",
                event_payload=discontinuous_payload,
                prev_hash=discontinuous_prev_hash,
                curr_hash=discontinuous_hash,
                created_at=discontinuous_created_at,
            )
            db.add(discontinuity)
            db.commit()
            db.refresh(discontinuity)
            stored_discontinuity = (
                discontinuity.prev_hash,
                discontinuity.curr_hash,
                discontinuity.created_at,
            )
            appended = audit_logger.log_event(
                db, None, "PG_APPEND_AFTER_DISCONTINUITY", {"synthetic": True},
            )
            db.refresh(discontinuity)
            self.assertEqual(
                (
                    discontinuity.prev_hash,
                    discontinuity.curr_hash,
                    discontinuity.created_at,
                ),
                stored_discontinuity,
            )
            self.assertEqual(appended.prev_hash, discontinuity.curr_hash)
            self.assertEqual(
                appended.curr_hash,
                audit_logger._compute_hash(
                    appended.prev_hash,
                    appended.actor_id,
                    appended.event_type,
                    appended.event_payload,
                    appended.created_at.isoformat(),
                ),
            )
            self.assertNotEqual(previous_tail.curr_hash, discontinuity.prev_hash)

            before_failure_count = db.query(models.AuditLog).count()
            db.execute(text("""
                CREATE FUNCTION reject_synthetic_audit_insert() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.event_type = 'PG_SYNTHETIC_FAILURE' THEN
                        RAISE EXCEPTION 'synthetic audit insert failure';
                    END IF;
                    RETURN NEW;
                END
                $$
            """))
            db.execute(text("""
                CREATE TRIGGER reject_synthetic_audit_insert_trigger
                BEFORE INSERT ON audit_log
                FOR EACH ROW EXECUTE FUNCTION reject_synthetic_audit_insert()
            """))
            db.commit()
            with self.assertRaises(DBAPIError):
                audit_logger.log_event(
                    db, None, "PG_SYNTHETIC_FAILURE", {"synthetic": True},
                )
            db.rollback()
            self.assertEqual(db.query(models.AuditLog).count(), before_failure_count)
            self.assertEqual(db.query(models.AuditLog).filter_by(
                event_type="PG_SYNTHETIC_FAILURE",
            ).count(), 0)
            db.execute(text("DROP TRIGGER reject_synthetic_audit_insert_trigger ON audit_log"))
            db.execute(text("DROP FUNCTION reject_synthetic_audit_insert()"))
            db.commit()
            post_failure = audit_logger.log_event(
                db, None, "PG_SYNTHETIC_AFTER_ROLLBACK", {"synthetic": True},
            )
            self.assertEqual(post_failure.prev_hash, appended.curr_hash)
            self.assertEqual(
                post_failure.curr_hash,
                audit_logger._compute_hash(
                    post_failure.prev_hash,
                    post_failure.actor_id,
                    post_failure.event_type,
                    post_failure.event_payload,
                    post_failure.created_at.isoformat(),
                ),
            )


if __name__ == "__main__":
    unittest.main()
