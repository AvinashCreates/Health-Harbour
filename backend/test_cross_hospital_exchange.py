import os
import tempfile
import unittest
from datetime import datetime
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


class CrossHospitalExchangeTests(unittest.TestCase):
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
        models.Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        with self.session_factory() as db:
            self.patient = self._user(db, "Synthetic Patient", "patient", "patient@example.test")
            self.provider_b = self._user(db, "Synthetic Provider B", "doctor", "provider-b@example.test")
            self.provider_a = self._user(db, "Synthetic Provider A", "doctor", "provider-a@example.test")
            self.admin_b = self._user(db, "Synthetic Admin B", "admin", "admin-b@example.test")

            self.org_a = models.HealthcareOrganization(
                legal_name="Synthetic Hospital A", display_name="Hospital A", organization_type="HOSPITAL",
                administrative_contact_name="Admin A", administrative_contact_email="a@example.test", status="APPROVED",
            )
            self.org_b = models.HealthcareOrganization(
                legal_name="Synthetic Hospital B", display_name="Hospital B", organization_type="HOSPITAL",
                administrative_contact_name="Admin B", administrative_contact_email="b@example.test", status="APPROVED",
            )
            db.add_all([self.org_a, self.org_b])
            db.flush()

            self.provider_profile_b = models.HealthcareProvider(
                account_id=self.provider_b.id,
                professional_name="Synthetic Provider B",
                registration_authority="Synthetic Council",
                registration_number="SYN-B-1",
                qualifications=["Synthetic MD"],
                status="VERIFIED",
            )
            self.provider_profile_a = models.HealthcareProvider(
                account_id=self.provider_a.id,
                professional_name="Synthetic Provider A",
                registration_authority="Synthetic Council",
                registration_number="SYN-A-1",
                qualifications=["Synthetic MD"],
                status="VERIFIED",
            )
            db.add_all([self.provider_profile_b, self.provider_profile_a])
            db.flush()
            db.add(models.OrganizationAffiliation(
                organization_id=self.org_b.id,
                provider_id=self.provider_profile_b.id,
                account_id=self.provider_b.id,
                organization_role="PROVIDER",
                status="ACTIVE",
                invited_by_id=self.admin_b.id,
                effective_from=datetime.utcnow(),
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
            "patient": self._headers(self.patient.id),
            "provider_b": self._headers(self.provider_b.id),
            "provider_a": self._headers(self.provider_a.id),
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
        return {"Authorization": f"Bearer {create_access_token({'sub': user_id, 'role': 'ignored'})}"}

    def test_cross_hospital_request_approval_document_scope_and_revocation(self):
        created = self.client.post("/api/v1/cross-hospital/exchange-requests", headers=self.headers["provider_b"], json={
            "patient_id": self.patient.id,
            "requesting_organization_id": self.org_b.id,
            "source_organization_id": self.org_a.id,
            "resource_types": ["Document"],
            "requested_duration_days": 7,
            "reason": "Synthetic cross-hospital treatment review.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        exchange = created.json()

        self.assertEqual(self.client.get("/api/v1/cross-hospital/exchange-requests/me/patient", headers=self.headers["provider_b"]).status_code, 403)

        before = self.client.get(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/documents",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(before.status_code, 403)

        approved = self.client.post(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/patient-decision",
            headers=self.headers["patient"],
            json={"decision": "APPROVED", "reason": "I approve this limited exchange."},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        consent_id = approved.json()["consent_id"]
        self.assertIsNotNone(consent_id)

        with self.session_factory() as db:
            db.add(models.ClinicalFile(
                patient_id=self.patient.id,
                uploaded_by_id=self.patient.id,
                filename="hospital-a-record.txt",
                storage_key="hospital-a-record.blob",
                media_type="text/plain",
                category="clinical-record",
                size_bytes=23,
                sha256="a" * 64,
                processing_status="CLEAN",
                scan_status="NOT_REQUIRED",
                source_organization_id=self.org_a.id,
                custodian_organization_id=self.org_a.id,
            ))
            db.commit()

        documents = self.client.get(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/documents",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(documents.status_code, 200, documents.text)
        self.assertEqual(len(documents.json()), 1)
        document_id = documents.json()[0]["id"]

        imported = self.client.post(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/documents/{document_id}/import",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertTrue(imported.json()["integrity_verified"])
        self.assertEqual(imported.json()["source_organization_id"], self.org_a.id)
        self.assertEqual(imported.json()["receiving_organization_id"], self.org_b.id)

        wrong_document = self.client.post(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/documents/not-a-document/import",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(wrong_document.status_code, 404)

        revoked = self.client.post(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/patient-decision",
            headers=self.headers["patient"],
            json={"decision": "REVOKED", "reason": "I revoke this exchange."},
        )
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()["status"], "REVOKED")

        blocked = self.client.get(
            f"/api/v1/cross-hospital/exchange-requests/{exchange['id']}/documents",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(blocked.status_code, 403)

    def test_provider_cannot_create_exchange_for_unauthenticated_org_and_patient_cross_tenant_is_denied(self):
        denied_org = self.client.post("/api/v1/cross-hospital/exchange-requests", headers=self.headers["provider_a"], json={
            "patient_id": self.patient.id,
            "requesting_organization_id": self.org_b.id,
            "source_organization_id": self.org_a.id,
            "resource_types": ["Document"],
            "requested_duration_days": 7,
            "reason": "Attempted organization impersonation.",
        })
        self.assertIn(denied_org.status_code, {403, 404})

        foreign_patient = self.client.get(
            "/api/v1/cross-hospital/exchange-requests/me/patient",
            headers=self.headers["provider_b"],
        )
        self.assertEqual(foreign_patient.status_code, 403)


if __name__ == "__main__":
    unittest.main()
