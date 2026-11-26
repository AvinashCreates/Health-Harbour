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


class OrganizationConsentTests(unittest.TestCase):
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
        db = self.session_factory()
        self.patient = self._user(db, "Patient", "patient", "patient@example.com")
        self.doctor = self._user(db, "Physician", "doctor", "doctor@example.com")
        self.organization = self._user(db, "Organization", "lab", "organization@example.com")
        self.other_organization = self._user(db, "Other Organization", "lab", "other@example.com")
        self.admin = self._user(db, "Administrator", "admin", "admin@example.com")
        registry_organization = models.HealthcareOrganization(
            legal_name="Synthetic Registry Organization",
            display_name="Synthetic Registry Organization",
            organization_type="HOSPITAL",
            administrative_contact_name="Synthetic Administrator",
            administrative_contact_email="registry@example.com",
            status="APPROVED",
        )
        db.add(registry_organization)
        provider = models.HealthcareProvider(
            account_id=self.doctor.id,
            professional_name=self.doctor.full_name,
            registration_authority="synthetic-test-authority",
            registration_number=f"TEST-{self.doctor.id}",
            qualifications=["Synthetic test qualification"],
            status="VERIFIED",
        )
        db.add(provider)
        db.flush()
        db.add(models.OrganizationAffiliation(
            organization_id=registry_organization.id,
            provider_id=provider.id,
            account_id=self.doctor.id,
            organization_role="PROVIDER",
            status="ACTIVE",
            invited_by_id=self.admin.id,
            effective_from=datetime.utcnow(),
        ))
        db.add(models.FHIRResource(
            resource_type="Patient",
            fhir_id=self.patient.fhir_resource_id,
            resource_data={
                "resourceType": "Patient",
                "id": self.patient.fhir_resource_id,
                "active": True,
            },
            owner_id=self.patient.id,
            created_by=self.patient.id,
        ))
        db.commit()
        self.ids = {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "organization": self.organization.id,
            "other_organization": self.other_organization.id,
            "admin": self.admin.id,
        }
        db.close()

        def override_get_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(app)
        self.patient_headers = self._headers(self.ids["patient"], "patient")
        self.doctor_headers = self._headers(self.ids["doctor"], "doctor")
        self.admin_headers = self._headers(self.ids["admin"], "admin")

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(database.get_db, None)
        self.engine.dispose()
        self.environment.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _user(db, name, role, email):
        user = models.User(
            full_name=name,
            email=email,
            hashed_password="unused",
            role=role,
            fhir_resource_id=models.gen_uuid(),
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def _headers(user_id, role):
        token = create_access_token({"sub": user_id, "role": role})
        return {"Authorization": f"Bearer {token}"}

    def _add_practitioner(self, organization_email="organization@example.com"):
        return self.client.post(
            "/auth/organization-memberships",
            headers=self.admin_headers,
            json={
                "organization_email": organization_email,
                "practitioner_email": "doctor@example.com",
            },
        )

    def test_named_organization_consent_is_scoped_and_membership_removal_revokes_access(self):
        self.assertEqual(self._add_practitioner().status_code, 200)

        available = self.client.get("/consent/organizations", headers=self.patient_headers)
        self.assertEqual(available.status_code, 200, available.text)
        self.assertEqual([item["id"] for item in available.json()], [self.ids["organization"]])
        self.assertEqual(available.json()[0]["practitioners"][0]["id"], self.ids["doctor"])

        grant = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Patient"],
                "duration_days": 7,
            },
        )
        self.assertEqual(grant.status_code, 200, grant.text)
        self.assertEqual(grant.json()["organization_id"], self.ids["organization"])
        self.assertEqual(grant.json()["purpose"], "TREATMENT")

        patient_read = self.client.get(
            f"/fhir/Patient/{self.ids['patient']}",
            headers=self.doctor_headers,
        )
        self.assertEqual(patient_read.status_code, 200, patient_read.text)

        request = self.client.post(
            "/fhir/ServiceRequest",
            headers={**self.doctor_headers, "Idempotency-Key": "scope-mismatch-001"},
            json={
                "patient_email": "patient@example.com",
                "lab_email": "organization@example.com",
                "test_display": "Synthetic test",
            },
        )
        self.assertEqual(request.status_code, 403, request.text)

        memberships = self.client.get(
            "/auth/organization-memberships",
            headers=self.admin_headers,
        )
        membership_id = memberships.json()[0]["id"]
        removed = self.client.delete(
            f"/auth/organization-memberships/{membership_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(removed.status_code, 204, removed.text)

        denied = self.client.get(
            f"/fhir/Patient/{self.ids['patient']}",
            headers=self.doctor_headers,
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        consents = self.client.get("/consent/active", headers=self.patient_headers)
        self.assertFalse(consents.json()[0]["is_active"])

        reactivated = self._add_practitioner()
        self.assertEqual(reactivated.status_code, 200, reactivated.text)
        still_denied = self.client.get(
            f"/fhir/Patient/{self.ids['patient']}",
            headers=self.doctor_headers,
        )
        self.assertEqual(still_denied.status_code, 403, still_denied.text)

        renewed = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Patient"],
            },
        )
        self.assertEqual(renewed.status_code, 200, renewed.text)
        restored = self.client.get(
            f"/fhir/Patient/{self.ids['patient']}",
            headers=self.doctor_headers,
        )
        self.assertEqual(restored.status_code, 200, restored.text)

    def test_patient_cannot_grant_organization_access_to_a_nonmember(self):
        response = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Patient"],
            },
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_only_administrators_can_manage_organization_memberships(self):
        response = self.client.post(
            "/auth/organization-memberships",
            headers=self.doctor_headers,
            json={
                "organization_email": "organization@example.com",
                "practitioner_email": "doctor@example.com",
            },
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_membership_for_another_organization_does_not_authorize_grant(self):
        self.assertEqual(
            self._add_practitioner(organization_email="other@example.com").status_code,
            200,
        )
        response = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Patient"],
            },
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_organization_document_consent_stops_after_membership_removal(self):
        uploaded = self.client.post(
            "/files",
            headers=self.patient_headers,
            files={"file": ("record.txt", b"Synthetic record", "text/plain")},
            data={"category": "clinical-record"},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]
        self.assertEqual(self._add_practitioner().status_code, 200)

        grant = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Document"],
            },
        )
        self.assertEqual(grant.status_code, 200, grant.text)
        allowed = self.client.get(
            f"/files/{file_id}/download",
            headers=self.doctor_headers,
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.content, b"Synthetic record")

        membership = self.client.get(
            "/auth/organization-memberships",
            headers=self.admin_headers,
        ).json()[0]
        self.client.delete(
            f"/auth/organization-memberships/{membership['id']}",
            headers=self.admin_headers,
        )
        denied = self.client.get(
            f"/files/{file_id}/download",
            headers=self.doctor_headers,
        )
        self.assertEqual(denied.status_code, 404)

    def test_organization_consent_purpose_is_limited_to_treatment(self):
        response = self.client.post(
            "/consent/grant",
            headers=self.patient_headers,
            json={
                "doctor_email": "doctor@example.com",
                "organization_id": self.ids["organization"],
                "resource_types": ["Patient"],
                "purpose": "OPERATIONS",
            },
        )
        self.assertEqual(response.status_code, 422, response.text)

        db = self.session_factory()
        db.add(models.OrganizationMembership(
            organization_id=self.ids["organization"],
            practitioner_id=self.ids["doctor"],
            created_by=self.ids["admin"],
        ))
        db.add(models.Consent(
            patient_id=self.ids["patient"],
            grantee_id=self.ids["doctor"],
            organization_id=self.ids["organization"],
            purpose="OPERATIONS",
            resource_types=["Patient"],
            granted_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=1),
        ))
        db.commit()
        db.close()
        denied = self.client.get(
            f"/fhir/Patient/{self.ids['patient']}",
            headers=self.doctor_headers,
        )
        self.assertEqual(denied.status_code, 403, denied.text)
