import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from auth_utils import create_access_token, hash_password
from main import app


class ClinicalFileApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.environment = patch.dict(os.environ, {
            "FILE_STORAGE_PATH": str(Path(self.temp_dir.name) / "private-files"),
            "FHIR_MODE": "local",
            "FABRIC_ENABLED": "false",
        })
        self.environment.start()
        self.db = self.session_factory()
        self.patient = self._user("File Patient", "patient", "patient@example.test")
        self.doctor = self._user("File Physician", "doctor", "doctor@example.test")
        self.lab = self._user("File Laboratory", "lab", "lab@example.test")
        self.other_lab = self._user("Other Laboratory", "lab", "other-lab@example.test")
        self.technician = self._user("Assigned Technician", "lab_technician", "tech@example.test")
        self.admin = self._user("File Administrator", "admin", "admin@example.test")
        request = models.FHIRResource(
            resource_type="ServiceRequest",
            fhir_id="service-request-1",
            resource_data={"resourceType": "ServiceRequest", "id": "service-request-1"},
            owner_id=self.patient.id,
            created_by=self.doctor.id,
        )
        self.db.add(request)
        self.db.flush()
        self.workflow = models.LaboratoryWorkflow(
            service_request_id=request.id,
            patient_id=self.patient.id,
            physician_id=self.doctor.id,
            laboratory_id=self.lab.id,
            technician_id=self.technician.id,
            status="ASSIGNED",
        )
        self.db.add(self.workflow)
        self.db.commit()
        self.db.close()

        def override_get_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(database.get_db, None)
        self.environment.stop()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _user(self, name, role, email):
        user = models.User(
            full_name=name,
            email=email,
            hashed_password=hash_password("temporary-test-password"),
            role=role,
            fhir_resource_id=models.gen_uuid(),
        )
        self.db.add(user)
        self.db.flush()
        return user

    @staticmethod
    def _headers(user):
        return {"Authorization": f"Bearer {create_access_token({'sub': user.id, 'role': user.role})}"}

    def _upload_patient_file(self, patient, filename="care-plan.txt", content=b"Follow-up next week"):
        return self.client.post(
            "/files",
            headers=self._headers(patient),
            files={"file": (filename, content, "text/plain")},
            data={"category": "clinical-record"},
        )

    def _grant_document_consent(self, patient, doctor):
        consent_db = self.session_factory()
        try:
            consent_db.add(models.Consent(
                patient_id=patient.id,
                grantee_id=doctor.id,
                resource_types=["Document"],
                granted_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=2),
            ))
            consent_db.commit()
        finally:
            consent_db.close()

    def test_file_download_requires_active_document_consent_and_revocation_takes_effect(self):
        uploaded = self._upload_patient_file(self.patient)
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]
        self.assertEqual(uploaded.json()["patient_id"], self.patient.id)

        denied = self.client.get(f"/files/{file_id}/download", headers=self._headers(self.doctor))
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(len(self.client.get("/files", headers=self._headers(self.doctor)).json()), 0)

        self._grant_document_consent(self.patient, self.doctor)
        physician_files = self.client.get("/files", headers=self._headers(self.doctor))
        self.assertEqual([item["id"] for item in physician_files.json()], [file_id])
        download = self.client.get(f"/files/{file_id}/download", headers=self._headers(self.doctor))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.content, b"Follow-up next week")
        self.assertEqual(download.headers["x-content-type-options"], "nosniff")
        self.assertIn("attachment", download.headers["content-disposition"])

        consent_db = self.session_factory()
        try:
            consent_db.query(models.Consent).filter_by(
                patient_id=self.patient.id,
                grantee_id=self.doctor.id,
            ).one().revoked_at = datetime.utcnow()
            consent_db.commit()
        finally:
            consent_db.close()
        revoked = self.client.get(f"/files/{file_id}/download", headers=self._headers(self.doctor))
        self.assertEqual(revoked.status_code, 404)

    def test_expired_document_consent_denies_list_download_and_upload_picker(self):
        uploaded = self._upload_patient_file(self.patient)
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]

        consent_db = self.session_factory()
        try:
            consent_db.add(models.Consent(
                patient_id=self.patient.id,
                grantee_id=self.doctor.id,
                resource_types=["Document"],
                granted_at=datetime.utcnow() - timedelta(days=31),
                expires_at=datetime.utcnow() - timedelta(seconds=1),
            ))
            consent_db.commit()
        finally:
            consent_db.close()

        listed_files = self.client.get("/files", headers=self._headers(self.doctor))
        self.assertEqual(listed_files.status_code, 200)
        self.assertEqual(listed_files.json(), [])

        download = self.client.get(
            f"/files/{file_id}/download",
            headers=self._headers(self.doctor),
        )
        self.assertEqual(download.status_code, 404)

        upload_patients = self.client.get(
            "/files/patients",
            headers=self._headers(self.doctor),
        )
        self.assertEqual(upload_patients.status_code, 200)
        self.assertEqual(upload_patients.json(), [])

    def test_patient_file_listing_uses_bounded_queries_as_file_count_grows(self):
        db = self.session_factory()
        try:
            db.add_all([
                models.ClinicalFile(
                    patient_id=self.patient.id,
                    uploaded_by_id=self.patient.id,
                    filename=f"record-{index}.txt",
                    storage_key=f"record-{index}",
                    media_type="text/plain",
                    category="clinical-record",
                    size_bytes=1,
                    sha256="a" * 64,
                )
                for index in range(20)
            ])
            db.commit()
        finally:
            db.close()

        select_count = 0

        def count_selects(_connection, _cursor, statement, _parameters, _context, _executemany):
            nonlocal select_count
            if statement.lstrip().upper().startswith("SELECT"):
                select_count += 1

        event.listen(self.engine, "before_cursor_execute", count_selects)
        try:
            response = self.client.get("/files", headers=self._headers(self.patient))
        finally:
            event.remove(self.engine, "before_cursor_execute", count_selects)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 20)
        self.assertTrue(all(item["patient_name"] == self.patient.full_name for item in response.json()))
        self.assertTrue(all(item["uploaded_by_name"] == self.patient.full_name for item in response.json()))
        self.assertLessEqual(select_count, 4)

    def test_physician_patient_picker_only_returns_active_document_consent(self):
        self.assertEqual(
            self.client.get("/files/patients", headers=self._headers(self.doctor)).json(),
            [],
        )
        self._grant_document_consent(self.patient, self.doctor)
        response = self.client.get("/files/patients", headers=self._headers(self.doctor))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([patient["id"] for patient in response.json()], [self.patient.id])
        self.assertEqual(
            self.client.get("/files/patients", headers=self._headers(self.admin)).status_code,
            403,
        )

    def test_upload_file_is_persisted_as_fhir_document_reference_and_patient_can_delete(self):
        uploaded = self._upload_patient_file(self.patient)
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        data = uploaded.json()
        self.assertEqual(data["filename"], "care-plan.txt")
        self.assertEqual(data["media_type"], "text/plain")
        self.assertTrue(data["can_delete"])

        db = self.session_factory()
        try:
            resource = db.query(models.FHIRResource).filter_by(
                resource_type="DocumentReference",
                fhir_id=data["id"],
            ).one()
            attachment = resource.resource_data["content"][0]["attachment"]
            self.assertEqual(attachment["contentType"], "text/plain")
            self.assertEqual(attachment["size"], len(b"Follow-up next week"))
            self.assertTrue(attachment["url"].endswith(f"/files/{data['id']}/download"))
        finally:
            db.close()

        deleted = self.client.delete(f"/files/{data['id']}", headers=self._headers(self.patient))
        self.assertEqual(deleted.status_code, 200)
        db = self.session_factory()
        try:
            resource = db.query(models.FHIRResource).filter_by(
                resource_type="DocumentReference",
                fhir_id=data["id"],
            ).one()
            self.assertEqual(resource.resource_data["status"], "entered-in-error")
        finally:
            db.close()
        self.assertEqual(self.client.get("/files", headers=self._headers(self.patient)).json(), [])
        self.assertEqual(
            self.client.get(f"/files/{data['id']}/download", headers=self._headers(self.patient)).status_code,
            404,
        )

    def test_patient_can_remove_physician_uploaded_file(self):
        self._grant_document_consent(self.patient, self.doctor)
        uploaded = self.client.post(
            "/files",
            headers=self._headers(self.doctor),
            files={"file": ("visit-note.txt", b"Care note", "text/plain")},
            data={"patient_id": self.patient.id, "category": "clinical-record"},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]
        patient_files = self.client.get("/files", headers=self._headers(self.patient)).json()
        self.assertTrue(next(item for item in patient_files if item["id"] == file_id)["can_delete"])
        self.assertEqual(
            self.client.delete(f"/files/{file_id}", headers=self._headers(self.patient)).status_code,
            200,
        )

    def test_lab_and_technician_access_is_limited_to_assigned_workflow_files(self):
        uploaded = self.client.post(
            "/files",
            headers=self._headers(self.technician),
            files={"file": ("result.txt", b"Result attachment", "text/plain")},
            data={"service_request_id": self.workflow.service_request_id, "category": "lab-result"},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]
        laboratory_files = self.client.get("/files", headers=self._headers(self.lab))
        technician_files = self.client.get("/files", headers=self._headers(self.technician))
        other_laboratory_files = self.client.get("/files", headers=self._headers(self.other_lab))
        self.assertEqual([item["id"] for item in laboratory_files.json()], [file_id])
        self.assertEqual([item["id"] for item in technician_files.json()], [file_id])
        self.assertEqual(other_laboratory_files.json(), [])
        self.assertEqual(
            self.client.get(f"/files/{file_id}/download", headers=self._headers(self.lab)).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/files/{file_id}/download", headers=self._headers(self.other_lab)).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/files/{file_id}/download", headers=self._headers(self.admin)).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/files/{file_id}", headers=self._headers(self.lab)).status_code,
            403,
        )

    def test_file_validation_rejects_unsupported_mismatched_and_oversized_files(self):
        unsupported = self._upload_patient_file(self.patient, "script.html", b"<script>alert(1)</script>")
        self.assertEqual(unsupported.status_code, 415)

        mismatched = self._upload_patient_file(self.patient, "notes.pdf", b"not a pdf")
        self.assertEqual(mismatched.status_code, 415)

        too_large = self._upload_patient_file(
            self.patient,
            "large.txt",
            b"x" * (10 * 1024 * 1024 + 1),
        )
        self.assertEqual(too_large.status_code, 413)

        self.assertEqual(self.client.get("/files", headers=self._headers(self.admin)).status_code, 403)


if __name__ == "__main__":
    unittest.main()
