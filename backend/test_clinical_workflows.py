import os
import tempfile
import unittest
from datetime import datetime, timedelta
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


class ClinicalWorkflowTests(unittest.TestCase):
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
            self.patient = self._user(db, "Synthetic Patient", "patient", "patient@example.test")
            self.doctor = self._user(db, "Synthetic Doctor", "doctor", "doctor@example.test")
            self.other_doctor = self._user(db, "Synthetic Other Doctor", "doctor", "other@example.test")
            self.admin = self._user(db, "Synthetic Admin", "admin", "admin@example.test")
            organization = models.HealthcareOrganization(
                legal_name="Synthetic Hospital", display_name="Synthetic Hospital",
                organization_type="HOSPITAL", administrative_contact_name="Admin",
                administrative_contact_email="hospital@example.test", status="APPROVED",
            )
            db.add(organization)
            db.flush()
            provider = models.HealthcareProvider(
                account_id=self.doctor.id,
                professional_name="Synthetic Doctor",
                registration_authority="Synthetic Council",
                registration_number="SYN-1",
                qualifications=["Synthetic MD"],
                status="VERIFIED",
            )
            db.add(provider)
            db.flush()
            db.add(models.OrganizationAffiliation(
                organization_id=organization.id,
                provider_id=provider.id,
                account_id=self.doctor.id,
                organization_role="PROVIDER",
                status="ACTIVE",
                invited_by_id=self.admin.id,
                effective_from=datetime.utcnow(),
            ))
            db.add(models.Consent(
                patient_id=self.patient.id,
                grantee_id=self.doctor.id,
                organization_id=organization.id,
                resource_types=["MedicationRequest", "DiagnosticReport"],
                purpose="TREATMENT",
                granted_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
            ))
            db.commit()
            self.organization_id = organization.id
            self.provider_id = provider.id

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
            "doctor": self._headers(self.doctor.id),
            "other": self._headers(self.other_doctor.id),
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

    def test_prescription_creation_transition_and_cross_patient_denial(self):
        created = self.client.post("/api/v1/prescriptions", headers=self.headers["doctor"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "medication_name": "Synthetic Example Medication",
            "dosage": "1 synthetic unit",
            "route": "oral",
            "frequency": "once daily",
            "duration": "7 days",
            "quantity": "7 units",
            "instructions": "Synthetic test instruction only",
            "activate": True,
        })
        self.assertEqual(created.status_code, 201, created.text)
        prescription = created.json()
        self.assertEqual(prescription["status"], "ACTIVE")

        transitioned = self.client.post(
            f"/api/v1/prescriptions/{prescription['id']}/transition",
            headers=self.headers["doctor"],
            json={"status": "STOPPED", "reason": "Synthetic clinical stop reason"},
        )
        self.assertEqual(transitioned.status_code, 200, transitioned.text)
        self.assertEqual(transitioned.json()["status"], "STOPPED")

        other = self.client.post("/api/v1/prescriptions", headers=self.headers["other"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "medication_name": "Synthetic Unauthorized Medication",
            "dosage": "1 unit",
            "frequency": "once",
            "activate": True,
        })
        self.assertIn(other.status_code, {403, 404})

        cross_patient = self.client.get("/api/v1/prescriptions/me/patient", headers=self.headers["doctor"])
        self.assertEqual(cross_patient.status_code, 403)

    def test_physician_clinical_review_requires_consent_and_links_resources(self):
        report = models.FHIRResource(
            resource_type="DiagnosticReport",
            fhir_id="synthetic-report-1",
            resource_data={"resourceType": "DiagnosticReport", "id": "synthetic-report-1", "status": "final"},
            owner_id=self.patient.id,
            created_by=self.admin.id,
        )
        with self.session_factory() as db:
            db.add(report)
            db.commit()

        created = self.client.post("/api/v1/clinical-reviews", headers=self.headers["doctor"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "diagnostic_report_id": report.fhir_id,
            "status": "FOLLOW_UP_REQUIRED",
            "clinical_note": "Synthetic follow-up note",
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["status"], "FOLLOW_UP_REQUIRED")

        wrong_patient = self.client.post("/api/v1/clinical-reviews", headers=self.headers["other"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "diagnostic_report_id": report.fhir_id,
            "status": "REVIEWED",
            "clinical_note": "Unauthorized synthetic review",
        })
        self.assertIn(wrong_patient.status_code, {403, 404})


if __name__ == "__main__":
    unittest.main()
