import base64
import os
import secrets
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import auth_utils
from main import app
import models
from database import get_db
from deps import get_current_user
from services import fhir_builder, ledger, oidc
from services.fhir_server import (
    FHIRIntegrationError,
    persist_resource,
    restore_resource_from_mirror,
)


def _b64url(value: int) -> str:
    encoded = base64.urlsafe_b64encode(
        value.to_bytes((value.bit_length() + 7) // 8, "big")
    ).decode("ascii")
    return encoded.rstrip("=")


class CorsIntegrationTests(unittest.TestCase):
    def test_service_request_preflight_allows_idempotency_key_from_loopback_ip(self):
        cors = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls.__name__ == "CORSMiddleware"
        )
        origin = "http://127.0.0.1:5173"
        self.assertIn(origin, cors.kwargs["allow_origins"])
        with TestClient(app) as client:
            response = client.options(
                "/fhir/servicerequests",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("idempotency-key", response.headers["access-control-allow-headers"].lower())


class OIDCIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_numbers = cls.private_key.public_key().public_numbers()
        cls.jwks = {
            "keys": [{
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "test-key",
                "n": _b64url(public_numbers.n),
                "e": _b64url(public_numbers.e),
            }]
        }
        cls.private_pem = cls.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "KEYCLOAK_ISSUER": "https://identity.example/realms/healthharbor",
            "KEYCLOAK_JWKS_URL": "https://identity.example/realms/healthharbor/protocol/openid-connect/certs",
            "KEYCLOAK_AUDIENCE": "healthcare-exchange-api",
        })
        self.environment.start()
        oidc.reset_jwks_cache()

    def tearDown(self):
        oidc.reset_jwks_cache()
        self.environment.stop()

    def issue_token(self, **overrides):
        claims = {
            "iss": "https://identity.example/realms/healthharbor",
            "aud": "healthcare-exchange-api",
            "sub": "verified-subject",
            "email": "patient@example.test",
            "email_verified": True,
            "name": "Test Patient",
            "realm_access": {"roles": ["PATIENT"]},
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
        claims.update(overrides)
        return jwt.encode(
            claims,
            self.private_pem,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

    @patch("services.oidc._load_jwks")
    def test_verifies_signature_issuer_audience_and_subject(self, load_jwks):
        load_jwks.return_value = self.jwks
        claims = oidc.decode_keycloak_token(self.issue_token())
        self.assertEqual(claims["sub"], "verified-subject")
        self.assertEqual(oidc.map_keycloak_role(claims), "patient")

    @patch("services.oidc._load_jwks")
    def test_rejects_wrong_issuer_and_audience(self, load_jwks):
        load_jwks.return_value = self.jwks
        with self.assertRaises(JWTError):
            oidc.decode_keycloak_token(self.issue_token(iss="https://attacker.example"))
        with self.assertRaises(JWTError):
            oidc.decode_keycloak_token(self.issue_token(aud="different-api"))

    def test_rejects_ambiguous_explicit_realm_roles(self):
        self.assertIsNone(
            oidc.map_keycloak_role({"realm_access": {"roles": ["PATIENT", "PHYSICIAN"]}})
        )
        self.assertEqual(
            oidc.map_keycloak_role({"realm_access": {"roles": ["PHYSICIAN"]}}),
            "doctor",
        )
        self.assertIsNone(oidc.map_keycloak_role({"realm_access": {"roles": "ADMIN"}}))

    @patch("services.oidc._load_jwks")
    def test_rejects_missing_audience(self, load_jwks):
        load_jwks.return_value = self.jwks
        with self.assertRaises(JWTError):
            oidc.decode_keycloak_token(self.issue_token(aud=None))


class LocalTokenSecurityTests(unittest.TestCase):
    def test_local_access_token_requires_expiry_and_nonempty_subject(self):
        missing_expiry = jwt.encode(
            {"sub": "test-subject"},
            auth_utils.SECRET_KEY,
            algorithm="HS256",
        )
        empty_subject = auth_utils.create_access_token({"sub": " "})
        valid = auth_utils.create_access_token({"sub": "test-subject"})

        self.assertIsNone(auth_utils.decode_access_token(missing_expiry))
        self.assertIsNone(auth_utils.decode_access_token(empty_subject))
        self.assertEqual(auth_utils.decode_access_token(valid)["sub"], "test-subject")

    def test_production_rejects_missing_and_known_development_secrets(self):
        for secret in (None, " " * 64, "dev-secret-change-in-production-please",
                       "local-development-secret-change-before-deployment-123456"):
            with self.subTest(secret=secret):
                environment = os.environ.copy()
                environment["APP_ENV"] = "production"
                if secret is None:
                    environment.pop("JWT_SECRET", None)
                else:
                    environment["JWT_SECRET"] = secret
                result = subprocess.run(
                    [sys.executable, "-c", "import auth_utils"],
                    cwd=os.path.dirname(__file__),
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("JWT_SECRET", result.stderr)

    def test_production_accepts_a_unique_long_secret(self):
        environment = os.environ.copy()
        environment["APP_ENV"] = "production"
        environment["JWT_SECRET"] = secrets.token_urlsafe(48)
        result = subprocess.run(
            [sys.executable, "-c", "import auth_utils"],
            cwd=os.path.dirname(__file__),
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class ConsentAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        db = self.session_factory()
        self.patient = models.User(
            id="consent-patient",
            full_name="Synthetic Patient",
            email="consent-patient@example.com",
            hashed_password="unused",
            role="patient",
        )
        self.doctor = models.User(
            id="consent-doctor",
            full_name="Synthetic Physician",
            email="consent-doctor@example.com",
            hashed_password="unused",
            role="doctor",
        )
        self.laboratory = models.User(
            id="consent-lab",
            full_name="Synthetic Laboratory",
            email="consent-lab@example.com",
            hashed_password="unused",
            role="lab",
        )
        db.add_all([self.patient, self.doctor, self.laboratory])
        db.flush()
        patient_resource = models.FHIRResource(
            id="consent-patient-resource",
            resource_type="Patient",
            fhir_id=self.patient.id,
            resource_data={"resourceType": "Patient", "id": self.patient.id},
            owner_id=self.patient.id,
            created_by=self.patient.id,
        )
        request = models.FHIRResource(
            id="consent-request-resource",
            resource_type="ServiceRequest",
            fhir_id="expired-request",
            resource_data={
                "resourceType": "ServiceRequest",
                "id": "expired-request",
                "subject": {"reference": f"Patient/{self.patient.id}"},
            },
            owner_id=self.patient.id,
            created_by=self.doctor.id,
        )
        db.add_all([patient_resource, request])
        db.flush()
        db.add_all([
            models.Consent(
                patient_id=self.patient.id,
                grantee_id=self.doctor.id,
                resource_types=["Patient", "ServiceRequest"],
                granted_at=datetime.utcnow() - timedelta(days=31),
                expires_at=datetime.utcnow() - timedelta(seconds=1),
            ),
            models.LaboratoryWorkflow(
                service_request_id=request.id,
                patient_id=self.patient.id,
                physician_id=self.doctor.id,
                laboratory_id=self.laboratory.id,
                status="REQUESTED",
            ),
        ])
        db.commit()
        db.close()

        self.previous_overrides = app.dependency_overrides.copy()

        def override_db():
            session = self.session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.doctor
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        self.engine.dispose()

    def test_expired_consent_denies_patient_reads_and_service_request_access(self):
        patient_response = self.client.get(f"/fhir/Patient/{self.patient.id}")
        self.assertEqual(patient_response.status_code, 403)

        request_list = self.client.get("/fhir/ServiceRequest")
        self.assertEqual(request_list.status_code, 200, request_list.text)
        self.assertEqual(request_list.json(), [])

        create_request = self.client.post(
            "/fhir/ServiceRequest",
            headers={"Idempotency-Key": "expired-consent-request"},
            json={
                "patient_email": self.patient.email,
                "lab_email": self.laboratory.email,
            },
        )
        self.assertEqual(create_request.status_code, 403, create_request.text)


class FHIRIntegrationTests(unittest.TestCase):
    def test_consent_builder_uses_r4_codeable_concept_for_scopes(self):
        start = datetime(2030, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=30)
        resource = fhir_builder.build_consent(
            "consent-id", "patient-id", "practitioner-id",
            ["Patient", "DiagnosticReport"], start, end,
        )
        self.assertEqual(resource["resourceType"], "Consent")
        self.assertEqual(resource["status"], "active")
        self.assertEqual(
            [entry["coding"][0]["code"] for entry in resource["provision"]["code"]],
            ["Patient", "DiagnosticReport"],
        )
        self.assertNotIn("data", resource["provision"])

    @patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://hapi/fhir"})
    @patch("services.fhir_server._client")
    def test_persists_validated_r4_resource_and_returns_server_version(self, client_factory):
        import httpx
        from unittest.mock import MagicMock

        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = httpx.Response(200, json={"resourceType": "Patient", "id": "p1"})
        client.post.return_value = httpx.Response(200, json={
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "information", "code": "informational"}],
        })
        server_resource = {"resourceType": "ServiceRequest", "id": "sr1", "meta": {"versionId": "2"}}
        client.put.return_value = httpx.Response(200, json=server_resource)
        client_factory.return_value = client

        result = persist_resource({
            "resourceType": "ServiceRequest",
            "id": "sr1",
            "subject": {"reference": "Patient/p1"},
            "meta": {"versionId": "1"},
        })

        self.assertEqual(result["meta"]["versionId"], "2")
        self.assertEqual(client.post.call_args.args[0], "http://hapi/fhir/ServiceRequest/$validate")
        self.assertEqual(client.put.call_args.kwargs["headers"]["If-Match"], 'W/"1"')

    @patch.dict(os.environ, {"FHIR_MODE": "invalid"})
    def test_rejects_unknown_mode_instead_of_falling_back(self):
        with self.assertRaises(FHIRIntegrationError):
            persist_resource({"resourceType": "Patient", "id": "p1"})

    @patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://hapi/fhir"})
    @patch("services.fhir_server.persist_resource")
    @patch("services.fhir_server.retrieve_resource", return_value=None)
    def test_restores_missing_resource_dependencies_before_request(self, retrieve, persist):
        patient = {"resourceType": "Patient", "id": "p1", "meta": {"versionId": "4"}}
        service_request = {
            "resourceType": "ServiceRequest",
            "id": "sr1",
            "subject": {"reference": "Patient/p1"},
            "meta": {"versionId": "7", "lastUpdated": "2030-01-01T00:00:00Z"},
        }
        persisted = []

        def persist_mirror(resource):
            persisted.append(resource)
            return resource

        persist.side_effect = persist_mirror
        result = restore_resource_from_mirror(
            "ServiceRequest",
            "sr1",
            service_request,
            lambda resource_type, resource_id: (
                patient if (resource_type, resource_id) == ("Patient", "p1") else None
            ),
        )

        self.assertEqual([resource["resourceType"] for resource in persisted], ["Patient", "ServiceRequest"])
        self.assertNotIn("versionId", persisted[0]["meta"])
        self.assertNotIn("versionId", persisted[1]["meta"])
        self.assertNotIn("lastUpdated", persisted[1]["meta"])
        self.assertEqual(result["id"], "sr1")
        self.assertGreaterEqual(retrieve.call_count, 3)

    @patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://hapi/fhir"})
    @patch("services.fhir_server.persist_resource")
    @patch("services.fhir_server.retrieve_resource", return_value=None)
    def test_reports_missing_local_reference_when_resource_cannot_be_restored(self, _, persist):
        service_request = {
            "resourceType": "ServiceRequest",
            "id": "sr1",
            "subject": {"reference": "Patient/p1"},
        }

        with self.assertRaisesRegex(FHIRIntegrationError, "Patient/p1 is missing from the local mirror"):
            restore_resource_from_mirror("ServiceRequest", "sr1", service_request, lambda *_: None)

        persist.assert_not_called()

    @patch.dict(os.environ, {"FHIR_MODE": "hapi", "FHIR_SERVER_URL": "http://hapi/fhir"})
    @patch("services.fhir_server.persist_resource", side_effect=lambda resource: resource)
    @patch("services.fhir_server.retrieve_resource", return_value=None)
    def test_service_request_list_recovers_missing_hapi_resource(self, _, persist):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        models.Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine)
        db = session_factory()
        patient = models.User(
            id="patient-local", full_name="Test Patient", email="patient@example.test",
            hashed_password="unused", role="patient",
        )
        doctor = models.User(
            id="doctor-local", full_name="Test Doctor", email="doctor@example.test",
            hashed_password="unused", role="doctor",
        )
        laboratory = models.User(
            id="lab-local", full_name="Test Laboratory", email="lab@example.test",
            hashed_password="unused", role="lab",
        )
        db.add_all([patient, doctor, laboratory])
        db.flush()
        resources = [
            ("Patient", "patient-fhir", {"resourceType": "Patient", "id": "patient-fhir"}),
            ("Practitioner", "doctor-fhir", {"resourceType": "Practitioner", "id": "doctor-fhir"}),
            ("Organization", "lab-fhir", {"resourceType": "Organization", "id": "lab-fhir"}),
        ]
        for resource_type, fhir_id, data in resources:
            db.add(models.FHIRResource(
                resource_type=resource_type,
                fhir_id=fhir_id,
                resource_data=data,
                owner_id=patient.id if resource_type == "Patient" else None,
                created_by=doctor.id,
            ))
        request = models.FHIRResource(
            id="request-local",
            resource_type="ServiceRequest",
            fhir_id="request-fhir",
            resource_data={
                "resourceType": "ServiceRequest",
                "id": "request-fhir",
                "status": "active",
                "intent": "order",
                "code": {"text": "CBC"},
                "subject": {"reference": "Patient/patient-fhir"},
                "requester": {"reference": "Practitioner/doctor-fhir"},
                "performer": [{"reference": "Organization/lab-fhir"}],
            },
            owner_id=patient.id,
            created_by=doctor.id,
        )
        db.add(request)
        db.flush()
        db.add(models.LaboratoryWorkflow(
            service_request_id=request.id,
            patient_id=patient.id,
            physician_id=doctor.id,
            laboratory_id=laboratory.id,
            status="REQUESTED",
        ))
        db.commit()
        previous_overrides = app.dependency_overrides.copy()

        def override_db():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: laboratory
        try:
            with TestClient(app) as client:
                response = client.get("/fhir/ServiceRequest")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()[0]["resource"]["id"], "request-fhir")
            self.assertCountEqual(
                [call.args[0]["resourceType"] for call in persist.call_args_list],
                ["Patient", "Practitioner", "Organization", "ServiceRequest"],
            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
            db.close()
            engine.dispose()


class FabricOutboxTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database.Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.environment = patch.dict(os.environ, {
            "FABRIC_ENABLED": "true",
            "FABRIC_GATEWAY_URL": "http://fabric-gateway:8081",
            "FABRIC_GATEWAY_TOKEN": "test-gateway-token-with-at-least-32-bytes",
            "FABRIC_PSEUDONYM_KEY": "test-pseudonym-key-with-at-least-32-bytes",
        })
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.engine.dispose()

    def test_outbox_ignores_event_types_outside_backend_allowlist(self):
        db = self.session_factory()
        try:
            ledger.queue_ledger_event(
                db,
                "actor-internal-id",
                "UNREVIEWED_EVENT",
                {"patient_id": "patient-internal-id"},
                datetime(2030, 1, 1),
            )
            db.commit()
            self.assertEqual(db.query(models.LedgerOutbox).count(), 0)
        finally:
            db.close()

    def test_outbox_excludes_identifiers_and_tracks_confirmed_commit(self):
        db = self.session_factory()
        try:
            ledger.queue_ledger_event(
                db,
                "actor-internal-id",
                "DATA_ACCESSED",
                {
                    "patient_id": "patient-internal-id",
                    "resource_id": "fhir-resource-internal-id",
                    "resource_type": "DiagnosticReport",
                },
                datetime(2030, 1, 1),
            )
            db.commit()
            event = db.query(models.LedgerOutbox).one()
            serialized_event = str(event.event_payload)
            self.assertNotIn("patient-internal-id", serialized_event)
            self.assertNotIn("fhir-resource-internal-id", serialized_event)
            self.assertEqual(set(event.event_payload), {
                "eventId",
                "eventType",
                "actorRef",
                "subjectRef",
                "resourceRef",
                "resourceType",
                "occurredAt",
                "payloadHash",
            })
            self.assertEqual(event.status, "PENDING")

            response = MagicMock()
            response.json.return_value = {"transactionId": "confirmed-tx-1"}
            with patch.object(database, "SessionLocal", self.session_factory), \
                    patch("httpx.post", return_value=response):
                self.assertEqual(ledger.process_pending_events(), 1)

            db.refresh(event)
            self.assertEqual(event.status, "COMMITTED")
            self.assertEqual(event.transaction_id, "confirmed-tx-1")
            self.assertIsNotNone(event.committed_at)
        finally:
            db.close()

    @patch.dict(os.environ, {"AUTH_PROVIDER": "keycloak", "FHIR_MODE": "local"})
    @patch("routers.auth.verify_keycloak_claims")
    def test_keycloak_self_provisioning_requires_verified_patient_claims(self, verify_claims):
        from fastapi import HTTPException
        from routers.auth import provision_oidc_patient

        db = self.session_factory()
        try:
            verify_claims.return_value = {
                "sub": "new-patient-subject",
                "email": "new.patient@example.com",
                "email_verified": True,
                "name": "New Patient",
                "realm_access": {"roles": ["PATIENT"]},
            }
            profile = provision_oidc_patient(token="signed-token", db=db)
            self.assertEqual(profile.role, "patient")
            self.assertEqual(profile.identity_subject, "new-patient-subject")

            verify_claims.return_value = {
                "sub": "different-subject",
                "email": "new.patient@example.com",
                "email_verified": True,
                "name": "Another Patient",
                "realm_access": {"roles": ["PATIENT"]},
            }
            with self.assertRaises(HTTPException) as duplicate_email:
                provision_oidc_patient(token="signed-token", db=db)
            self.assertEqual(duplicate_email.exception.status_code, 409)

            verify_claims.return_value = {
                "sub": "unverified-subject",
                "email": "unverified@example.com",
                "email_verified": False,
                "name": "Unverified Person",
                "realm_access": {"roles": ["PATIENT"]},
            }
            with self.assertRaises(HTTPException) as unverified:
                provision_oidc_patient(token="signed-token", db=db)
            self.assertEqual(unverified.exception.status_code, 422)

            verify_claims.return_value = {
                "sub": "administrator-subject",
                "email": "admin@example.test",
                "email_verified": True,
                "name": "Administrator",
                "realm_access": {"roles": ["ADMIN"]},
            }
            with self.assertRaises(HTTPException) as non_patient:
                provision_oidc_patient(token="signed-token", db=db)
            self.assertEqual(non_patient.exception.status_code, 403)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
