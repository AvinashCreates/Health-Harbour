"""Seeds demo accounts plus one sample consent -> ServiceRequest ->
DiagnosticReport chain, so the app isn't empty on first run.
Run with: python seed.py
"""
import os
import uuid
import hashlib
from datetime import datetime, timedelta

import models
from auth_utils import hash_password
from database import Base, DATABASE_URL, SessionLocal, engine
from services import audit_logger, fhir_builder
from services.fhir_server import persist_resource
from services.document_storage import get_document_storage


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

org_a = db.query(models.HealthcareOrganization).filter(
    models.HealthcareOrganization.legacy_user_id == lab1.id,
).first()
if org_a is None:
    org_a = models.HealthcareOrganization(
        legacy_user_id=lab1.id,
        legal_name="Central Diagnostics Hospital",
        display_name="Central Diagnostics Hospital",
        organization_type="DIAGNOSTIC_LABORATORY",
        registration_authority="Synthetic Health Authority",
        registration_identifier="SYN-ORG-A",
        address={"city": "Hyderabad", "country": "IN"},
        administrative_contact_name="Central Diagnostics Admin",
        administrative_contact_email="lab@example.com",
        status="APPROVED",
        fhir_resource_id=lab1.fhir_resource_id or lab1.id,
    )
    db.add(org_a)
    db.flush()
else:
    org_a.status = "APPROVED"

org_b = db.query(models.HealthcareOrganization).filter(
    models.HealthcareOrganization.registration_identifier == "SYN-ORG-B",
).first()
if org_b is None:
    org_b = models.HealthcareOrganization(
        legal_name="Harbor Specialty Hospital",
        display_name="Harbor Specialty Hospital",
        organization_type="HOSPITAL",
        registration_authority="Synthetic Health Authority",
        registration_identifier="SYN-ORG-B",
        address={"city": "Bengaluru", "country": "IN"},
        administrative_contact_name="Harbor Specialty Admin",
        administrative_contact_email="hospital-b@example.com",
        status="APPROVED",
    )
    db.add(org_b)
    db.flush()
else:
    org_b.status = "APPROVED"

provider1 = db.query(models.HealthcareProvider).filter(
    models.HealthcareProvider.account_id == doctor1.id,
).first()
if provider1 is None:
    provider1 = models.HealthcareProvider(
        account_id=doctor1.id,
        professional_name="Dr. Priya Sharma",
        registration_authority="Synthetic Medical Council",
        registration_number="SYN-PROVIDER-1",
        qualifications=["Synthetic MD"],
        specialization="Internal Medicine",
        status="VERIFIED",
        fhir_resource_id=doctor1.fhir_resource_id or doctor1.id,
    )
    db.add(provider1)
    db.flush()
else:
    provider1.status = "VERIFIED"

provider2 = db.query(models.HealthcareProvider).filter(
    models.HealthcareProvider.account_id == doctor2.id,
).first()
if provider2 is None:
    provider2 = models.HealthcareProvider(
        account_id=doctor2.id,
        professional_name="Dr. Arjun Mehta",
        registration_authority="Synthetic Medical Council",
        registration_number="SYN-PROVIDER-2",
        qualifications=["Synthetic MD"],
        specialization="Cardiology",
        status="VERIFIED",
        fhir_resource_id=doctor2.fhir_resource_id or doctor2.id,
    )
    db.add(provider2)
    db.flush()
else:
    provider2.status = "VERIFIED"

for organization, provider in ((org_a, provider1), (org_b, provider2)):
    affiliation = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.organization_id == organization.id,
        models.OrganizationAffiliation.provider_id == provider.id,
    ).first()
    if affiliation is None:
        db.add(models.OrganizationAffiliation(
            organization_id=organization.id,
            provider_id=provider.id,
            account_id=provider.account_id,
            organization_role="PROVIDER",
            status="ACTIVE",
            invited_by_id=admin1.id,
            effective_from=datetime.utcnow(),
        ))
    else:
        affiliation.status = "ACTIVE"

db.commit()

already_seeded = db.query(models.Consent).filter(
    models.Consent.patient_id == patient1.id, models.Consent.grantee_id == doctor1.id
).first()

if not already_seeded:
    consent = models.Consent(
        patient_id=patient1.id,
        grantee_id=doctor1.id,
        organization_id=org_a.id,
        resource_types=["Patient", "ServiceRequest", "Observation", "DiagnosticReport", "Document", "MedicationRequest"],
        granted_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(consent)
    db.flush()
    fhir_consent = fhir_builder.build_consent(
        consent.id, patient1.fhir_resource_id, doctor1.fhir_resource_id,
        consent.resource_types, consent.granted_at, consent.expires_at,
        organization_ref=org_a.fhir_resource_id or org_a.id,
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

    file_content = b"Synthetic fasting glucose report: 96 mg/dL. This is not medical advice."
    digest = hashlib.sha256(file_content).hexdigest()
    storage_key = f"{uuid.uuid4().hex}.blob"
    storage = get_document_storage()
    storage_path, encryption_version, encryption_key_id = storage.write_new(storage_key, file_content)
    document_id = str(uuid.uuid4())
    document = models.ClinicalFile(
        id=document_id,
        patient_id=patient1.id,
        uploaded_by_id=lab1.id,
        service_request_id=sr_record.id,
        filename="fasting-glucose-synthetic.txt",
        storage_key=storage_key,
        media_type="text/plain",
        category="laboratory-report",
        size_bytes=len(file_content),
        sha256=digest,
        source_organization_id=org_a.id,
        custodian_organization_id=org_a.id,
        processing_status="CLEAN",
        scan_status="NOT_REQUIRED",
        encryption_version=encryption_version,
        encryption_key_id=encryption_key_id,
    )
    db.add(document)
    db.commit()

    prescription = models.Prescription(
        patient_id=patient1.id,
        provider_id=provider1.id,
        organization_id=org_a.id,
        medication_name="Synthetic Wellness Supplement",
        dosage="1 synthetic unit",
        route="oral",
        frequency="once daily",
        duration="7 days",
        quantity="7 units",
        instructions="Synthetic demonstration only; no real medication advice.",
        status="ACTIVE",
    )
    db.add(prescription)
    db.flush()
    db.add(models.PrescriptionHistory(
        prescription_id=prescription.id,
        actor_id=doctor1.id,
        from_status=None,
        to_status="ACTIVE",
        reason="Synthetic demo prescription",
    ))

    review = models.PhysicianClinicalReview(
        patient_id=patient1.id,
        provider_id=provider1.id,
        organization_id=org_a.id,
        diagnostic_report_id=report_fhir_id,
        service_request_id=sr_record.id,
        status="REVIEWED",
        clinical_note="Synthetic review: fasting glucose is within the simulated reference range.",
        reviewed_at=datetime.utcnow(),
    )
    db.add(review)
    db.commit()
    audit_logger.log_event(db, doctor1.id, "PRESCRIPTION_CREATED", {
        "prescription_id": prescription.id,
        "patient_id": patient1.id,
        "provider_id": provider1.id,
        "organization_id": org_a.id,
        "medication_name": prescription.medication_name,
    })
    audit_logger.log_event(db, doctor1.id, "PHYSICIAN_CLINICAL_REVIEW_RECORDED", {
        "patient_id": patient1.id,
        "provider_id": provider1.id,
        "organization_id": org_a.id,
        "report_id": report_fhir_id,
        "status": "REVIEWED",
    })
    print("Sample consent + ServiceRequest + DiagnosticReport chain created for Asha Rao / Dr. Priya Sharma.")
else:
    print("Sample workflow already present -- skipped.")

print("\nLocal demo accounts seeded; password is not displayed.")
for u in [patient1, patient2, doctor1, doctor2, lab1, admin1]:
    print(f"  {u.role:8s} {u.email}")

db.close()
