import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from auth_utils import create_access_token
from main import app


class CareRequestApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "AUTH_PROVIDER": "local",
            "FHIR_MODE": "local",
            "FABRIC_ENABLED": "false",
            "FILE_STORAGE_PATH": str(Path(self.temp_dir.name) / "files"),
        })
        self.environment.start()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.session_factory() as db:
            self.patient_a = self._user(db, "Patient A", "patient", "patient-a@example.com")
            self.patient_b = self._user(db, "Patient B", "patient", "patient-b@example.com")
            self.provider_account = self._user(db, "Dr Verified", "doctor", "provider@example.com")
            self.other_provider_account = self._user(db, "Dr Other", "doctor", "other-provider@example.com")
            self.admin = self._user(db, "Platform Admin", "admin", "admin@example.com")
            db.add_all([
                models.HealthcareOrganization(
                    legal_name="Synthetic A", display_name="Synthetic Hospital A",
                    organization_type="HOSPITAL", administrative_contact_name="Admin",
                    administrative_contact_email="admin-a@example.com", status="APPROVED",
                ),
                models.HealthcareOrganization(
                    legal_name="Synthetic B", display_name="Synthetic Hospital B",
                    organization_type="HOSPITAL", administrative_contact_name="Admin",
                    administrative_contact_email="admin-b@example.com", status="APPROVED",
                ),
            ])
            db.flush()
            self.organization_a = db.query(models.HealthcareOrganization).filter_by(display_name="Synthetic Hospital A").one()
            self.organization_b = db.query(models.HealthcareOrganization).filter_by(display_name="Synthetic Hospital B").one()
            self.provider = models.HealthcareProvider(
                account_id=self.provider_account.id,
                professional_name="Dr Verified",
                registration_authority="Synthetic Council",
                registration_number="SYN-100",
                qualifications=["Synthetic MBBS"],
                specialization="Cardiology",
                status="VERIFIED",
            )
            self.other_provider = models.HealthcareProvider(
                account_id=self.other_provider_account.id,
                professional_name="Dr Other",
                registration_authority="Synthetic Council",
                registration_number="SYN-200",
                qualifications=["Synthetic MD"],
                status="VERIFIED",
            )
            db.add_all([self.provider, self.other_provider])
            db.flush()
            db.add(models.OrganizationAffiliation(
                organization_id=self.organization_a.id,
                provider_id=self.provider.id,
                account_id=self.provider_account.id,
                organization_role="PROVIDER",
                status="ACTIVE",
                invited_by_id=self.admin.id,
                effective_from=__import__("datetime").datetime.utcnow(),
            ))
            db.commit()

        def override_get_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(app)
        self.headers = {
            "patient_a": self._headers(self.patient_a.id),
            "patient_b": self._headers(self.patient_b.id),
            "provider": self._headers(self.provider_account.id),
            "other_provider": self._headers(self.other_provider_account.id),
        }

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(database.get_db, None)
        self.engine.dispose()
        self.environment.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _user(db, name, role, email):
        user = models.User(full_name=name, email=email, hashed_password="unused", role=role)
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def _headers(user_id):
        token = create_access_token({"sub": user_id, "role": "ignored"})
        return {"Authorization": f"Bearer {token}"}

    def test_patient_connection_and_provider_response(self):
        created = self.client.post("/api/v1/care-connections", headers=self.headers["patient_a"], json={
            "provider_id": self.provider.id,
            "organization_id": self.organization_a.id,
            "reason": "I need ongoing cardiology care.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        connection = created.json()
        self.assertEqual(connection["status"], "INITIATED")

        duplicate = self.client.post("/api/v1/care-connections", headers=self.headers["patient_a"], json={
            "provider_id": self.provider.id,
            "organization_id": self.organization_a.id,
            "reason": "Duplicate request.",
        })
        self.assertEqual(duplicate.status_code, 409)

        other_provider = self.client.post(
            f"/api/v1/care-connections/{connection['id']}/provider-response",
            headers=self.headers["other_provider"],
            json={"decision": "ACCEPTED", "response": "I will review your request."},
        )
        self.assertIn(other_provider.status_code, {403, 404})

        accepted = self.client.post(
            f"/api/v1/care-connections/{connection['id']}/provider-response",
            headers=self.headers["provider"],
            json={"decision": "ACCEPTED", "response": "I accept this care connection."},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["status"], "ACCEPTED")

    def test_record_request_requires_affiliation_and_patient_owner(self):
        created = self.client.post("/api/v1/record-requests", headers=self.headers["provider"], json={
            "patient_id": self.patient_a.id,
            "organization_id": self.organization_a.id,
            "resource_types": ["Document", "DiagnosticReport"],
            "requested_duration_days": 7,
            "reason": "Review recent cardiac records.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        request = created.json()

        wrong_patient = self.client.post(
            f"/api/v1/record-requests/{request['id']}/patient-decision",
            headers=self.headers["patient_b"],
            json={"decision": "APPROVED", "response_reason": "Not authorized owner."},
        )
        self.assertEqual(wrong_patient.status_code, 404)

        wrong_org = self.client.post("/api/v1/record-requests", headers=self.headers["provider"], json={
            "patient_id": self.patient_a.id,
            "organization_id": self.organization_b.id,
            "resource_types": ["Document"],
            "requested_duration_days": 7,
            "reason": "Try another organization.",
        })
        self.assertEqual(wrong_org.status_code, 403)

    def test_patient_approval_creates_existing_consent_and_rejection_creates_no_consent(self):
        created = self.client.post("/api/v1/record-requests", headers=self.headers["provider"], json={
            "patient_id": self.patient_a.id,
            "organization_id": self.organization_a.id,
            "resource_types": ["Document", "DiagnosticReport"],
            "requested_duration_days": 10,
            "reason": "Care review requested.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        request = created.json()
        approved = self.client.post(
            f"/api/v1/record-requests/{request['id']}/patient-decision",
            headers=self.headers["patient_a"],
            json={"decision": "APPROVED", "response_reason": "I consent to this specific review."},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        consent_id = approved.json()["consent_id"]
        self.assertIsNotNone(consent_id)

        consents = self.client.get("/consent/active", headers=self.headers["patient_a"])
        self.assertEqual(consents.status_code, 200)
        match = [item for item in consents.json() if item["id"] == consent_id]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["organization_id"], self.organization_a.id)
        self.assertTrue(match[0]["is_active"])

        rejected_request = self.client.post("/api/v1/record-requests", headers=self.headers["provider"], json={
            "patient_id": self.patient_a.id,
            "organization_id": self.organization_a.id,
            "resource_types": ["Observation"],
            "requested_duration_days": 5,
            "reason": "I need observation data.",
        })
        self.assertEqual(rejected_request.status_code, 201, rejected_request.text)
        rejected = self.client.post(
            f"/api/v1/record-requests/{rejected_request.json()['id']}/patient-decision",
            headers=self.headers["patient_a"],
            json={"decision": "REJECTED", "response_reason": "I do not authorize this request."},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["status"], "REJECTED")
        self.assertIsNone(rejected.json()["consent_id"])

    def test_suspended_provider_and_affiliation_changes_block_requests(self):
        with self.session_factory() as db:
            provider = db.query(models.HealthcareProvider).filter_by(id=self.provider.id).one()
            provider.status = "SUSPENDED"
            db.commit()

        connection = self.client.post("/api/v1/care-connections", headers=self.headers["patient_a"], json={
            "provider_id": self.provider.id,
            "organization_id": self.organization_a.id,
            "reason": "Suspended provider connection attempt.",
        })
        self.assertIn(connection.status_code, {403, 404})

        record_request = self.client.post("/api/v1/record-requests", headers=self.headers["provider"], json={
            "patient_id": self.patient_a.id,
            "organization_id": self.organization_a.id,
            "resource_types": ["Document"],
            "requested_duration_days": 7,
            "reason": "Suspension test.",
        })
        self.assertIn(record_request.status_code, {403, 404})


if __name__ == "__main__":
    unittest.main()
