import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from services import audit_logger


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


if __name__ == "__main__":
    unittest.main()
