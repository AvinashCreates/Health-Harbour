import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from services.fhir_sync import process_fhir_sync, queue_fhir_resource, reconcile_fhir
from services.fhir_server import FHIRIntegrationError
from services import fhir_builder


class FHIRSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = create_engine(f"sqlite:///{Path(self.temp_dir.name) / 'fhir.db'}")
        models.Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.environment = patch.dict(os.environ, {
            "FHIR_MODE": "local",
            "FABRIC_ENABLED": "false",
        })
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_queue_is_stable_and_repeated_payload_does_not_duplicate(self):
        payload = {"resourceType": "Patient", "id": "patient-1", "active": True}
        with self.session_factory() as db:
            first = queue_fhir_resource(db, "Patient", "patient-1", payload)
            db.commit()
            second = queue_fhir_resource(db, "Patient", "patient-1", dict(payload))
            db.commit()
            self.assertEqual(first.id, second.id)
            self.assertEqual(db.query(models.FHIRSyncOutbox).count(), 1)

    def test_local_processing_syncs_mirror_and_repeated_update(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-1", {
                "resourceType": "Patient", "id": "patient-1", "active": True,
            })
            db.commit()
            result = process_fhir_sync(db, 20)
            self.assertEqual(result["synced"], 1)
            event = db.query(models.FHIRSyncOutbox).one()
            self.assertEqual(event.status, "SYNCED")
            mirror = db.query(models.FHIRResource).filter_by(
                resource_type="Patient", fhir_id="patient-1",
            ).one()
            self.assertTrue(mirror.resource_data["active"])

            queue_fhir_resource(db, "Patient", "patient-1", {
                "resourceType": "Patient", "id": "patient-1", "active": False,
            })
            db.commit()
            process_fhir_sync(db, 20)
            db.refresh(mirror)
            self.assertFalse(mirror.resource_data["active"])

    def test_identity_resource_builders_and_practitioner_role_references(self):
        provider = models.HealthcareProvider(
            id="provider-1", professional_name="Dr Synthetic", registration_authority="Council",
            registration_number="SYN-1", qualifications=["Synthetic MD"], specialization="Cardiology",
            status="VERIFIED",
        )
        account = models.User(id="account-1", full_name="Dr Synthetic", email="doctor@example.com", hashed_password="unused", role="doctor")
        organization = models.HealthcareOrganization(
            id="organization-1", legal_name="Synthetic Org", display_name="Synthetic Hospital",
            organization_type="HOSPITAL", administrative_contact_name="Admin",
            administrative_contact_email="admin@example.com", status="APPROVED",
        )
        affiliation = models.OrganizationAffiliation(
            id="affiliation-1", organization_id="organization-1", provider_id="provider-1",
            account_id="account-1", status="ACTIVE", invited_by_id="account-1",
        )
        practitioner = fhir_builder.build_healthcare_practitioner(provider, account)
        org = fhir_builder.build_healthcare_organization(organization)
        role = fhir_builder.build_practitioner_role(affiliation, provider, organization)
        self.assertEqual(practitioner["id"], "provider-1")
        self.assertTrue(practitioner["active"])
        self.assertEqual(org["id"], "organization-1")
        self.assertEqual(role["practitioner"]["reference"], "Practitioner/provider-1")
        self.assertEqual(role["organization"]["reference"], "Organization/organization-1")

    def test_duplicate_worker_execution_does_not_resync_same_event(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-duplicate", {
                "resourceType": "Patient", "id": "patient-duplicate", "active": True,
            })
            db.commit()
            first = process_fhir_sync(db, 20)
            second = process_fhir_sync(db, 20)
            self.assertEqual(first["synced"], 1)
            self.assertEqual(second["processed"], 0)
            self.assertEqual(db.query(models.FHIRResource).filter_by(resource_type="Patient", fhir_id="patient-duplicate").count(), 1)

    def test_worker_crash_after_remote_operation_can_retry_without_duplicate_logic(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-crash-recovery", {
                "resourceType": "Patient", "id": "patient-crash-recovery", "active": True,
            })
            db.commit()
            with patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://127.0.0.1:1/fhir"}):
                with patch("services.fhir_sync.persist_resource", return_value={
                    "resourceType": "Patient", "id": "patient-crash-recovery", "active": True,
                }), patch("services.fhir_sync._store_local_mirror", side_effect=RuntimeError("worker interrupted")):
                    crashed = process_fhir_sync(db, 20)
                event = db.query(models.FHIRSyncOutbox).one()
                self.assertEqual(crashed["failed"], 1)
                self.assertEqual(event.status, "FAILED")
                event.next_attempt_at = datetime.utcnow()
                db.commit()

                with patch("services.fhir_sync.persist_resource", return_value={
                    "resourceType": "Patient", "id": "patient-crash-recovery", "active": True,
                }):
                    recovered = process_fhir_sync(db, 20)
                event = db.query(models.FHIRSyncOutbox).one()
                self.assertEqual(recovered["synced"], 1)
                self.assertEqual(event.status, "SYNCED")

    def test_failed_event_retries_and_permanent_event_not_requeued(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-retry", {
                "resourceType": "Patient", "id": "patient-retry", "active": True,
            })
            db.commit()
            event = db.query(models.FHIRSyncOutbox).one()
            event.status = "FAILED"
            event.attempt_count = 1
            event.next_attempt_at = datetime.utcnow()
            db.commit()

            queue_fhir_resource(db, "Patient", "patient-retry", {
                "resourceType": "Patient", "id": "patient-retry", "active": True,
            })
            db.commit()
            event = db.query(models.FHIRSyncOutbox).one()
            self.assertEqual(event.status, "PENDING")

            event.status = "PERMANENT_FAILED"
            db.commit()
            queue_fhir_resource(db, "Patient", "patient-retry", {
                "resourceType": "Patient", "id": "patient-retry", "active": True,
            })
            db.commit()
            event = db.query(models.FHIRSyncOutbox).one()
            self.assertEqual(event.status, "PERMANENT_FAILED")

    def test_hapi_permanent_error_is_marked_permanent_failed(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-permanent", {
                "resourceType": "Patient", "id": "patient-permanent", "active": True,
            })
            db.commit()
            with patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://127.0.0.1:1/fhir"}):
                with patch("services.fhir_sync.persist_resource", side_effect=FHIRIntegrationError(
                    "invalid resource", status_code=422, operation="resource persistence",
                )):
                    result = process_fhir_sync(db, 20)
            event = db.query(models.FHIRSyncOutbox).one()
            self.assertEqual(result["permanent_failed"], 1)
            self.assertEqual(event.status, "PERMANENT_FAILED")
            self.assertEqual(event.last_error_category, "permanent")

    def test_reconciliation_reports_missing_hapi_resource_and_local_status(self):
        with self.session_factory() as db:
            queue_fhir_resource(db, "Patient", "patient-missing", {
                "resourceType": "Patient", "id": "patient-missing", "active": True,
            })
            db.commit()
            with patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://127.0.0.1:1/fhir"}):
                result = reconcile_fhir(db)
            self.assertIn("pending", result)
            self.assertIsInstance(result["discrepancies"], list)


if __name__ == "__main__":
    unittest.main()
