import os
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

import models
import rate_limit
import schemas
from auth_utils import create_access_token, hash_password, verify_password
from database import get_db
from deps import get_current_user, oauth2_scheme, require_roles, verify_keycloak_claims
from services import audit_logger, fhir_builder
from services.fhir_server import persist_resource
from services.oidc import map_keycloak_role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token)
def register(payload: schemas.PublicUserCreate, db: Session = Depends(get_db)):
    if os.getenv("AUTH_PROVIDER", "local").lower() == "keycloak":
        raise HTTPException(status_code=409, detail="Patient registration must be completed through Keycloak")
    return _create_account(db, payload, "patient")


@router.post("/oidc/provision-patient", response_model=schemas.UserOut)
def provision_oidc_patient(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    if os.getenv("AUTH_PROVIDER", "local").lower() != "keycloak":
        raise HTTPException(status_code=404, detail="OIDC patient provisioning is not enabled")
    claims = verify_keycloak_claims(token)
    if map_keycloak_role(claims) != "patient":
        raise HTTPException(status_code=403, detail="Only patient accounts may self-provision")

    subject = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name")
    if (
        not isinstance(subject, str) or not subject
        or claims.get("email_verified") is not True
        or not isinstance(email, str) or not email
        or not isinstance(name, str) or len(name.strip()) < 2
    ):
        raise HTTPException(status_code=422, detail="Verified Keycloak name and email claims are required")

    existing_subject = db.query(models.User).filter(
        models.User.identity_subject == subject,
    ).first()
    if existing_subject:
        if existing_subject.role != "patient":
            raise HTTPException(status_code=403, detail="Keycloak role does not match the provisioned account")
        return existing_subject
    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="This email is already provisioned; contact an administrator")

    try:
        payload = schemas.UserCreate(
            full_name=name.strip(),
            email=email,
            password=secrets.token_urlsafe(48),
            role="patient",
            identity_subject=subject,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Keycloak profile claims are invalid") from exc
    return _create_account(db, payload, "patient", issue_token=False)


@router.post("/users", response_model=schemas.UserOut)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    keycloak_mode = os.getenv("AUTH_PROVIDER", "local").lower() == "keycloak"
    if keycloak_mode and not payload.identity_subject:
        raise HTTPException(status_code=422, detail="identity_subject is required for Keycloak accounts")
    if not keycloak_mode and not payload.password:
        raise HTTPException(status_code=422, detail="password is required for local accounts")
    user = _create_account(db, payload, payload.role, issue_token=False)
    audit_logger.log_event(db, current_user.id, "USER_PROVISIONED", {
        "user_id": user.id,
        "role": user.role,
    })
    return user


@router.post("/laboratory-memberships")
def create_laboratory_membership(
    payload: schemas.LaboratoryMembershipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    laboratory = db.query(models.User).filter(
        models.User.email == payload.laboratory_email,
        models.User.role.in_(("lab", "lab_supervisor")),
    ).first()
    technician = db.query(models.User).filter(
        models.User.email == payload.technician_email,
        models.User.role == "lab_technician",
    ).first()
    if not laboratory or not technician:
        raise HTTPException(status_code=404, detail="Laboratory or technician account not found")

    membership = db.query(models.LaboratoryMembership).filter(
        models.LaboratoryMembership.laboratory_id == laboratory.id,
        models.LaboratoryMembership.technician_id == technician.id,
    ).first()
    if not membership:
        membership = models.LaboratoryMembership(
            laboratory_id=laboratory.id,
            technician_id=technician.id,
            created_by=current_user.id,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        audit_logger.log_event(db, current_user.id, "LABORATORY_MEMBER_ADDED", {
            "laboratory_id": laboratory.id,
            "technician_id": technician.id,
        })
    return {"id": membership.id, "laboratory_id": laboratory.id, "technician_id": technician.id}


def _create_account(db: Session, payload, role: str, issue_token: bool = True):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password or secrets.token_urlsafe(48)),
        role=role,
        identity_subject=getattr(payload, "identity_subject", None),
    )
    db.add(user)
    db.flush()

    if user.role in ("patient", "doctor", "lab", "lab_supervisor"):
        builder, resource_type = {
            "patient": (fhir_builder.build_patient, "Patient"),
            "doctor": (fhir_builder.build_practitioner, "Practitioner"),
            "lab": (fhir_builder.build_organization, "Organization"),
            "lab_supervisor": (fhir_builder.build_organization, "Organization"),
        }[user.role]
        user.fhir_resource_id = user.id
        resource_data = persist_resource(builder(user))
        db.add(models.FHIRResource(
            resource_type=resource_type, fhir_id=user.id, resource_data=resource_data,
            owner_id=user.id, created_by=user.id,
        ))
    db.commit()
    db.refresh(user)

    audit_logger.log_event(db, user.id, "USER_REGISTERED", {"role": user.role})

    if not issue_token:
        return user
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "user": schemas.UserOut.model_validate(user)}


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    if os.getenv("AUTH_PROVIDER", "local").lower() == "keycloak":
        raise HTTPException(status_code=409, detail="Sign in through the configured Keycloak client")
    locked_for = rate_limit.is_locked_out(payload.email)
    if locked_for:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {locked_for:.0f}s.",
            headers={"Retry-After": str(int(locked_for) + 1)},
        )

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        rate_limit.record_failure(payload.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    rate_limit.record_success(payload.email)
    audit_logger.log_event(db, user.id, "USER_LOGIN", {"role": user.role})
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "user": schemas.UserOut.model_validate(user)}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
