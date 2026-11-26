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


class HealthcareRegistryApiTests(unittest.TestCase):
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
            self.representative_a = self._user(db, "Hospital A Representative", "patient")
            self.representative_b = self._user(db, "Hospital B Representative", "patient")
            self.provider_user = self._user(db, "Dr Synthetic Provider", "patient")
            self.other_user = self._user(db, "Other User", "patient")
            self.admin = self._user(db, "Platform Admin", "admin")
            self.other_admin = self._user(db, "Other Platform Admin", "admin")
            db.commit()
        self.ids = {
            key: value.id
            for key, value in {
                "representative_a": self.representative_a,
                "representative_b": self.representative_b,
                "provider": self.provider_user,
                "other": self.other_user,
                "admin": self.admin,
                "other_admin": self.other_admin,
            }.items()
        }

        def override_get_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(app)
        self.headers = {
            key: self._headers(user_id)
            for key, user_id in self.ids.items()
        }

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.pop(database.get_db, None)
        self.engine.dispose()
        self.environment.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _user(db, name, role):
        user = models.User(
            full_name=name,
            email=f"{name.lower().replace(' ', '.')}@example.test",
            hashed_password="unused",
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def _headers(user_id):
        token = create_access_token({"sub": user_id, "role": "ignored"})
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _organization_payload(suffix):
        return {
            "legal_name": f"Synthetic Health Network {suffix}",
            "display_name": f"Synthetic Hospital {suffix}",
            "organization_type": "HOSPITAL",
            "registration_authority": "synthetic-authority",
            "registration_identifier": f"hospital-{suffix.lower()}",
            "address": {"city": "Example City", "country": "IN"},
            "contact_email": f"contact-{suffix.lower()}@example.com",
            "contact_phone": "+91-0000000000",
            "administrative_contact_name": f"Representative {suffix}",
            "administrative_contact_email": f"rep-{suffix.lower()}@example.com",
            "evidence_references": [f"synthetic-evidence-{suffix.lower()}"],
        }

    def _submit_and_approve_organization(self, representative, suffix):
        response = self.client.post(
            "/api/v1/organization-applications",
            headers=self.headers[representative],
            json=self._organization_payload(suffix),
        )
        self.assertEqual(response.status_code, 201, response.text)
        application = response.json()
        decision = self.client.post(
            f"/api/v1/admin/organization-applications/{application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "APPROVED", "reason": "Synthetic manual review passed"},
        )
        self.assertEqual(decision.status_code, 200, decision.text)
        return application, decision.json()

    def _submit_provider(self):
        response = self.client.post(
            "/api/v1/provider-applications",
            headers=self.headers["provider"],
            json={
                "professional_name": "Dr Synthetic Provider",
                "registration_authority": "synthetic-medical-council",
                "registration_number": "SYN-REG-1001",
                "qualifications": ["Synthetic MBBS"],
                "specialization": "Internal Medicine",
                "public_profile": "Synthetic profile for registry tests.",
                "public_contact_email": "provider-public@example.com",
                "evidence_references": ["synthetic-provider-evidence-1"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _decide_provider(self, application, decision="APPROVED"):
        return self.client.post(
            f"/api/v1/admin/provider-applications/{application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": decision, "reason": "Synthetic manual verification"},
        )

    def test_pending_entities_are_hidden_and_approval_is_admin_only(self):
        response = self.client.post(
            "/api/v1/organization-applications",
            headers=self.headers["representative_a"],
            json=self._organization_payload("A"),
        )
        self.assertEqual(response.status_code, 201, response.text)
        application = response.json()
        self.assertEqual(application["status"], "PENDING")
        self.assertEqual(
            self.client.get("/api/v1/organizations", headers=self.headers["other"]).json(),
            [],
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/admin/organization-applications",
                headers=self.headers["other"],
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/organization-applications/{application['id']}/decision",
                headers=self.headers["other"],
                json={"decision": "APPROVED", "reason": "not authorized"},
            ).status_code,
            403,
        )
        approved = self.client.post(
            f"/api/v1/admin/organization-applications/{application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "APPROVED", "reason": "Synthetic manual review passed"},
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        directory = self.client.get("/api/v1/organizations", headers=self.headers["other"])
        self.assertEqual(directory.status_code, 200)
        self.assertEqual(directory.json()[0]["display_name"], "Synthetic Hospital A")
        self.assertNotIn("administrative_contact_email", directory.json()[0])
        self.assertNotIn("evidence_references", directory.json()[0])
        history = self.client.get(
            f"/api/v1/admin/organizations/{application['organization_id']}/history",
            headers=self.headers["admin"],
        )
        self.assertEqual([row["decision"] for row in history.json()], ["APPROVED"])

    def test_rejected_organization_can_resubmit_without_creating_a_second_profile(self):
        first = self.client.post(
            "/api/v1/organization-applications",
            headers=self.headers["representative_a"],
            json=self._organization_payload("A"),
        )
        self.assertEqual(first.status_code, 201, first.text)
        first_application = first.json()
        rejected = self.client.post(
            f"/api/v1/admin/organization-applications/{first_application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "REJECTED", "reason": "Synthetic correction required"},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)

        payload = self._organization_payload("A")
        payload["display_name"] = "Synthetic Hospital A Resubmitted"
        resubmitted = self.client.post(
            "/api/v1/organization-applications",
            headers=self.headers["representative_a"],
            json=payload,
        )
        self.assertEqual(resubmitted.status_code, 201, resubmitted.text)
        self.assertNotEqual(resubmitted.json()["id"], first_application["id"])
        self.assertEqual(resubmitted.json()["organization_id"], first_application["organization_id"])
        self.assertEqual(resubmitted.json()["status"], "PENDING")

    def test_provider_verification_and_affiliation_gate_directory_access(self):
        organization, _ = self._submit_and_approve_organization("representative_a", "A")
        provider_application = self._submit_provider()
        provider_id = provider_application["provider_id"]
        self.assertEqual(provider_application["status"], "PENDING")
        self.assertEqual(self.client.get("/api/v1/providers", headers=self.headers["other"]).json(), [])
        unpublished_profile = self.client.get(
            f"/api/v1/providers/{provider_id}",
            headers=self.headers["other"],
        )
        self.assertEqual(unpublished_profile.status_code, 404)

        approved_provider = self._decide_provider(provider_application)
        self.assertEqual(approved_provider.status_code, 200, approved_provider.text)
        candidates = self.client.get(
            f"/api/v1/organizations/{organization['organization_id']}/provider-candidates",
            headers=self.headers["representative_a"],
        )
        self.assertEqual(candidates.status_code, 200, candidates.text)
        self.assertEqual([candidate["id"] for candidate in candidates.json()], [provider_id])
        unauthorized_candidates = self.client.get(
            f"/api/v1/organizations/{organization['organization_id']}/provider-candidates",
            headers=self.headers["other"],
        )
        self.assertEqual(unauthorized_candidates.status_code, 404)
        invite = self.client.post(
            f"/api/v1/organizations/{organization['organization_id']}/affiliations",
            headers=self.headers["representative_a"],
            json={"provider_id": provider_id},
        )
        self.assertEqual(invite.status_code, 201, invite.text)
        affiliation = invite.json()
        self.assertEqual(affiliation["status"], "INVITED")
        accepted = self.client.post(
            f"/api/v1/affiliations/{affiliation['id']}/response",
            headers=self.headers["provider"],
            json={"decision": "ACCEPTED", "reason": "I accept this affiliation"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["status"], "PENDING")
        active = self.client.post(
            f"/api/v1/organizations/{organization['organization_id']}/affiliations/{affiliation['id']}/decision",
            headers=self.headers["representative_a"],
            json={"decision": "APPROVED", "reason": "Affiliation reviewed"},
        )
        self.assertEqual(active.status_code, 200, active.text)
        self.assertEqual(active.json()["status"], "ACTIVE")
        directory = self.client.get("/api/v1/providers", headers=self.headers["other"])
        self.assertEqual(directory.status_code, 200, directory.text)
        self.assertEqual(directory.json()[0]["id"], provider_id)
        self.assertNotIn("evidence_references", directory.json()[0])

    def test_unverified_provider_cannot_activate_and_cross_tenant_admin_is_hidden(self):
        organization_a, _ = self._submit_and_approve_organization("representative_a", "A")
        organization_b, _ = self._submit_and_approve_organization("representative_b", "B")
        provider_application = self._submit_provider()
        provider_id = provider_application["provider_id"]
        unauthorized = self.client.get(
            f"/api/v1/organizations/{organization_b['organization_id']}/affiliations",
            headers=self.headers["representative_a"],
        )
        self.assertEqual(unauthorized.status_code, 404)

        invitation = self.client.post(
            f"/api/v1/organizations/{organization_a['organization_id']}/affiliations",
            headers=self.headers["representative_a"],
            json={"provider_id": provider_id},
        )
        self.assertEqual(invitation.status_code, 201, invitation.text)
        affiliation_id = invitation.json()["id"]
        accepted = self.client.post(
            f"/api/v1/affiliations/{affiliation_id}/response",
            headers=self.headers["provider"],
            json={"decision": "ACCEPTED", "reason": "Synthetic acceptance"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        activation = self.client.post(
            f"/api/v1/organizations/{organization_a['organization_id']}/affiliations/{affiliation_id}/decision",
            headers=self.headers["representative_a"],
            json={"decision": "APPROVED", "reason": "Attempt before verification"},
        )
        self.assertEqual(activation.status_code, 409)
        self.assertEqual(activation.json()["detail"], "Only verified providers can be activated")
        self.assertEqual(self.client.get("/api/v1/providers", headers=self.headers["other"]).json(), [])

    def test_affiliations_are_independent_and_status_is_rechecked(self):
        organization_a, _ = self._submit_and_approve_organization("representative_a", "A")
        organization_b, _ = self._submit_and_approve_organization("representative_b", "B")
        provider_application = self._submit_provider()
        self.assertEqual(self._decide_provider(provider_application).status_code, 200)
        provider_id = provider_application["provider_id"]

        active_affiliations = []
        for org_id, representative in [
            (organization_a["organization_id"], "representative_a"),
            (organization_b["organization_id"], "representative_b"),
        ]:
            invitation = self.client.post(
                f"/api/v1/organizations/{org_id}/affiliations",
                headers=self.headers[representative],
                json={"provider_id": provider_id},
            )
            self.assertEqual(invitation.status_code, 201, invitation.text)
            affiliation_id = invitation.json()["id"]
            accepted = self.client.post(
                f"/api/v1/affiliations/{affiliation_id}/response",
                headers=self.headers["provider"],
                json={"decision": "ACCEPTED", "reason": "Synthetic acceptance"},
            )
            self.assertEqual(accepted.status_code, 200, accepted.text)
            activated = self.client.post(
                f"/api/v1/organizations/{org_id}/affiliations/{affiliation_id}/decision",
                headers=self.headers[representative],
                json={"decision": "APPROVED", "reason": "Synthetic affiliation approval"},
            )
            self.assertEqual(activated.status_code, 200, activated.text)
            active_affiliations.append((org_id, representative, affiliation_id))

        oversight = self.client.get(
            "/api/v1/admin/affiliations",
            headers=self.headers["admin"],
        )
        self.assertEqual(oversight.status_code, 200, oversight.text)
        self.assertEqual(len(oversight.json()), 2)
        self.assertEqual(
            self.client.get(
                "/api/v1/admin/affiliations",
                headers=self.headers["other"],
            ).status_code,
            403,
        )
        self.assertEqual(len(self.client.get("/api/v1/providers", headers=self.headers["other"]).json()), 1)
        first_org, first_representative, first_affiliation = active_affiliations[0]
        suspended = self.client.post(
            f"/api/v1/organizations/{first_org}/affiliations/{first_affiliation}/decision",
            headers=self.headers[first_representative],
            json={"decision": "SUSPENDED", "reason": "Synthetic suspension"},
        )
        self.assertEqual(suspended.status_code, 200, suspended.text)
        self.assertEqual(suspended.json()["status"], "SUSPENDED")
        directory = self.client.get("/api/v1/providers", headers=self.headers["other"])
        self.assertEqual(len(directory.json()), 1)
        self.assertEqual(
            [organization["id"] for organization in directory.json()[0]["organizations"]],
            [active_affiliations[1][0]],
        )
        history = self.client.get(
            f"/api/v1/affiliations/{first_affiliation}/history",
            headers=self.headers["provider"],
        )
        self.assertEqual(
            [row["decision"] for row in history.json()],
            ["SUSPENDED", "ACTIVE", "PENDING", "INVITED"],
        )
        self.assertEqual(
            self.client.get("/api/v1/providers/me/affiliations", headers=self.headers["provider"]).status_code,
            200,
        )

    def test_provider_suspension_and_organization_suspension_remove_directory_entries(self):
        organization, _ = self._submit_and_approve_organization("representative_a", "A")
        application = self._submit_provider()
        self.assertEqual(self._decide_provider(application).status_code, 200)
        invite = self.client.post(
            f"/api/v1/organizations/{organization['organization_id']}/affiliations",
            headers=self.headers["representative_a"],
            json={"provider_id": application["provider_id"]},
        )
        self.assertEqual(invite.status_code, 201)
        affiliation_id = invite.json()["id"]
        self.client.post(
            f"/api/v1/affiliations/{affiliation_id}/response",
            headers=self.headers["provider"],
            json={"decision": "ACCEPTED", "reason": "Synthetic acceptance"},
        )
        self.client.post(
            f"/api/v1/organizations/{organization['organization_id']}/affiliations/{affiliation_id}/decision",
            headers=self.headers["representative_a"],
            json={"decision": "APPROVED", "reason": "Synthetic approval"},
        )
        self.assertEqual(len(self.client.get("/api/v1/providers", headers=self.headers["other"]).json()), 1)

        provider_suspended = self.client.post(
            f"/api/v1/admin/provider-applications/{application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "SUSPENDED", "reason": "Synthetic suspension"},
        )
        self.assertEqual(provider_suspended.status_code, 200, provider_suspended.text)
        self.assertEqual(self.client.get("/api/v1/providers", headers=self.headers["other"]).json(), [])
        provider_reinstated = self.client.post(
            f"/api/v1/admin/provider-applications/{application['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "REINSTATED", "reason": "Synthetic reinstatement"},
        )
        self.assertEqual(provider_reinstated.status_code, 200, provider_reinstated.text)
        self.assertEqual(len(self.client.get("/api/v1/providers", headers=self.headers["other"]).json()), 1)

        org_suspended = self.client.post(
            f"/api/v1/admin/organization-applications/{organization['id']}/decision",
            headers=self.headers["admin"],
            json={"decision": "SUSPENDED", "reason": "Synthetic organization suspension"},
        )
        self.assertEqual(org_suspended.status_code, 200, org_suspended.text)
        self.assertEqual(org_suspended.json()["status"], "SUSPENDED")
        self.assertEqual(self.client.get("/api/v1/providers", headers=self.headers["other"]).json(), [])

    def test_public_and_self_endpoints_do_not_expose_other_applications(self):
        own = self.client.post(
            "/api/v1/organization-applications",
            headers=self.headers["representative_a"],
            json=self._organization_payload("A"),
        )
        self.assertEqual(own.status_code, 201, own.text)
        other_apps = self.client.get(
            "/api/v1/organization-applications/me",
            headers=self.headers["other"],
        )
        self.assertEqual(other_apps.json(), [])
        app_admin = self.client.get(
            "/api/v1/admin/organization-applications",
            headers=self.headers["admin"],
        )
        self.assertEqual(app_admin.status_code, 200)
        self.assertEqual(len(app_admin.json()), 1)
        self.assertEqual(
            app_admin.json()[0]["evidence_references"],
            ["synthetic-evidence-a"],
        )


if __name__ == "__main__":
    unittest.main()
