"""Adversarial tests, separate from test_api.py's functional coverage.
Each test is a concrete attack attempt, not just a happy-path check.

Run with: DATABASE_URL=sqlite:///./test_security.db python test_security.py
"""
import sys
from datetime import timedelta

from fastapi.testclient import TestClient

from auth_utils import create_access_token
from auth_utils import hash_password
from database import SessionLocal
from main import app
import models

client = TestClient(app)
failures = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def register(email, role="patient"):
    if role == "patient":
        r = client.post("/auth/register", json={
            "full_name": "Sec Test", "email": email, "password": "SecPassword@123",
        })
        return r.json()
    db = SessionLocal()
    user = models.User(full_name="Sec Test", email=email, hashed_password=hash_password("SecPassword@123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    result = {
        "access_token": create_access_token({"sub": user.id, "role": user.role}),
        "user": {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role},
    }
    db.close()
    return result


# --- 1. No token at all on a protected route ---
r = client.get("/auth/me")
check("no token on protected route -> 401", r.status_code == 401)

# --- 2. Garbage / malformed token ---
r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
check("malformed token -> 401", r.status_code == 401)

# --- 3. Expired token rejected ---
user = register("sec.expiry@example.com")
expired_token = create_access_token({"sub": user["user"]["id"], "role": "patient"}, expires_delta=timedelta(seconds=-10))
r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
check("expired token (exp in the past) -> 401", r.status_code == 401)

# --- 4. Tampered token (valid structure, broken signature) rejected ---
valid_token = user["access_token"]
tampered = valid_token[:-4] + ("A" if valid_token[-4] != "A" else "B") + valid_token[-3:]
r = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
check("tampered signature -> 401", r.status_code == 401)

# --- 5. Public registration cannot self-assign privileged roles ---
r = client.post("/auth/register", json={
    "full_name": "Role Escalation", "email": "sec.escalation@example.com",
    "password": "SecPassword@123", "role": "admin",
})
check("public registration with admin role -> 422", r.status_code == 422)

r = client.get("/health")
check("API includes no-sniff and no-store security headers", r.headers.get("X-Content-Type-Options") == "nosniff" and r.headers.get("Cache-Control") == "no-store")

# --- 5. Role escalation attempts: each role-gated route rejects the wrong role ---
r = client.post("/auth/register", json={
    "full_name": "Long Password", "email": "sec.long-password@example.com",
    "password": "A" * 73,
})
check("password exceeding bcrypt's supported byte length -> 422", r.status_code == 422)
patient = register("sec.patient@example.com", "patient")
doctor = register("sec.doctor@example.com", "doctor")
lab = register("sec.lab@example.com", "lab")
admin = register("sec.admin@example.com", "admin")
patient_token = patient["access_token"]
doctor_token = doctor["access_token"]

r = client.post("/auth/users", json={
    "full_name": "Created by patient",
    "email": "sec.provisioned@example.com",
    "password": "SecPassword@123",
    "role": "lab_technician",
}, headers={"Authorization": f"Bearer {patient_token}"})
check("patient cannot provision a staff account -> 403", r.status_code == 403)

r = client.post("/auth/users", json={
    "full_name": "Provisioned technician",
    "email": "sec.provisioned@example.com",
    "password": "SecPassword@123",
    "role": "lab_technician",
}, headers={"Authorization": f"Bearer {admin['access_token']}"})
check("admin can provision a technician account -> 200", r.status_code == 200 and r.json()["role"] == "lab_technician")

r = client.post("/auth/laboratory-memberships", json={
    "laboratory_email": "sec.lab@example.com",
    "technician_email": "sec.provisioned@example.com",
}, headers={"Authorization": f"Bearer {admin['access_token']}"})
check("admin can add technician to a laboratory -> 200", r.status_code == 200)

r = client.post("/auth/laboratory-memberships", json={
    "laboratory_email": "sec.lab@example.com",
    "technician_email": "sec.provisioned@example.com",
}, headers={"Authorization": f"Bearer {patient_token}"})
check("patient cannot modify laboratory membership -> 403", r.status_code == 403)

r = client.get("/audit/log", headers={"Authorization": f"Bearer {patient_token}"})
check("non-admin GET /audit/log -> 403", r.status_code == 403)

r = client.post("/consent/grant", json={"doctor_email": "sec.doctor@example.com"}, headers={"Authorization": f"Bearer {doctor_token}"})
check("non-patient POST /consent/grant -> 403", r.status_code == 403)

r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "sec.patient@example.com", "lab_email": "sec.lab@example.com",
}, headers={"Authorization": f"Bearer {patient_token}", "Idempotency-Key": "security-unauth-test"})
check("non-doctor POST /fhir/ServiceRequest -> 403", r.status_code == 403)

r = client.post("/fhir/DiagnosticReport", json={"service_request_id": "x", "observations": [], "conclusion": "x"}, headers={"Authorization": f"Bearer {doctor_token}"})
check("non-lab POST /fhir/DiagnosticReport -> 403", r.status_code == 403)

r = client.get(f"/fhir/Patient/{patient['user']['id']}", headers={"Authorization": f"Bearer {admin['access_token']}"})
check("admin cannot read a patient's clinical resource -> 403", r.status_code == 403)

r = client.get("/fhir/ServiceRequest", headers={"Authorization": f"Bearer {admin['access_token']}"})
check("admin cannot list clinical laboratory requests -> 403", r.status_code == 403)

r = client.get("/fhir/DiagnosticReport", headers={"Authorization": f"Bearer {admin['access_token']}"})
check("admin cannot list clinical reports -> 403", r.status_code == 403)

# --- 6. Injection-style strings in free-text fields don't break the app
#     or touch the database structurally (SQLAlchemy ORM parameterizes
#     everything, so this should just be stored as an inert string) ---
injection_doctor = register("sec.injector@example.com", "doctor")
# give this doctor consent so the ServiceRequest call reaches the field we're
# attacking rather than failing earlier on a 403
client.post("/consent/grant", json={
    "doctor_email": "sec.injector@example.com", "duration_days": 1,
}, headers={"Authorization": f"Bearer {patient_token}"})

payload_str = "'; DROP TABLE users; --"
r = client.post("/fhir/ServiceRequest", json={
    "patient_email": "sec.patient@example.com",
    "lab_email": "sec.lab@example.com",
    "test_display": payload_str,
    "note": "<script>alert(1)</script>",
}, headers={"Authorization": f"Bearer {injection_doctor['access_token']}", "Idempotency-Key": "security-injection-test"})
check("injection-style string -> no server error (500)", r.status_code != 500)
check("injection-style string stored verbatim, inert", r.status_code == 200 and r.json()["resource"]["code"]["text"] == payload_str)

# confirm the users table is intact (i.e. nothing was actually dropped)
r = client.post("/auth/login", json={"email": "sec.patient@example.com", "password": "SecPassword@123"})
check("users table intact after injection attempt (existing user can still log in)", r.status_code == 200)

# --- 7. Login rate limiting: 5 failed attempts lock out the 6th, even with
#     the CORRECT password, for the lockout window ---
rl_email = "sec.ratelimit@example.com"
register(rl_email)
for _ in range(5):
    client.post("/auth/login", json={"email": rl_email, "password": "WrongPassword"})
r = client.post("/auth/login", json={"email": rl_email, "password": "SecPassword@123"})  # correct password
check("6th attempt after 5 failures is locked out (429) even with correct password", r.status_code == 429)

print()
if failures:
    print(f"{len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All security checks passed.")
