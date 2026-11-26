"""Seeds demo accounts plus one sample consent -> ServiceRequest ->
DiagnosticReport chain, so the app isn't empty on first run.
Run with: python seed.py
"""
import os
import uuid
from datetime import datetime, timedelta

import models
from auth_utils import hash_password
from database import Base, DATABASE_URL, SessionLocal, engine
from services import audit_logger, fhir_builder
from services.fhir_server import persist_resource


def _configured_password(environment_name):
    password = os.getenv(environment_name)
    if password is None:
        raise RuntimeError(f"{environment_name} must be explicitly configured before seeding")
    encoded = password.encode("utf-8")
    if (
        len(password) < 16
        or len(encoded) > 72
        or not any(char.islower() for char in password)
        or not any(char.isupper() for char in password)
        or not any(char.isdigit() for char in password)
        or not any(not char.isalnum() for char in password)
    ):
        raise RuntimeError(
            f"{environment_name} must be 16-72 UTF-8 bytes and include "
            "lowercase, uppercase, numeric, and special characters"
        )
    return password


if os.getenv("AUTH_PROVIDER", "local").lower() == "keycloak":
    raise RuntimeError("Local account seeding is disabled with Keycloak authentication")

production = os.getenv("APP_ENV", "development").lower() == "production"
if production:
    initial_admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
    initial_admin_name = os.getenv("INITIAL_ADMIN_NAME", "").strip()
    initial_admin_password = _configured_password("INITIAL_ADMIN_PASSWORD")
    if (
        "@" not in initial_admin_email
        or len(initial_admin_email) > 254
        or not 2 <= len(initial_admin_name) <= 120
    ):
        raise RuntimeError("A valid INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_NAME are required")
else:
    demo_password = _configured_password("DEMO_SEED_PASSWORD")

if DATABASE_URL.startswith("sqlite") or os.getenv("DB_AUTO_CREATE") == "1":
    Base.metadata.create_all(bind=engine)
else:
    from sqlalchemy import inspect
    if not inspect(engine).has_table("users"):
        raise RuntimeError("Run `alembic upgrade head` before seeding PostgreSQL")
db = SessionLocal()

if production:
    initial_admin = db.query(models.User).filter(
        models.User.email == initial_admin_email,
    ).first()
    if initial_admin is not None and initial_admin.role != "admin":
        db.close()
        raise RuntimeError("INITIAL_ADMIN_EMAIL already belongs to a non-administrator account")
    if initial_admin is None:
        initial_admin = models.User(
            full_name=initial_admin_name,
            email=initial_admin_email,
            hashed_password=hash_password(initial_admin_password),
            role="admin",
        )
        db.add(initial_admin)
        db.commit()
        print("Initial administrator account created.")
    else:
        print("Initial administrator account already exists; no credentials were changed.")
    db.close()
    raise SystemExit(0)


def make_user(full_name, email, role):
    existing = db.query(models.User).filter(models.User.email == email).first()
    user = existing or models.User(
        full_name=full_name,
        email=email,
        hashed_password=hash_password(demo_password),
        role=role,
    )
    if existing is None:
        db.add(user)
        db.flush()
    if role in ("patient", "doctor", "lab"):
        builder, resource_type = {
            "patient": (fhir_builder.build_patient, "Patient"),
            "doctor": (fhir_builder.build_practitioner, "Practitioner"),
            "lab": (fhir_builder.build_organization, "Organization"),
        }[role]
        user.fhir_resource_id = user.fhir_resource_id or user.id
        data = persist_resource(builder(user))
        record = db.query(models.FHIRResource).filter(
            models.FHIRResource.resource_type == resource_type,
            models.FHIRResource.fhir_id == user.fhir_resource_id,
        ).first()
        if record:
            record.resource_data = data
        else:
            db.add(models.FHIRResource(
                resource_type=resource_type, fhir_id=user.fhir_resource_id, resource_data=data,
                owner_id=user.id, created_by=user.id,
            ))
    db.commit()
    db.refresh(user)
    return user


print("Seeding local demo accounts...")
patient1 = make_user("Asha Rao", "asha.patient@example.com", "patient")
patient2 = make_user("Vikram Nair", "vikram.patient@example.com", "patient")
doctor1 = make_user("Dr. Priya Sharma", "priya.doctor@example.com", "doctor")
doctor2 = make_user("Dr. Arjun Mehta", "arjun.doctor@example.com", "doctor")
lab1 = make_user("Central Diagnostics Lab", "lab@example.com", "lab")
admin1 = make_user("System Admin", "admin@example.com", "admin")

already_seeded = db.query(models.Consent).filter(
    models.Consent.patient_id == patient1.id, models.Consent.grantee_id == doctor1.id
).first()

if not already_seeded:
    consent = models.Consent(
        patient_id=patient1.id,
        grantee_id=doctor1.id,
        resource_types=["Patient", "ServiceRequest", "Observation", "DiagnosticReport"],
        granted_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(consent)
    db.flush()
    fhir_consent = fhir_builder.build_consent(
        consent.id, patient1.fhir_resource_id, doctor1.fhir_resource_id,
        consent.resource_types, consent.granted_at, consent.expires_at,
    )
    persist_resource(fhir_consent)
    db.commit()
    audit_logger.log_event(db, patient1.id, "CONSENT_GRANTED", {
        "consent_id": consent.id, "grantee_id": doctor1.id, "note": "seed data",
    })

    sr_fhir_id = str(uuid.uuid4())
    sr_data = fhir_builder.build_service_request(
        sr_fhir_id, patient1.id, doctor1.id, "2345-7",
        "Glucose [Mass/volume] in Serum or Plasma", "Routine fasting glucose check",
    )
    sr_data["performer"] = [{"reference": f"Organization/{lab1.fhir_resource_id or lab1.id}"}]
    sr_data = persist_resource(sr_data)
    sr_record = models.FHIRResource(
        resource_type="ServiceRequest", fhir_id=sr_fhir_id, resource_data=sr_data,
        owner_id=patient1.id, created_by=doctor1.id,
    )
    db.add(sr_record)
    db.commit()
    db.refresh(sr_record)
    audit_logger.log_event(db, doctor1.id, "SERVICE_REQUEST_CREATED", {"patient_id": patient1.id, "fhir_id": sr_fhir_id})

    obs_fhir_id = str(uuid.uuid4())
    obs_data = fhir_builder.build_observation(obs_fhir_id, patient1.id, sr_fhir_id, "2345-7", "Glucose", 96, "mg/dL")
    obs_data = persist_resource(obs_data)
    db.add(models.FHIRResource(
        resource_type="Observation", fhir_id=obs_fhir_id, resource_data=obs_data,
        owner_id=patient1.id, created_by=lab1.id,
    ))

    report_fhir_id = str(uuid.uuid4())
    report_data = fhir_builder.build_diagnostic_report(
        report_fhir_id, patient1.id, sr_fhir_id, [obs_fhir_id], lab1.id,
        "Fasting glucose within normal range (96 mg/dL).",
    )
    report_data = persist_resource(report_data)
    db.add(models.FHIRResource(
        resource_type="DiagnosticReport", fhir_id=report_fhir_id, resource_data=report_data,
        owner_id=patient1.id, created_by=lab1.id,
    ))
    db.commit()
    workflow = models.LaboratoryWorkflow(
        service_request_id=sr_record.id,
        patient_id=patient1.id,
        physician_id=doctor1.id,
        laboratory_id=lab1.id,
        reviewer_id=lab1.id,
        report_fhir_id=report_fhir_id,
        status="FINALIZED",
    )
    db.add(workflow)
    db.flush()
    for previous, current in [
        ("", "REQUESTED"),
        ("REQUESTED", "ACCEPTED"),
        ("ACCEPTED", "ASSIGNED"),
        ("ASSIGNED", "SPECIMEN_REGISTERED"),
        ("SPECIMEN_REGISTERED", "PROCESSING"),
        ("PROCESSING", "RESULTS_SUBMITTED"),
        ("RESULTS_SUBMITTED", "FINALIZED"),
    ]:
        db.add(models.WorkflowTransition(
            workflow_id=workflow.id,
            actor_id=doctor1.id if current == "REQUESTED" else lab1.id,
            from_status=previous,
            to_status=current,
            note="Synthetic demo history",
        ))
    db.commit()
    audit_logger.log_event(db, lab1.id, "DIAGNOSTIC_REPORT_UPLOADED", {"patient_id": patient1.id, "report_fhir_id": report_fhir_id})
    print("Sample consent + ServiceRequest + DiagnosticReport chain created for Asha Rao / Dr. Priya Sharma.")
else:
    print("Sample workflow already present -- skipped.")

print("\nLocal demo accounts seeded; password is not displayed.")
for u in [patient1, patient2, doctor1, doctor2, lab1, admin1]:
    print(f"  {u.role:8s} {u.email}")

db.close()
