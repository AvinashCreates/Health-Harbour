import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import rate_limit
import database
from auth_utils import create_access_token, hash_password
from main import app
from routers import fhir as fhir_router
from services.fhir_server import FHIRIntegrationError


BACKEND_DIR = Path(__file__).resolve().parent
STRONG_PASSWORD = "Strong-Seed-Password-2048!"


class SharedLoginRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            f"sqlite:///{Path(self.temp_dir.name) / 'rate-limit.db'}",
            connect_args={"timeout": 15},
        )
        models.Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_limit_is_shared_across_sessions_and_expires(self):
        identifier = "person@example.test"
        now = datetime(2026, 1, 1, 12, 0)
        for _ in range(rate_limit.MAX_ATTEMPTS - 1):
            with self.session_factory() as db:
                rate_limit.record_failure(db, identifier, now=now)

        with self.session_factory() as db:
            self.assertEqual(rate_limit.is_locked_out(db, identifier, now=now), 0)
            rate_limit.record_failure(db, identifier, now=now)
        with self.session_factory() as db:
            self.assertEqual(rate_limit.is_locked_out(db, identifier, now=now), rate_limit.LOCKOUT_SECONDS)
            self.assertEqual(
                rate_limit.is_locked_out(
                    db,
                    identifier,
                    now=now + timedelta(seconds=rate_limit.LOCKOUT_SECONDS + 1),
                ),
                0,
            )

    def test_concurrent_failures_are_counted_atomically(self):
        identifier = "concurrent@example.test"
        now = datetime(2026, 1, 1, 12, 0)

        def fail_login(_):
            with self.session_factory() as db:
                rate_limit.record_failure(db, identifier, now=now)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(fail_login, range(8)))

        with self.session_factory() as db:
            self.assertGreater(
                rate_limit.is_locked_out(db, identifier, now=now),
                0,
            )

    def test_success_clears_the_shared_failure_state(self):
        identifier = "reset@example.test"
        now = datetime(2026, 1, 1, 12, 0)
        for _ in range(rate_limit.MAX_ATTEMPTS):
            with self.session_factory() as db:
                rate_limit.record_failure(db, identifier, now=now)
        with self.session_factory() as db:
            rate_limit.record_success(db, identifier)
        with self.session_factory() as db:
            self.assertEqual(rate_limit.is_locked_out(db, identifier, now=now), 0)
            rate_limit.record_failure(db, identifier, now=now)
        with self.session_factory() as db:
            record = db.query(models.LoginRateLimit).one()
            self.assertEqual(record.failure_count, 1)
            self.assertIsNone(record.locked_until)

    def test_failure_updates_prune_expired_records(self):
        now = datetime(2026, 1, 2, 12, 0)
        with self.session_factory() as db:
            db.add(models.LoginRateLimit(
                key_hash="stale-key",
                failure_count=1,
                window_started_at=now - timedelta(days=2),
                locked_until=None,
                updated_at=now - rate_limit.STALE_RECORD_RETENTION - timedelta(seconds=1),
            ))
            db.commit()
        with self.session_factory() as db:
            rate_limit.record_failure(db, "fresh@example.com", now=now)
        with self.session_factory() as db:
            self.assertIsNone(db.query(models.LoginRateLimit).filter_by(
                key_hash="stale-key",
            ).one_or_none())

    def test_storage_errors_fail_closed(self):
        with self.session_factory() as db:
            with patch.object(
                db,
                "execute",
                side_effect=OperationalError("SELECT", {}, RuntimeError("offline")),
            ):
                with self.assertRaises(rate_limit.RateLimitStoreError):
                    rate_limit.is_locked_out(db, "offline@example.test")

    def test_api_returns_service_unavailable_if_rate_limit_store_fails(self):
        def override_get_db():
            with self.session_factory() as db:
                yield db

        app.dependency_overrides[database.get_db] = override_get_db
        try:
            with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}):
                with patch.object(
                    rate_limit,
                    "is_locked_out",
                    side_effect=rate_limit.RateLimitStoreError("store offline"),
                ):
                    with TestClient(app) as client:
                        response = client.post("/auth/login", json={
                            "email": "person@example.com",
                            "password": "Not-used-in-this-test",
                        })
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {"detail": "Sign-in is temporarily unavailable"})
        finally:
            app.dependency_overrides.pop(database.get_db, None)


class SeedCredentialTests(unittest.TestCase):
    def _environment(self, database_path):
        env = os.environ.copy()
        for key in (
            "DEMO_SEED_PASSWORD",
            "INITIAL_ADMIN_EMAIL",
            "INITIAL_ADMIN_NAME",
            "INITIAL_ADMIN_PASSWORD",
        ):
            env.pop(key, None)
        env.update({
            "DATABASE_URL": f"sqlite:///{database_path}",
            "DB_AUTO_CREATE": "0",
            "AUTH_PROVIDER": "local",
            "FHIR_MODE": "local",
            "APP_ENV": "development",
        })
        return env

    def _run_seed(self, env):
        return subprocess.run(
            [sys.executable, "seed.py"],
            cwd=BACKEND_DIR,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )

    def test_demo_seed_requires_explicit_strong_password_without_echoing_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = self._environment(Path(temp_dir) / "missing.db")
            result = self._run_seed(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("DEMO_SEED_PASSWORD", result.stderr)
            self.assertNotIn(STRONG_PASSWORD, result.stdout + result.stderr)

            env["DEMO_SEED_PASSWORD"] = "weak"
            result = self._run_seed(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("16-72 UTF-8 bytes", result.stderr)
            self.assertNotIn("weak", result.stdout + result.stderr)

    def test_production_seed_creates_only_explicit_administrator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            env = self._environment(database_path)
            env.update({
                "APP_ENV": "production",
                "JWT_SECRET": "isolated-production-test-secret-0123456789-abcdefgh",
                "INITIAL_ADMIN_EMAIL": "owner@example.test",
                "INITIAL_ADMIN_NAME": "Production Owner",
                "INITIAL_ADMIN_PASSWORD": STRONG_PASSWORD,
            })
            result = self._run_seed(env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(STRONG_PASSWORD, result.stdout + result.stderr)
            with sqlite3.connect(database_path) as db:
                users = db.execute("SELECT email, role FROM users").fetchall()
            self.assertEqual(users, [("owner@example.test", "admin")])
            self.assertNotIn("asha.patient@example.com", result.stdout + result.stderr)

    def test_production_seed_rejects_missing_or_weak_admin_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = self._environment(Path(temp_dir) / "not-created.db")
            env.update({
                "APP_ENV": "production",
                "JWT_SECRET": "isolated-production-test-secret-0123456789-abcdefgh",
                "INITIAL_ADMIN_EMAIL": "owner@example.test",
                "INITIAL_ADMIN_NAME": "Production Owner",
            })
            result = self._run_seed(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("INITIAL_ADMIN_PASSWORD", result.stderr)

            env["INITIAL_ADMIN_PASSWORD"] = "weak"
            result = self._run_seed(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("16-72 UTF-8 bytes", result.stderr)
            self.assertNotIn("weak", result.stdout + result.stderr)


class FHIRResponseRedactionTests(unittest.TestCase):
    def test_upstream_diagnostics_are_not_returned_to_api_clients(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        with session_factory() as db:
            patient = models.User(
                full_name="Redaction Test Patient",
                email="redaction@example.test",
                hashed_password=hash_password("Temporary-test-password-2048!"),
                role="patient",
                fhir_resource_id="redaction-patient",
            )
            db.add(patient)
            db.flush()
            db.add(models.FHIRResource(
                resource_type="Patient",
                fhir_id=patient.fhir_resource_id,
                resource_data={"resourceType": "Patient", "id": patient.fhir_resource_id},
                owner_id=patient.id,
                created_by=patient.id,
            ))
            db.commit()
            patient_id = patient.id
            token = create_access_token({"sub": patient.id, "role": patient.role})

        def override_get_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[database.get_db] = override_get_db
        sensitive = "https://internal.fhir.example/private-token clinical diagnostic"
        try:
            with patch.dict(os.environ, {"AUTH_PROVIDER": "local"}):
                with patch.object(
                    fhir_router,
                    "authoritative_resource",
                    side_effect=FHIRIntegrationError(
                        sensitive,
                        status_code=503,
                        operation="patient read",
                        upstream_status_code=500,
                    ),
                ):
                    with TestClient(app) as client:
                        response = client.get(
                            f"/fhir/Patient/{patient_id}",
                            headers={"Authorization": f"Bearer {token}"},
                        )
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {"detail": "FHIR service is unavailable"})
            self.assertNotIn(sensitive, response.text)
        finally:
            app.dependency_overrides.pop(database.get_db, None)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
