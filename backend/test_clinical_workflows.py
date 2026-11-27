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
            self.patient = self._user(db, "Synthetic Patient", "patient", "patient@example.com")
            self.doctor = self._user(db, "Synthetic Doctor", "doctor", "doctor@example.com")
            self.other_doctor = self._user(db, "Synthetic Other Doctor", "doctor", "other@example.com")
            self.lab = self._user(db, "Synthetic Lab", "lab", "lab@example.com")
            self.technician = self._user(db, "Synthetic Technician", "lab_technician", "tech@example.com")
            self.admin = self._user(db, "Synthetic Admin", "admin", "admin@example.com")
            organization = models.HealthcareOrganization(
                legal_name="Synthetic Hospital", display_name="Synthetic Hospital",
                organization_type="HOSPITAL", administrative_contact_name="Admin",
                administrative_contact_email="hospital@example.test", status="APPROVED",
                legacy_user_id=self.lab.id,
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
            db.add(models.LaboratoryMembership(
                laboratory_id=self.lab.id,
                technician_id=self.technician.id,
                created_by=self.admin.id,
            ))
            db.add(models.Consent(
                patient_id=self.patient.id,
                grantee_id=self.doctor.id,
                organization_id=organization.id,
                resource_types=["MedicationRequest", "DiagnosticReport", "ServiceRequest", "Observation", "Specimen", "Document"],
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
            "lab": self._headers(self.lab.id),
            "technician": self._headers(self.technician.id),
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

    def test_complete_clinical_journey_across_existing_workflows(self):
        order = self.client.post(
            "/fhir/ServiceRequest",
            headers={**self.headers["doctor"], "Idempotency-Key": "m10-acceptance-order-1"},
            json={
                "patient_email": self.patient.email,
                "lab_email": self.lab.email,
                "test_code": "24323-8",
                "test_display": "Synthetic comprehensive metabolic panel",
                "note": "Synthetic acceptance journey",
            },
        )
        self.assertEqual(order.status_code, 200, order.text)
        service_request_id = order.json()["id"]

        accepted = self.client.post(
            f"/fhir/ServiceRequest/{service_request_id}/accept",
            headers=self.headers["lab"],
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)

        assigned = self.client.post(
            f"/fhir/ServiceRequest/{service_request_id}/assign",
            headers=self.headers["lab"],
            json={"technician_email": self.technician.email},
        )
        self.assertEqual(assigned.status_code, 200, assigned.text)

        specimen = self.client.post(
            f"/fhir/ServiceRequest/{service_request_id}/specimen",
            headers=self.headers["technician"],
            json={"type_code": "122555007", "type_display": "Venous blood specimen"},
        )
        self.assertEqual(specimen.status_code, 200, specimen.text)

        processing = self.client.post(
            f"/fhir/ServiceRequest/{service_request_id}/processing",
            headers=self.headers["technician"],
        )
        self.assertEqual(processing.status_code, 200, processing.text)

        results = self.client.post(
            "/fhir/DiagnosticReport",
            headers=self.headers["technician"],
            json={
                "service_request_id": service_request_id,
                "observations": [{
                    "code": "2345-7",
                    "display": "Synthetic glucose",
                    "value": 101.5,
                    "unit": "mg/dL",
                }],
                "conclusion": "Synthetic preliminary result",
            },
        )
        self.assertEqual(results.status_code, 200, results.text)
        report_id = results.json()["id"]

        finalized = self.client.post(
            f"/fhir/ServiceRequest/{service_request_id}/finalize",
            headers=self.headers["lab"],
        )
        self.assertEqual(finalized.status_code, 200, finalized.text)

        review = self.client.post("/api/v1/clinical-reviews", headers=self.headers["doctor"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "diagnostic_report_id": report_id,
            "service_request_id": service_request_id,
            "status": "REVIEWED",
            "clinical_note": "Synthetic physician review",
        })
        self.assertEqual(review.status_code, 201, review.text)

        prescription = self.client.post("/api/v1/prescriptions", headers=self.headers["doctor"], json={
            "patient_id": self.patient.id,
            "organization_id": self.organization_id,
            "medication_name": "Synthetic Acceptance Medication",
            "dosage": "1 synthetic unit",
            "route": "oral",
            "frequency": "once daily",
            "duration": "7 days",
            "quantity": "7 units",
            "instructions": "Synthetic test instructions",
            "activate": True,
        })
        self.assertEqual(prescription.status_code, 201, prescription.text)

        patient_history = self.client.get("/api/v1/prescriptions/me/patient", headers=self.headers["patient"])
        self.assertEqual(patient_history.status_code, 200)
        self.assertEqual(len(patient_history.json()), 1)

        patient_orders = self.client.get("/fhir/ServiceRequest", headers=self.headers["patient"])
        self.assertEqual(patient_orders.status_code, 200)
        self.assertEqual(len(patient_orders.json()), 1)

        patient_reports = self.client.get("/fhir/DiagnosticReport", headers=self.headers["patient"])
        self.assertEqual(patient_reports.status_code, 200)
        self.assertEqual(len(patient_reports.json()), 1)

        with self.session_factory() as db:
            self.assertGreaterEqual(db.query(models.FHIRSyncOutbox).count(), 5)
            self.assertGreaterEqual(db.query(models.AuditLog).count(), 10)

    def test_finalized_report_amendment_preserves_history_and_rejects_unauthorized_users(self):
        with self.session_factory() as db:
            report = models.FHIRResource(
                resource_type="DiagnosticReport",
                fhir_id="synthetic-amended-report",
                resource_data={
                    "resourceType": "DiagnosticReport",
                    "id": "synthetic-amended-report",
                    "status": "final",
                    "conclusion": "Original synthetic conclusion",
                },
                owner_id=self.patient.id,
                created_by=self.lab.id,
            )
            db.add(report)
            db.flush()
            order = models.FHIRResource(
                resource_type="ServiceRequest",
                fhir_id="synthetic-amended-order",
                resource_data={"resourceType": "ServiceRequest", "id": "synthetic-amended-order", "status": "active"},
                owner_id=self.patient.id,
                created_by=self.doctor.id,
            )
            db.add(order)
            db.flush()
            workflow = models.LaboratoryWorkflow(
                service_request_id=order.id,
                patient_id=self.patient.id,
                physician_id=self.doctor.id,
                laboratory_id=self.lab.id,
                status="FINALIZED",
                report_fhir_id=report.fhir_id,
            )
            db.add(workflow)
            db.commit()

        amended = self.client.post(
            "/fhir/DiagnosticReport/synthetic-amended-report/amend",
            headers=self.headers["lab"],
            json={"conclusion": "Amended synthetic conclusion", "reason": "Synthetic correction required"},
        )
        self.assertEqual(amended.status_code, 200, amended.text)
        self.assertEqual(amended.json()["resource"]["status"], "amended")

        unauthorized = self.client.post(
            "/fhir/DiagnosticReport/synthetic-amended-report/amend",
            headers=self.headers["doctor"],
            json={"conclusion": "Unauthorized conclusion", "reason": "Unauthorized attempt"},
        )
        self.assertIn(unauthorized.status_code, {403, 404})

        with self.session_factory() as db:
            amendment = db.query(models.LaboratoryReportAmendment).one()
            self.assertEqual(amendment.previous_conclusion, "Original synthetic conclusion")
            self.assertEqual(amendment.conclusion, "Amended synthetic conclusion")

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
