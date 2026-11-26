"""Automated smoke test for the whole backend, run in-process (no server
needed) via FastAPI's TestClient. Exercises: registration, login, the
consent-gating rule (the core feature), the ServiceRequest -> DiagnosticReport
lab workflow, and audit-chain tamper detection.

Run with: DATABASE_URL=sqlite:///./test.db python test_api.py
"""
import sys

from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
import models
from auth_utils import create_access_token, hash_password

client = TestClient(app)
failures = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def provision_test_user(full_name, email, role):
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        user = models.User(full_name=full_name, email=email, hashed_password=hash_password("TestPassword@123"), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    result = {
        "access_token": create_access_token({"sub": user.id, "role": user.role}),
        "user": {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role},
    }
    db.close()
    return result


def add_lab_membership(lab_id, technician_id, actor_id):
    db = SessionLocal()
    db.add(models.LaboratoryMembership(
        laboratory_id=lab_id,
        technician_id=technician_id,
        created_by=actor_id,
    ))
    db.commit()
    db.close()


def add_registry_eligibility(doctor_ids, laboratory_ids):
    db = SessionLocal()
    try:
        organization = models.HealthcareOrganization(
            legal_name="Synthetic Test Hospital",
            display_name="Synthetic Test Hospital",
            organization_type="HOSPITAL",
            administrative_contact_name="Synthetic Administrator",
            administrative_contact_email="registry@example.test",
            status="APPROVED",
        )
        db.add(organization)
        for laboratory_id in laboratory_ids:
            laboratory = db.query(models.User).filter(
                models.User.id == laboratory_id,
            ).one()
            db.add(models.HealthcareOrganization(
                legacy_user_id=laboratory.id,
                legal_name=f"Synthetic {laboratory.full_name}",
                display_name=laboratory.full_name,
                organization_type="DIAGNOSTIC_LABORATORY",
                administrative_contact_name="Synthetic Administrator",
                administrative_contact_email="registry@example.test",
                status="APPROVED",
            ))
        db.flush()
        for doctor_id in doctor_ids:
            doctor = db.query(models.User).filter(models.User.id == doctor_id).one()
            provider = models.HealthcareProvider(
                account_id=doctor.id,
                professional_name=doctor.full_name,
                registration_authority="synthetic-test-authority",
                registration_number=f"TEST-{doctor.id}",
                qualifications=["Synthetic test qualification"],
                status="VERIFIED",
            )
            db.add(provider)
            db.flush()
            db.add(models.OrganizationAffiliation(
                organization_id=organization.id,
                provider_id=provider.id,
                account_id=doctor.id,
                organization_role="PROVIDER",
                status="ACTIVE",
                invited_by_id=doctor_id,
            ))
        db.commit()
    finally:
        db.close()


# 1. Register four roles
r = client.post("/auth/register", json={"full_name": "Test Patient", "email": "qa.patient@example.com", "password": "TestPassword@123"})
check("register patient -> 200", r.status_code == 200)
patient = r.json()

doctorA = provision_test_user("Test Doctor A", "qa.doctorA@example.com", "doctor")

doctorB = provision_test_user("Test Doctor B", "qa.doctorB@example.com", "doctor")

lab = provision_test_user("Test Lab", "qa.lab@example.com", "lab")
other_lab = provision_test_user("Other Lab", "qa.otherlab@example.com", "lab")
technician = provision_test_user("Test Technician", "qa.technician@example.com", "lab_technician")
unaffiliated_technician = provision_test_user("Unassigned Technician", "qa.unassigned@example.com", "lab_technician")
admin = provision_test_user("Test Admin", "qa.admin@example.com", "admin")
add_lab_membership(lab["user"]["id"], technician["user"]["id"], admin["user"]["id"])
add_registry_eligibility(
    [doctorA["user"]["id"], doctorB["user"]["id"]],
    [lab["user"]["id"], other_lab["user"]["id"]],
)

# 2. Duplicate email rejected
r = client.post("/auth/register", json={"full_name": "Dup", "email": "qa.patient@example.com", "password": "TestPassword@123"})
check("duplicate email -> 400", r.status_code == 400)

# 3. Wrong password rejected
r = client.post("/auth/login", json={"email": "qa.patient@example.com", "password": "WrongPassword"})
check("wrong password -> 401", r.status_code == 401)

patient_token = patient["access_token"]
doctorA_token = doctorA["access_token"]
doctorB_token = doctorB["access_token"]
lab_token = lab["access_token"]
admin_token = admin["access_token"]
patient_id = patient["user"]["id"]

# 4. Before any consent, doctorA cannot see the patient resource
r = client.get(f"/fhir/Patient/{patient_id}", headers=auth_headers(doctorA_token))
check("no consent yet -> doctor GET Patient = 403", r.status_code == 403)

# 5. Patient grants consent to doctorA only
r = client.post("/consent/grant", json={"doctor_email": "qa.doctorA@example.com", "duration_days": 30}, headers=auth_headers(patient_token))
check("grant consent -> 200", r.status_code == 200)
consent_id = r.json()["id"]
check("consent is_active True", r.json()["is_active"] is True)

# Consent inputs are bounded and use supported FHIR resource types only.
r = client.post("/consent/grant", json={
    "doctor_email": "qa.doctorA@example.com", "duration_days": 31,
}, headers=auth_headers(patient_token))
check("consent duration over 30 days -> 422", r.status_code == 422)

r = client.post("/consent/grant", json={
    "doctor_email": "qa.doctorA@example.com", "resource_types": ["UnsupportedResource"],
}, headers=auth_headers(patient_token))
check("unsupported consent resource type -> 422", r.status_code == 422)

# A grant for Patient alone must not disclose laboratory resources.
r = client.post("/consent/grant", json={
    "doctor_email": "qa.doctorB@example.com", "resource_types": ["Patient"],
    "duration_days": 30,
}, headers=auth_headers(patient_token))
check("grant Patient-only consent -> 200", r.status_code == 200)

# 6. doctorA (consented) can now see patient; doctorB (not consented) cannot
r = client.get(f"/fhir/Patient/{patient_id}", headers=auth_headers(doctorA_token))
check("consented doctor GET Patient -> 200", r.status_code == 200)

r = client.get(f"/fhir/Patient/{patient_id}", headers=auth_headers(doctorB_token))
check("Patient-only doctor GET Patient -> 200", r.status_code == 200)

# 7. doctorA creates a ServiceRequest; doctorB (no consent) is blocked from doing the same
r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "qa.patient@example.com",
    "lab_email": "qa.lab@example.com",
    "test_display": "Complete blood count",
}, headers={**auth_headers(doctorA_token), "Idempotency-Key": "qa-service-request-001"})
check("consented doctor creates ServiceRequest -> 200", r.status_code == 200)
service_request_id = r.json()["id"]

r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "qa.patient@example.com",
    "lab_email": "qa.lab@example.com",
    "test_display": "Complete blood count",
}, headers={**auth_headers(doctorA_token), "Idempotency-Key": "qa-service-request-001"})
check("retry with same Idempotency-Key returns the same request", r.status_code == 200 and r.json()["id"] == service_request_id)

r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "qa.patient@example.com",
    "lab_email": "qa.lab@example.com",
    "test_display": "Different test",
}, headers={**auth_headers(doctorA_token), "Idempotency-Key": "qa-service-request-001"})
check("reusing Idempotency-Key for a different request -> 409", r.status_code == 409)

r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "qa.patient@example.com",
    "lab_email": "qa.lab@example.com",
    "test_display": "Complete blood count",
}, headers={**auth_headers(doctorB_token), "Idempotency-Key": "qa-service-request-002"})
check("Patient-only doctor creates ServiceRequest -> 403", r.status_code == 403)

# 8. Lab sees the pending request and fulfills it
r = client.get("/fhir/ServiceRequest", headers=auth_headers(lab_token))
check("lab lists ServiceRequests -> sees at least 1", r.status_code == 200 and len(r.json()) >= 1)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/accept", headers=auth_headers(other_lab["access_token"]))
check("unassigned laboratory cannot accept the request -> 403", r.status_code == 403)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/finalize", headers=auth_headers(lab_token))
check("reviewer cannot finalize before results are submitted -> 409", r.status_code == 409)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/accept", headers=auth_headers(lab_token))
check("assigned lab accepts request -> 200", r.status_code == 200 and r.json()["status"] == "ACCEPTED")

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/assign", json={
    "technician_email": "qa.unassigned@example.com",
}, headers=auth_headers(lab_token))
check("laboratory cannot assign an unaffiliated technician -> 403", r.status_code == 403)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/assign", json={
    "technician_email": "qa.technician@example.com",
}, headers=auth_headers(lab_token))
check("lab assigns member technician -> 200", r.status_code == 200 and r.json()["status"] == "ASSIGNED")

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/specimen", json={}, headers=auth_headers(technician["access_token"]))
check("assigned technician registers specimen -> 200", r.status_code == 200 and r.json()["status"] == "SPECIMEN_REGISTERED")
check(
    "specimen is linked to patient and ServiceRequest",
    r.status_code == 200
    and r.json()["specimen"]["resourceType"] == "Specimen"
    and r.json()["specimen"]["subject"]["reference"] == f"Patient/{patient_id}"
    and r.json()["specimen"]["request"][0]["reference"].startswith("ServiceRequest/"),
)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/processing", headers=auth_headers(technician["access_token"]))
check("assigned technician starts processing -> 200", r.status_code == 200 and r.json()["status"] == "PROCESSING")

r = client.post("/fhir/DiagnosticReport", json={
    "service_request_id": service_request_id,
    "observations": [{"code": "6690-2", "display": "WBC count", "value": 6.8, "unit": "10*3/uL"}],
    "conclusion": "White blood cell count within normal limits.",
}, headers=auth_headers(technician["access_token"]))
check("assigned technician submits results -> 200 preliminary report", r.status_code == 200 and r.json()["resource"]["status"] == "preliminary")
check(
    "diagnostic report references the registered specimen",
    r.status_code == 200 and r.json()["resource"]["specimen"][0]["reference"].startswith("Specimen/"),
)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/finalize", headers=auth_headers(lab_token))
check("assigned lab reviewer finalizes report -> 200", r.status_code == 200 and r.json()["resource"]["status"] == "final")

# 9. Patient sees own report; consented doctorA sees it; unconsented doctorB does not
r = client.get("/fhir/DiagnosticReport", headers=auth_headers(patient_token))
check("patient sees own DiagnosticReport", r.status_code == 200 and len(r.json()) == 1)

r = client.get("/fhir/DiagnosticReport", headers=auth_headers(doctorA_token))
check("consented doctor sees DiagnosticReport", r.status_code == 200 and len(r.json()) == 1)

r = client.get("/fhir/DiagnosticReport", headers=auth_headers(doctorB_token))
check("Patient-only doctor sees 0 reports (not an error, just empty)", r.status_code == 200 and len(r.json()) == 0)

r = client.post(f"/fhir/ServiceRequest/{service_request_id}/physician-review", headers=auth_headers(doctorA_token))
check("requesting physician records clinical review -> 200", r.status_code == 200 and r.json()["status"] == "PHYSICIAN_REVIEWED")

r = client.get("/consent/access-history", headers=auth_headers(patient_token))
check(
    "patient sees sharing access history but not their own record views",
    r.status_code == 200 and any(entry["actor_role"] == "doctor" and entry["resource_type"] == "Patient" for entry in r.json()) and all(entry["actor_role"] != "patient" for entry in r.json()),
)

# 10. Revoke consent, then confirm doctorA loses access immediately
r = client.post(f"/consent/revoke/{consent_id}", headers=auth_headers(patient_token))
check("revoke consent -> 200", r.status_code == 200 and r.json()["is_active"] is False)

r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "qa.patient@example.com",
    "lab_email": "qa.lab@example.com",
    "test_display": "Follow-up test",
}, headers={**auth_headers(doctorA_token), "Idempotency-Key": "qa-service-request-003"})
check("after revoke, same doctor creating ServiceRequest -> 403", r.status_code == 403)

r = client.get("/fhir/DiagnosticReport", headers=auth_headers(doctorA_token))
check("after revoke, doctor cannot retrieve reports -> empty list", r.status_code == 200 and len(r.json()) == 0)

# 11. Admin reads audit log and verifies the hash chain is intact
r = client.get("/audit/log", headers=auth_headers(admin_token))
check("admin reads audit log -> 200, has entries", r.status_code == 200 and len(r.json()) > 0)

r = client.get("/audit/verify", headers=auth_headers(admin_token))
check("audit chain verifies as valid before tampering", r.status_code == 200 and r.json()["chain_valid"] is True)

# 12. Tamper test: directly edit one historical row in the DB (bypassing the
# API, the way a rogue admin with DB access might) and confirm /audit/verify
# detects it. This is the actual proof of the tamper-evidence claim.
db = SessionLocal()
victim = db.query(models.AuditLog).filter(models.AuditLog.event_type == "CONSENT_GRANTED").first()
victim_id = victim.id
victim.event_payload = {**victim.event_payload, "resource_types": ["Patient", "ServiceRequest", "Observation", "DiagnosticReport", "SECRETLY_ADDED"]}
db.commit()
db.close()

r = client.get("/audit/verify", headers=auth_headers(admin_token))
result = r.json()
check("tampering a past row is detected -> chain_valid False", result["chain_valid"] is False)
check("verify reports the correct broken entry id", result["broken_at_id"] == victim_id)

print()
if failures:
    print(f"{len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"All checks passed.")
