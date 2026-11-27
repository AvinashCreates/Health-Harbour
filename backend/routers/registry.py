from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user, require_roles
from services import audit_logger
from services.registry import add_affiliation_event, require_organization_admin
from services import fhir_builder
from services.fhir_sync import queue_fhir_resource

router = APIRouter(prefix="/api/v1", tags=["healthcare registry"])

def _organization_application_out(
    application: models.OrganizationApplication,
    organization: models.HealthcareOrganization,
) -> dict:
    return {
        "id": application.id,
        "organization_id": organization.id,
        "legal_name": organization.legal_name,
        "display_name": organization.display_name,
        "organization_type": organization.organization_type,
        "registration_authority": organization.registration_authority,
        "registration_identifier": organization.registration_identifier,
        "address": organization.address or {},
        "contact_email": organization.contact_email,
        "contact_phone": organization.contact_phone,
        "administrative_contact_name": organization.administrative_contact_name,
        "administrative_contact_email": organization.administrative_contact_email,
        "status": organization.status,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "decision_reason": application.decision_reason,
        "evidence_references": application.evidence_references or [],
    }


def _provider_application_out(
    application: models.ProviderApplication,
    provider: models.HealthcareProvider,
    include_evidence: bool = True,
) -> dict:
    return {
        "id": application.id,
        "provider_id": provider.id,
        "professional_name": provider.professional_name,
        "registration_authority": provider.registration_authority,
        "registration_number": provider.registration_number,
        "qualifications": provider.qualifications or [],
        "specialization": provider.specialization,
        "status": provider.status,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "decision_reason": application.decision_reason,
        "evidence_references": (
            application.evidence_references or [] if include_evidence else None
        ),
    }


def _organization_directory_out(organization: models.HealthcareOrganization) -> dict:
    return {
        "id": organization.id,
        "legal_name": organization.legal_name,
        "display_name": organization.display_name,
        "organization_type": organization.organization_type,
        "registration_authority": organization.registration_authority,
        "registration_identifier": organization.registration_identifier,
        "address": organization.address or {},
        "contact_email": organization.contact_email,
    }


def _affiliation_out(
    db: Session,
    affiliation: models.OrganizationAffiliation,
) -> dict:
    organization = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == affiliation.organization_id,
    ).first()
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == affiliation.provider_id,
    ).first()
    return {
        "id": affiliation.id,
        "organization_id": affiliation.organization_id,
        "organization_name": organization.display_name if organization else "Organization",
        "provider_id": affiliation.provider_id,
        "professional_name": provider.professional_name if provider else "Provider",
        "organization_role": affiliation.organization_role,
        "status": affiliation.status,
        "invited_at": affiliation.invited_at,
        "accepted_at": affiliation.accepted_at,
        "effective_from": affiliation.effective_from,
        "effective_until": affiliation.effective_until,
        "decided_at": affiliation.decided_at,
        "decision_reason": affiliation.decision_reason,
    }


def _active_assignment(
    db: Session,
    user_id: str,
    organization_id: str,
    role: str = "ORGANIZATION_ADMIN",
) -> bool:
    return db.query(models.OrganizationRoleAssignment.id).filter(
        models.OrganizationRoleAssignment.user_id == user_id,
        models.OrganizationRoleAssignment.organization_id == organization_id,
        models.OrganizationRoleAssignment.role == role,
        models.OrganizationRoleAssignment.revoked_at.is_(None),
    ).first() is not None


def _latest_application(
    db: Session,
    model,
    foreign_key: str,
    entity_id: str,
):
    return db.query(model).filter(
        getattr(model, foreign_key) == entity_id,
    ).order_by(model.submitted_at.desc()).first()


@router.post(
    "/organization-applications",
    response_model=schemas.OrganizationApplicationOut,
    status_code=201,
)
def submit_organization_application(
    payload: schemas.OrganizationApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Platform administrators cannot apply for organizations")
    latest_application = _latest_application(
        db,
        models.OrganizationApplication,
        "applicant_user_id",
        current_user.id,
    )
    organization = None
    if latest_application:
        organization = db.query(models.HealthcareOrganization).filter(
            models.HealthcareOrganization.id == latest_application.organization_id,
        ).first()
    if organization is None:
        organization = db.query(models.HealthcareOrganization).filter(
            models.HealthcareOrganization.legacy_user_id == current_user.id,
        ).first()
    if payload.registration_authority and payload.registration_identifier:
        duplicate_query = db.query(models.HealthcareOrganization.id).filter(
            models.HealthcareOrganization.registration_authority == payload.registration_authority,
            models.HealthcareOrganization.registration_identifier == payload.registration_identifier,
        )
        if organization:
            duplicate_query = duplicate_query.filter(
                models.HealthcareOrganization.id != organization.id,
            )
        if duplicate_query.first():
            raise HTTPException(status_code=409, detail="This organization registration is already submitted")
    if organization:
        latest = _latest_application(
            db, models.OrganizationApplication, "organization_id", organization.id,
        )
        if organization.status in {"APPROVED", "UNDER_REVIEW", "SUSPENDED"} or (
            latest and latest.status in {"PENDING", "UNDER_REVIEW"}
        ):
            raise HTTPException(status_code=409, detail="An organization application is already active")
        organization.legal_name = payload.legal_name
        organization.display_name = payload.display_name
        organization.organization_type = payload.organization_type
        organization.registration_authority = payload.registration_authority
        organization.registration_identifier = payload.registration_identifier
        organization.address = payload.address
        organization.contact_email = str(payload.contact_email) if payload.contact_email else None
        organization.contact_phone = payload.contact_phone
        organization.administrative_contact_name = payload.administrative_contact_name
        organization.administrative_contact_email = str(payload.administrative_contact_email)
        organization.status = "PENDING"
        organization.reviewed_by_id = None
        organization.reviewed_at = None
        organization.decision_reason = None
    else:
        organization = models.HealthcareOrganization(
            legal_name=payload.legal_name,
            display_name=payload.display_name,
            organization_type=payload.organization_type,
            registration_authority=payload.registration_authority,
            registration_identifier=payload.registration_identifier,
            address=payload.address,
            contact_email=str(payload.contact_email) if payload.contact_email else None,
            contact_phone=payload.contact_phone,
            administrative_contact_name=payload.administrative_contact_name,
            administrative_contact_email=str(payload.administrative_contact_email),
            status="PENDING",
        )
        db.add(organization)
        try:
            db.flush()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An organization with this registration identifier is already registered",
            ) from error
    application = models.OrganizationApplication(
        organization_id=organization.id,
        applicant_user_id=current_user.id,
        status="PENDING",
        evidence_references=payload.evidence_references,
    )
    db.add(application)
    db.flush()
    try:
        audit_logger.log_event(db, current_user.id, "ORGANIZATION_APPLICATION_SUBMITTED", {
            "organization_id": organization.id,
            "application_id": application.id,
            "organization_type": organization.organization_type,
        })
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An organization with this registration identifier is already registered",
        ) from error
    return _organization_application_out(application, organization)


@router.get(
    "/organization-applications/me",
    response_model=list[schemas.OrganizationApplicationOut],
)
def my_organization_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.query(
        models.OrganizationApplication,
        models.HealthcareOrganization,
    ).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationApplication.organization_id,
    ).filter(
        models.OrganizationApplication.applicant_user_id == current_user.id,
    ).order_by(models.OrganizationApplication.submitted_at.desc()).all()
    return [_organization_application_out(application, organization) for application, organization in rows]


@router.get(
    "/admin/organization-applications",
    response_model=list[schemas.OrganizationApplicationOut],
)
def list_organization_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    query = db.query(
        models.OrganizationApplication,
        models.HealthcareOrganization,
    ).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationApplication.organization_id,
    )
    if status_filter:
        if status_filter not in {"PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED"}:
            raise HTTPException(status_code=422, detail="Unsupported application status")
        query = query.filter(models.OrganizationApplication.status == status_filter)
    rows = query.order_by(
        models.OrganizationApplication.submitted_at.asc(),
    ).offset(offset).limit(limit).all()
    return [_organization_application_out(application, organization) for application, organization in rows]


@router.post(
    "/admin/organization-applications/{application_id}/decision",
    response_model=schemas.OrganizationApplicationOut,
)
def decide_organization_application(
    application_id: str,
    payload: schemas.RegistryDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    application = db.query(models.OrganizationApplication).filter(
        models.OrganizationApplication.id == application_id,
    ).with_for_update().first()
    if application is None:
        raise HTTPException(status_code=404, detail="Organization application not found")
    organization = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == application.organization_id,
    ).with_for_update().first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization application not found")
    if application.applicant_user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Reviewers cannot approve their own application")

    decision = payload.decision
    if decision == "UNDER_REVIEW":
        if application.status != "PENDING":
            raise HTTPException(status_code=409, detail="Only pending applications can enter review")
        application.status = "UNDER_REVIEW"
        organization.status = "UNDER_REVIEW"
    elif decision in {"APPROVED", "REJECTED"}:
        if application.status not in {"PENDING", "UNDER_REVIEW"}:
            raise HTTPException(status_code=409, detail="This application has already been decided")
        application.status = decision
        organization.status = decision
        if decision == "APPROVED" and not _active_assignment(
            db, application.applicant_user_id, organization.id,
        ):
            db.add(models.OrganizationRoleAssignment(
                organization_id=organization.id,
                user_id=application.applicant_user_id,
                role="ORGANIZATION_ADMIN",
                granted_by_id=current_user.id,
            ))
    elif decision == "SUSPENDED":
        if organization.status != "APPROVED":
            raise HTTPException(status_code=409, detail="Only approved organizations can be suspended")
        organization.status = "SUSPENDED"
    elif decision == "REINSTATED":
        if organization.status != "SUSPENDED":
            raise HTTPException(status_code=409, detail="Only suspended organizations can be reinstated")
        organization.status = "APPROVED"
    organization.reviewed_by_id = current_user.id
    organization.reviewed_at = datetime.utcnow()
    organization.decision_reason = payload.reason
    application.reviewed_by_id = current_user.id
    application.reviewed_at = organization.reviewed_at
    application.decision_reason = payload.reason
    db.add(models.OrganizationReviewDecision(
        organization_id=organization.id,
        application_id=application.id,
        reviewer_id=current_user.id,
        decision=decision,
        reason=payload.reason,
    ))
    queue_fhir_resource(db, "Organization", organization.fhir_resource_id or organization.id, fhir_builder.build_healthcare_organization(organization))
    audit_logger.log_event(db, current_user.id, f"ORGANIZATION_{decision}", {
        "organization_id": organization.id,
        "application_id": application.id,
    })
    return _organization_application_out(application, organization)


@router.get("/admin/organizations/{organization_id}/history", response_model=list[schemas.RegistryHistoryOut])
def organization_review_history(
    organization_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    if db.query(models.HealthcareOrganization.id).filter(
        models.HealthcareOrganization.id == organization_id,
    ).first() is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    decisions = db.query(models.OrganizationReviewDecision).filter(
        models.OrganizationReviewDecision.organization_id == organization_id,
    ).order_by(
        models.OrganizationReviewDecision.created_at.desc(),
    ).offset(offset).limit(limit).all()
    return [{
        "id": item.id,
        "decision": item.decision,
        "reason": item.reason,
        "reviewer_id": item.reviewer_id,
        "created_at": item.created_at,
    } for item in decisions]


@router.get("/organizations", response_model=list[schemas.OrganizationDirectoryOut])
def organization_directory(
    query_text: str | None = Query(default=None, min_length=1, max_length=120, alias="q"),
    organization_type: schemas.OrganizationType | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.status == "APPROVED",
    )
    if organization_type:
        query = query.filter(models.HealthcareOrganization.organization_type == organization_type)
    if query_text:
        match = f"%{query_text.strip()}%"
        query = query.filter(or_(
            models.HealthcareOrganization.display_name.ilike(match),
            models.HealthcareOrganization.legal_name.ilike(match),
        ))
    organizations = query.order_by(
        models.HealthcareOrganization.display_name.asc(),
    ).offset(offset).limit(limit).all()
    return [_organization_directory_out(organization) for organization in organizations]


@router.get("/organizations/{organization_id}", response_model=schemas.OrganizationDirectoryOut)
def organization_profile(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    organization = db.query(models.HealthcareOrganization).filter(
        models.HealthcareOrganization.id == organization_id,
        models.HealthcareOrganization.status == "APPROVED",
    ).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _organization_directory_out(organization)


@router.post(
    "/provider-applications",
    response_model=schemas.ProviderApplicationOut,
    status_code=201,
)
def submit_provider_application(
    payload: schemas.ProviderApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Platform administrators cannot apply as providers")
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == current_user.id,
    ).with_for_update().first()
    now = datetime.utcnow()
    if provider is None:
        provider = models.HealthcareProvider(
            account_id=current_user.id,
            professional_name=payload.professional_name,
            registration_authority=payload.registration_authority,
            registration_number=payload.registration_number,
            qualifications=payload.qualifications,
            specialization=payload.specialization,
            public_profile=payload.public_profile,
            public_contact_email=(
                str(payload.public_contact_email) if payload.public_contact_email else None
            ),
            status="PENDING",
            fhir_resource_id=current_user.fhir_resource_id,
        )
        db.add(provider)
        db.flush()
    elif provider.status in {"VERIFIED", "SUSPENDED", "UNDER_REVIEW"}:
        raise HTTPException(status_code=409, detail="A provider application is already active or verified")
    else:
        provider.professional_name = payload.professional_name
        provider.registration_authority = payload.registration_authority
        provider.registration_number = payload.registration_number
        provider.qualifications = payload.qualifications
        provider.specialization = payload.specialization
        provider.public_profile = payload.public_profile
        provider.public_contact_email = (
            str(payload.public_contact_email) if payload.public_contact_email else None
        )
        provider.status = "PENDING"
        provider.reviewed_by_id = None
        provider.reviewed_at = None
        provider.decision_reason = None
    duplicate = db.query(models.HealthcareProvider.id).filter(
        models.HealthcareProvider.registration_authority == payload.registration_authority,
        models.HealthcareProvider.registration_number == payload.registration_number,
        models.HealthcareProvider.account_id != current_user.id,
    ).first()
    if duplicate:
        db.rollback()
        raise HTTPException(status_code=409, detail="This registration is already associated with a provider")
    application = models.ProviderApplication(
        provider_id=provider.id,
        applicant_user_id=current_user.id,
        status="PENDING",
        submitted_at=now,
        evidence_references=payload.evidence_references,
    )
    db.add(application)
    db.flush()
    try:
        audit_logger.log_event(db, current_user.id, "PROVIDER_APPLICATION_SUBMITTED", {
            "provider_id": provider.id,
            "application_id": application.id,
        })
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Provider application conflicts with an existing registration") from error
    return _provider_application_out(application, provider)


@router.get("/provider-applications/me", response_model=list[schemas.ProviderApplicationOut])
def my_provider_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.query(
        models.ProviderApplication,
        models.HealthcareProvider,
    ).join(
        models.HealthcareProvider,
        models.HealthcareProvider.id == models.ProviderApplication.provider_id,
    ).filter(
        models.ProviderApplication.applicant_user_id == current_user.id,
    ).order_by(models.ProviderApplication.submitted_at.desc()).all()
    return [_provider_application_out(application, provider) for application, provider in rows]


@router.get("/admin/provider-applications", response_model=list[schemas.ProviderApplicationOut])
def list_provider_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    query = db.query(
        models.ProviderApplication,
        models.HealthcareProvider,
    ).join(
        models.HealthcareProvider,
        models.HealthcareProvider.id == models.ProviderApplication.provider_id,
    )
    if status_filter:
        if status_filter not in {"PENDING", "UNDER_REVIEW", "VERIFIED", "REJECTED"}:
            raise HTTPException(status_code=422, detail="Unsupported application status")
        query = query.filter(models.ProviderApplication.status == status_filter)
    rows = query.order_by(
        models.ProviderApplication.submitted_at.asc(),
    ).offset(offset).limit(limit).all()
    return [_provider_application_out(application, provider) for application, provider in rows]


@router.post(
    "/admin/provider-applications/{application_id}/decision",
    response_model=schemas.ProviderApplicationOut,
)
def decide_provider_application(
    application_id: str,
    payload: schemas.RegistryDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    application = db.query(models.ProviderApplication).filter(
        models.ProviderApplication.id == application_id,
    ).with_for_update().first()
    if application is None:
        raise HTTPException(status_code=404, detail="Provider application not found")
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == application.provider_id,
    ).with_for_update().first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider application not found")
    if application.applicant_user_id == current_user.id or provider.account_id == current_user.id:
        raise HTTPException(status_code=403, detail="Reviewers cannot approve their own application")
    decision = payload.decision
    previous_status = provider.status
    if decision == "UNDER_REVIEW":
        if application.status != "PENDING":
            raise HTTPException(status_code=409, detail="Only pending applications can enter review")
        application.status = "UNDER_REVIEW"
        provider.status = "UNDER_REVIEW"
    elif decision in {"APPROVED", "REJECTED"}:
        if application.status not in {"PENDING", "UNDER_REVIEW"}:
            raise HTTPException(status_code=409, detail="This application has already been decided")
        if decision == "APPROVED" and not (
            provider.registration_authority and provider.registration_number
        ):
            raise HTTPException(status_code=409, detail="Professional registration details are required")
        application.status = "VERIFIED" if decision == "APPROVED" else "REJECTED"
        provider.status = application.status
    elif decision == "SUSPENDED":
        if provider.status != "VERIFIED":
            raise HTTPException(status_code=409, detail="Only verified providers can be suspended")
        provider.status = "SUSPENDED"
    elif decision == "REINSTATED":
        if provider.status != "SUSPENDED":
            raise HTTPException(status_code=409, detail="Only suspended providers can be reinstated")
        provider.status = "VERIFIED"
    provider.reviewed_by_id = current_user.id
    provider.reviewed_at = datetime.utcnow()
    provider.decision_reason = payload.reason
    application.reviewed_by_id = current_user.id
    application.reviewed_at = provider.reviewed_at
    application.decision_reason = payload.reason
    db.add(models.ProviderVerification(
        provider_id=provider.id,
        application_id=application.id,
        reviewer_id=current_user.id,
        decision="VERIFIED" if decision == "APPROVED" else decision,
        method="MANUAL_REVIEW",
        source=None,
        reason=payload.reason,
    ))
    provider_account = db.query(models.User).filter(models.User.id == provider.account_id).first()
    if provider_account:
        queue_fhir_resource(db, "Practitioner", provider.fhir_resource_id or provider.id, fhir_builder.build_healthcare_practitioner(provider, provider_account))
    audit_logger.log_event(db, current_user.id, f"PROVIDER_{decision}", {
        "provider_id": provider.id,
        "application_id": application.id,
        "previous_status": previous_status,
    })
    return _provider_application_out(application, provider)


@router.get("/admin/providers/{provider_id}/history", response_model=list[schemas.RegistryHistoryOut])
def provider_verification_history(
    provider_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    if db.query(models.HealthcareProvider.id).filter(
        models.HealthcareProvider.id == provider_id,
    ).first() is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    decisions = db.query(models.ProviderVerification).filter(
        models.ProviderVerification.provider_id == provider_id,
    ).order_by(
        models.ProviderVerification.created_at.desc(),
    ).offset(offset).limit(limit).all()
    return [{
        "id": item.id,
        "decision": item.decision,
        "reason": item.reason,
        "reviewer_id": item.reviewer_id,
        "created_at": item.created_at,
        "method": item.method,
        "source": item.source,
    } for item in decisions]


@router.get("/providers/me", response_model=schemas.ProviderProfileOut)
def my_provider_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == current_user.id,
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="No provider application exists")
    application = _latest_application(db, models.ProviderApplication, "provider_id", provider.id)
    return {
        "id": provider.id,
        "account_id": provider.account_id,
        "professional_name": provider.professional_name,
        "registration_authority": provider.registration_authority,
        "registration_number": provider.registration_number,
        "qualifications": provider.qualifications or [],
        "specialization": provider.specialization,
        "public_profile": provider.public_profile,
        "public_contact_email": provider.public_contact_email,
        "status": provider.status,
        "fhir_resource_id": provider.fhir_resource_id,
        "submitted_at": application.submitted_at if application else None,
        "decision_reason": provider.decision_reason,
    }


@router.get("/providers", response_model=list[schemas.ProviderDirectoryOut])
def provider_directory(
    query_text: str | None = Query(default=None, min_length=1, max_length=120, alias="q"),
    specialization: str | None = Query(default=None, min_length=1, max_length=120),
    organization_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.utcnow()
    eligible = db.query(models.OrganizationAffiliation.provider_id).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
    ).filter(
        models.OrganizationAffiliation.status == "ACTIVE",
        models.HealthcareOrganization.status == "APPROVED",
        or_(models.OrganizationAffiliation.effective_from.is_(None),
            models.OrganizationAffiliation.effective_from <= now),
        or_(models.OrganizationAffiliation.effective_until.is_(None),
            models.OrganizationAffiliation.effective_until > now),
    )
    if organization_id:
        eligible = eligible.filter(
            models.OrganizationAffiliation.organization_id == organization_id,
        )
    eligible_ids = eligible.distinct().subquery()
    query = db.query(models.HealthcareProvider).join(
        eligible_ids,
        eligible_ids.c.provider_id == models.HealthcareProvider.id,
    ).filter(
        models.HealthcareProvider.status == "VERIFIED",
        models.HealthcareProvider.registration_authority.is_not(None),
        models.HealthcareProvider.registration_number.is_not(None),
    )
    if specialization:
        query = query.filter(models.HealthcareProvider.specialization.ilike(f"%{specialization.strip()}%"))
    if query_text:
        match = f"%{query_text.strip()}%"
        query = query.filter(or_(
            models.HealthcareProvider.professional_name.ilike(match),
            models.HealthcareProvider.registration_number.ilike(match),
            models.HealthcareProvider.specialization.ilike(match),
        ))
    providers = query.order_by(
        models.HealthcareProvider.professional_name.asc(),
    ).offset(offset).limit(limit).all()
    result = []
    for provider in providers:
        affiliations = db.query(
            models.OrganizationAffiliation,
            models.HealthcareOrganization,
        ).join(
            models.HealthcareOrganization,
            models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
        ).filter(
            models.OrganizationAffiliation.provider_id == provider.id,
            models.OrganizationAffiliation.status == "ACTIVE",
            models.HealthcareOrganization.status == "APPROVED",
            or_(models.OrganizationAffiliation.effective_from.is_(None),
                models.OrganizationAffiliation.effective_from <= now),
            or_(models.OrganizationAffiliation.effective_until.is_(None),
                models.OrganizationAffiliation.effective_until > now),
        ).all()
        result.append({
            "id": provider.id,
            "professional_name": provider.professional_name,
            "qualifications": provider.qualifications or [],
            "specialization": provider.specialization,
            "public_profile": provider.public_profile,
            "public_contact_email": provider.public_contact_email,
            "registration_authority": provider.registration_authority,
            "registration_number": provider.registration_number,
            "organizations": [_organization_directory_out(org) for _, org in affiliations],
        })
    return result


@router.get("/providers/{provider_id}", response_model=schemas.ProviderDirectoryOut)
def provider_directory_profile(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.utcnow()
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == provider_id,
        models.HealthcareProvider.status == "VERIFIED",
        models.HealthcareProvider.registration_authority.is_not(None),
        models.HealthcareProvider.registration_number.is_not(None),
        db.query(models.OrganizationAffiliation.id).join(
            models.HealthcareOrganization,
            models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
        ).filter(
            models.OrganizationAffiliation.provider_id == models.HealthcareProvider.id,
            models.OrganizationAffiliation.status == "ACTIVE",
            models.HealthcareOrganization.status == "APPROVED",
            or_(models.OrganizationAffiliation.effective_from.is_(None),
                models.OrganizationAffiliation.effective_from <= now),
            or_(models.OrganizationAffiliation.effective_until.is_(None),
                models.OrganizationAffiliation.effective_until > now),
        ).exists(),
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    affiliations = db.query(
        models.OrganizationAffiliation,
        models.HealthcareOrganization,
    ).join(
        models.HealthcareOrganization,
        models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
    ).filter(
        models.OrganizationAffiliation.provider_id == provider.id,
        models.OrganizationAffiliation.status == "ACTIVE",
        models.HealthcareOrganization.status == "APPROVED",
        or_(models.OrganizationAffiliation.effective_from.is_(None),
            models.OrganizationAffiliation.effective_from <= now),
        or_(models.OrganizationAffiliation.effective_until.is_(None),
            models.OrganizationAffiliation.effective_until > now),
    ).all()
    return {
        "id": provider.id,
        "professional_name": provider.professional_name,
        "qualifications": provider.qualifications or [],
        "specialization": provider.specialization,
        "public_profile": provider.public_profile,
        "public_contact_email": provider.public_contact_email,
        "registration_authority": provider.registration_authority,
        "registration_number": provider.registration_number,
        "organizations": [_organization_directory_out(org) for _, org in affiliations],
    }


@router.get("/my/organizations", response_model=list[schemas.OrganizationDirectoryOut])
def my_managed_organizations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    organizations = db.query(models.HealthcareOrganization).join(
        models.OrganizationRoleAssignment,
        models.OrganizationRoleAssignment.organization_id == models.HealthcareOrganization.id,
    ).filter(
        models.OrganizationRoleAssignment.user_id == current_user.id,
        models.OrganizationRoleAssignment.role == "ORGANIZATION_ADMIN",
        models.OrganizationRoleAssignment.revoked_at.is_(None),
    ).order_by(models.HealthcareOrganization.display_name.asc()).all()
    return [_organization_directory_out(item) for item in organizations]


@router.get(
    "/organizations/{organization_id}/provider-candidates",
    response_model=list[schemas.ProviderDirectoryOut],
)
def list_provider_candidates(
    organization_id: str,
    query_text: str | None = Query(default=None, min_length=1, max_length=120, alias="q"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_organization_admin(db, current_user, organization_id)
    existing_affiliations = db.query(models.OrganizationAffiliation.provider_id).filter(
        models.OrganizationAffiliation.organization_id == organization_id,
        models.OrganizationAffiliation.status.in_(("INVITED", "PENDING", "ACTIVE", "SUSPENDED")),
    )
    query = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.status == "VERIFIED",
        models.HealthcareProvider.registration_authority.is_not(None),
        models.HealthcareProvider.registration_number.is_not(None),
        ~existing_affiliations.filter(
            models.OrganizationAffiliation.provider_id == models.HealthcareProvider.id,
        ).exists(),
    )
    if query_text:
        match = f"%{query_text.strip()}%"
        query = query.filter(or_(
            models.HealthcareProvider.professional_name.ilike(match),
            models.HealthcareProvider.registration_number.ilike(match),
            models.HealthcareProvider.specialization.ilike(match),
        ))
    providers = query.order_by(
        models.HealthcareProvider.professional_name.asc(),
    ).offset(offset).limit(limit).all()
    result = []
    now = datetime.utcnow()
    for provider in providers:
        affiliations = db.query(
            models.OrganizationAffiliation,
            models.HealthcareOrganization,
        ).join(
            models.HealthcareOrganization,
            models.HealthcareOrganization.id == models.OrganizationAffiliation.organization_id,
        ).filter(
            models.OrganizationAffiliation.provider_id == provider.id,
            models.OrganizationAffiliation.status == "ACTIVE",
            models.HealthcareOrganization.status == "APPROVED",
            or_(models.OrganizationAffiliation.effective_from.is_(None),
                models.OrganizationAffiliation.effective_from <= now),
            or_(models.OrganizationAffiliation.effective_until.is_(None),
                models.OrganizationAffiliation.effective_until > now),
        ).all()
        result.append({
            "id": provider.id,
            "professional_name": provider.professional_name,
            "qualifications": provider.qualifications or [],
            "specialization": provider.specialization,
            "public_profile": provider.public_profile,
            "public_contact_email": provider.public_contact_email,
            "registration_authority": provider.registration_authority,
            "registration_number": provider.registration_number,
            "organizations": [_organization_directory_out(org) for _, org in affiliations],
        })
    return result


@router.get("/organizations/{organization_id}/affiliations", response_model=list[schemas.AffiliationOut])
def list_organization_affiliations(
    organization_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_organization_admin(db, current_user, organization_id)
    query = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.organization_id == organization_id,
    )
    if status_filter:
        if status_filter not in {"INVITED", "PENDING", "ACTIVE", "REJECTED", "SUSPENDED", "ENDED"}:
            raise HTTPException(status_code=422, detail="Unsupported affiliation status")
        query = query.filter(models.OrganizationAffiliation.status == status_filter)
    affiliations = query.order_by(
        models.OrganizationAffiliation.invited_at.desc(),
    ).offset(offset).limit(limit).all()
    return [_affiliation_out(db, item) for item in affiliations]


@router.post(
    "/organizations/{organization_id}/affiliations",
    response_model=schemas.AffiliationOut,
    status_code=201,
)
def invite_provider(
    organization_id: str,
    payload: schemas.AffiliationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_organization_admin(db, current_user, organization_id)
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.id == payload.provider_id,
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    active = db.query(models.OrganizationAffiliation.id).filter(
        models.OrganizationAffiliation.organization_id == organization_id,
        models.OrganizationAffiliation.provider_id == provider.id,
        models.OrganizationAffiliation.status.in_(("INVITED", "PENDING", "ACTIVE", "SUSPENDED")),
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="An active or pending affiliation already exists")
    affiliation = models.OrganizationAffiliation(
        organization_id=organization_id,
        provider_id=provider.id,
        account_id=provider.account_id,
        organization_role=payload.organization_role,
        status="INVITED",
        invited_by_id=current_user.id,
        invitation_message=payload.invitation_message,
    )
    db.add(affiliation)
    db.flush()
    add_affiliation_event(db, affiliation, current_user.id, None, "INVITED", "Organization invitation sent")
    audit_logger.log_event(db, current_user.id, "ORGANIZATION_AFFILIATION_INVITED", {
        "organization_id": organization_id,
        "provider_id": provider.id,
        "affiliation_id": affiliation.id,
    })
    return _affiliation_out(db, affiliation)


@router.get("/providers/me/affiliations", response_model=list[schemas.AffiliationOut])
def my_affiliations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    provider = db.query(models.HealthcareProvider).filter(
        models.HealthcareProvider.account_id == current_user.id,
    ).first()
    if provider is None:
        return []
    affiliations = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.provider_id == provider.id,
    ).order_by(models.OrganizationAffiliation.invited_at.desc()).all()
    return [_affiliation_out(db, item) for item in affiliations]


@router.post("/affiliations/{affiliation_id}/response", response_model=schemas.AffiliationOut)
def respond_to_affiliation(
    affiliation_id: str,
    payload: schemas.AffiliationResponse,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    affiliation = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.id == affiliation_id,
        models.OrganizationAffiliation.account_id == current_user.id,
    ).with_for_update().first()
    if affiliation is None:
        raise HTTPException(status_code=404, detail="Affiliation invitation not found")
    if affiliation.status != "INVITED":
        raise HTTPException(status_code=409, detail="This affiliation invitation is no longer pending")
    previous = affiliation.status
    affiliation.accepted_at = datetime.utcnow()
    affiliation.status = payload.decision
    reason = payload.reason
    if payload.decision == "ACCEPTED":
        affiliation.status = "PENDING"
        reason = "Provider accepted organization invitation"
    else:
        affiliation.status = "REJECTED"
    affiliation.decision_by_id = current_user.id
    affiliation.decided_at = datetime.utcnow()
    affiliation.decision_reason = reason
    add_affiliation_event(db, affiliation, current_user.id, previous, affiliation.status, reason)
    audit_logger.log_event(db, current_user.id, "PROVIDER_AFFILIATION_RESPONSE", {
        "organization_id": affiliation.organization_id,
        "provider_id": affiliation.provider_id,
        "affiliation_id": affiliation.id,
        "status": affiliation.status,
    })
    return _affiliation_out(db, affiliation)


@router.post(
    "/organizations/{organization_id}/affiliations/{affiliation_id}/decision",
    response_model=schemas.AffiliationOut,
)
def decide_affiliation(
    organization_id: str,
    affiliation_id: str,
    payload: schemas.AffiliationDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    require_organization_admin(db, current_user, organization_id)
    affiliation = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.id == affiliation_id,
        models.OrganizationAffiliation.organization_id == organization_id,
    ).with_for_update().first()
    if affiliation is None:
        raise HTTPException(status_code=404, detail="Affiliation not found")
    previous = affiliation.status
    decision = payload.decision
    if decision == "APPROVED":
        if previous not in {"PENDING", "SUSPENDED"}:
            raise HTTPException(status_code=409, detail="Only pending or suspended affiliations can be activated")
        provider = db.query(models.HealthcareProvider).filter(
            models.HealthcareProvider.id == affiliation.provider_id,
            models.HealthcareProvider.status == "VERIFIED",
        ).first()
        if provider is None:
            raise HTTPException(status_code=409, detail="Only verified providers can be activated")
        affiliation.status = "ACTIVE"
        affiliation.effective_from = datetime.utcnow()
        affiliation.effective_until = None
    elif decision == "REJECTED":
        if previous not in {"INVITED", "PENDING"}:
            raise HTTPException(status_code=409, detail="This affiliation can no longer be rejected")
        affiliation.status = "REJECTED"
    elif decision == "SUSPENDED":
        if previous != "ACTIVE":
            raise HTTPException(status_code=409, detail="Only active affiliations can be suspended")
        affiliation.status = "SUSPENDED"
    elif decision == "ENDED":
        if previous not in {"ACTIVE", "SUSPENDED"}:
            raise HTTPException(status_code=409, detail="Only active affiliations can be ended")
        affiliation.status = "ENDED"
        affiliation.effective_until = datetime.utcnow()
    affiliation.decision_by_id = current_user.id
    affiliation.decided_at = datetime.utcnow()
    affiliation.decision_reason = payload.reason
    affiliation.updated_at = datetime.utcnow()
    add_affiliation_event(db, affiliation, current_user.id, previous, affiliation.status, payload.reason)
    organization = db.query(models.HealthcareOrganization).filter(models.HealthcareOrganization.id == organization_id).first()
    provider = db.query(models.HealthcareProvider).filter(models.HealthcareProvider.id == affiliation.provider_id).first()
    if organization and provider:
        queue_fhir_resource(db, "PractitionerRole", affiliation.id, fhir_builder.build_practitioner_role(affiliation, provider, organization))
    audit_logger.log_event(db, current_user.id, f"ORGANIZATION_AFFILIATION_{affiliation.status}", {
        "organization_id": organization_id,
        "provider_id": affiliation.provider_id,
        "affiliation_id": affiliation.id,
        "previous_status": previous,
    })
    return _affiliation_out(db, affiliation)


@router.get("/affiliations/{affiliation_id}/history", response_model=list[schemas.RegistryHistoryOut])
def affiliation_history(
    affiliation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    affiliation = db.query(models.OrganizationAffiliation).filter(
        models.OrganizationAffiliation.id == affiliation_id,
    ).first()
    if affiliation is None:
        raise HTTPException(status_code=404, detail="Affiliation not found")
    is_provider = affiliation.account_id == current_user.id
    is_admin = _active_assignment(
        db, current_user.id, affiliation.organization_id,
    )
    is_platform_admin = current_user.role == "admin"
    if not (is_provider or is_admin or is_platform_admin):
        raise HTTPException(status_code=404, detail="Affiliation not found")
    events = db.query(models.OrganizationAffiliationEvent).filter(
        models.OrganizationAffiliationEvent.affiliation_id == affiliation.id,
    ).order_by(
        models.OrganizationAffiliationEvent.created_at.desc(),
    ).offset(offset).limit(limit).all()
    return [{
        "id": event.id,
        "decision": event.to_status,
        "reason": event.reason,
        "reviewer_id": event.actor_id,
        "created_at": event.created_at,
    } for event in events]


@router.get("/admin/affiliations", response_model=list[schemas.AffiliationOut])
def admin_affiliation_oversight(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    query = db.query(models.OrganizationAffiliation)
    if status_filter:
        if status_filter not in {"INVITED", "PENDING", "ACTIVE", "REJECTED", "SUSPENDED", "ENDED"}:
            raise HTTPException(status_code=422, detail="Unsupported affiliation status")
        query = query.filter(models.OrganizationAffiliation.status == status_filter)
    affiliations = query.order_by(
        models.OrganizationAffiliation.invited_at.desc(),
    ).offset(offset).limit(limit).all()
    return [_affiliation_out(db, item) for item in affiliations]
