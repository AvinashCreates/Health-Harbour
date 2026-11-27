import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, text
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)  # patient | doctor | lab | admin
    identity_subject = Column(String, unique=True, nullable=True, index=True)
    fhir_resource_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FHIRResource(Base):
    """Generic store for FHIR resources (Patient, Practitioner, ServiceRequest,
    Specimen, Observation, DiagnosticReport). resource_data holds the actual
    FHIR R4 JSON; the other columns are indexes/ownership metadata used for
    access control and are not themselves part of the FHIR resource."""
    __tablename__ = "fhir_resources"
    id = Column(String, primary_key=True, default=gen_uuid)
    resource_type = Column(String, nullable=False, index=True)
    fhir_id = Column(String, nullable=False, index=True)
    resource_data = Column(JSON, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)  # the patient this resource is about
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClinicalFile(Base):
    __tablename__ = "clinical_files"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_clinical_file_size_positive"),
        CheckConstraint("size_bytes <= 10485760", name="ck_clinical_file_size_limit"),
        CheckConstraint(
            "processing_status IN ('RECEIVED', 'QUARANTINED', 'SCANNING', 'CLEAN', 'REJECTED', 'SCAN_FAILED')",
            name="ck_clinical_file_processing_status",
        ),
        CheckConstraint(
            "scan_status IN ('NOT_REQUIRED', 'CLEAN', 'MALICIOUS', 'UNSUPPORTED', 'UNAVAILABLE', 'TIMEOUT')",
            name="ck_clinical_file_scan_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    service_request_id = Column(String, ForeignKey("fhir_resources.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False, unique=True)
    media_type = Column(String, nullable=False)
    category = Column(String, nullable=False, default="clinical-record")
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String, nullable=False)
    processing_status = Column(String(24), nullable=False, default="CLEAN", server_default=text("'CLEAN'"), index=True)
    scan_status = Column(String(24), nullable=False, default="NOT_REQUIRED", server_default=text("'NOT_REQUIRED'"), index=True)
    scan_detail = Column(String(500), nullable=True)
    encryption_version = Column(String(16), nullable=True)
    encryption_key_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)


class Consent(Base):
    __tablename__ = "consents"
    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    grantee_id = Column(String, ForeignKey("users.id"), nullable=False)
    organization_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    resource_types = Column(JSON, nullable=False)  # list[str]
    purpose = Column(String, nullable=False, default="TREATMENT", server_default=text("'TREATMENT'"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "practitioner_id", name="uq_org_practitioner"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    practitioner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LaboratoryWorkflow(Base):
    __tablename__ = "laboratory_workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('REQUESTED', 'ACCEPTED', 'ASSIGNED', 'SPECIMEN_REGISTERED', "
            "'PROCESSING', 'RESULTS_SUBMITTED', 'FINALIZED', 'PHYSICIAN_REVIEWED')",
            name="ck_laboratory_workflow_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    service_request_id = Column(String, ForeignKey("fhir_resources.id"), nullable=False, unique=True, index=True)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    physician_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    laboratory_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    technician_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    specimen_fhir_id = Column(String, nullable=True)
    report_fhir_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="REQUESTED", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String, ForeignKey("laboratory_workflows.id"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    from_status = Column(String, nullable=False)
    to_status = Column(String, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class LaboratoryMembership(Base):
    __tablename__ = "laboratory_memberships"
    __table_args__ = (
        UniqueConstraint("laboratory_id", "technician_id", name="uq_laboratory_technician"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    laboratory_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    technician_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_id", "idempotency_key", name="uq_actor_idempotency_key"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    idempotency_key = Column(String, nullable=False)
    request_fingerprint = Column(String, nullable=False)
    service_request_id = Column(String, ForeignKey("fhir_resources.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LoginRateLimit(Base):
    __tablename__ = "login_rate_limits"
    key_hash = Column(String, primary_key=True)
    failure_count = Column(Integer, nullable=False)
    window_started_at = Column(DateTime, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class LedgerOutbox(Base):
    __tablename__ = "ledger_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'COMMITTED', 'FAILED')",
            name="ck_ledger_outbox_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    event_type = Column(String, nullable=False, index=True)
    event_payload = Column(JSON, nullable=False)
    payload_hash = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="PENDING", index=True)
    transaction_id = Column(String, nullable=True, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    committed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Append-only, hash-chained event log. Each row's curr_hash commits to
    the previous row's hash plus this row's content, so altering any past
    row breaks the chain from that point forward -- the tamper-evidence
    property real blockchains provide, demonstrated here without a
    multi-peer distributed ledger. See services/audit_logger.py."""
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, nullable=False)
    event_payload = Column(JSON, nullable=False)
    prev_hash = Column(String, nullable=False)
    curr_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealthcareOrganization(Base):
    __tablename__ = "healthcare_organizations"
    __table_args__ = (
        CheckConstraint(
            "organization_type IN ('HOSPITAL', 'CLINIC', 'DIAGNOSTIC_LABORATORY', 'OTHER')",
            name="ck_healthcare_organization_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED')",
            name="ck_healthcare_organization_status",
        ),
        UniqueConstraint(
            "registration_authority",
            "registration_identifier",
            name="uq_healthcare_organization_registration",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    legacy_user_id = Column(String, ForeignKey("users.id"), nullable=True, unique=True)
    legal_name = Column(String(200), nullable=False)
    display_name = Column(String(160), nullable=False)
    organization_type = Column(String(32), nullable=False)
    registration_authority = Column(String(160), nullable=True)
    registration_identifier = Column(String(160), nullable=True)
    address = Column(JSON, nullable=False, default=dict)
    contact_email = Column(String(254), nullable=True)
    contact_phone = Column(String(40), nullable=True)
    administrative_contact_name = Column(String(120), nullable=False)
    administrative_contact_email = Column(String(254), nullable=False)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    fhir_resource_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_reason = Column(String(1000), nullable=True)


class OrganizationApplication(Base):
    __tablename__ = "organization_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED')",
            name="ck_organization_application_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    applicant_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_reason = Column(String(1000), nullable=True)
    evidence_references = Column(JSON, nullable=False, default=list)


class OrganizationReviewDecision(Base):
    __tablename__ = "organization_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('UNDER_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED', 'REINSTATED')",
            name="ck_organization_review_decision",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("organization_applications.id"), nullable=True, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    decision = Column(String(24), nullable=False)
    reason = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class HealthcareProvider(Base):
    __tablename__ = "healthcare_providers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED', 'SUSPENDED')",
            name="ck_healthcare_provider_status",
        ),
        UniqueConstraint(
            "registration_authority",
            "registration_number",
            name="uq_healthcare_provider_registration",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    account_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    professional_name = Column(String(160), nullable=False)
    registration_authority = Column(String(160), nullable=True)
    registration_number = Column(String(120), nullable=True)
    qualifications = Column(JSON, nullable=False, default=list)
    specialization = Column(String(120), nullable=True)
    public_profile = Column(String(1000), nullable=True)
    public_contact_email = Column(String(254), nullable=True)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    fhir_resource_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_reason = Column(String(1000), nullable=True)


class ProviderApplication(Base):
    __tablename__ = "provider_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED')",
            name="ck_provider_application_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    provider_id = Column(String, ForeignKey("healthcare_providers.id"), nullable=False, index=True)
    applicant_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_reason = Column(String(1000), nullable=True)
    evidence_references = Column(JSON, nullable=False, default=list)


class ProviderVerification(Base):
    __tablename__ = "provider_verifications"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('UNDER_REVIEW', 'VERIFIED', 'REJECTED', 'SUSPENDED', 'REINSTATED')",
            name="ck_provider_verification_decision",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    provider_id = Column(String, ForeignKey("healthcare_providers.id"), nullable=False, index=True)
    application_id = Column(String, ForeignKey("provider_applications.id"), nullable=True, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    decision = Column(String(24), nullable=False)
    method = Column(String(40), nullable=False, default="MANUAL_REVIEW")
    source = Column(String(200), nullable=True)
    reason = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class OrganizationAffiliation(Base):
    __tablename__ = "organization_affiliations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('INVITED', 'PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED', 'ENDED')",
            name="ck_organization_affiliation_status",
        ),
        Index(
            "ix_org_affiliation_org_provider_status",
            "organization_id",
            "provider_id",
            "status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    provider_id = Column(String, ForeignKey("healthcare_providers.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    organization_role = Column(String(40), nullable=False, default="PROVIDER")
    status = Column(String(24), nullable=False, default="INVITED", index=True)
    invited_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    invitation_message = Column(String(500), nullable=True)
    decision_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    decision_reason = Column(String(1000), nullable=True)
    invited_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OrganizationRoleAssignment(Base):
    __tablename__ = "organization_role_assignments"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ORGANIZATION_ADMIN', 'ORGANIZATION_STAFF')",
            name="ck_organization_role_assignment_role",
        ),
        Index(
            "ix_org_role_assignment_scope",
            "organization_id",
            "user_id",
            "role",
            "revoked_at",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    granted_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class OrganizationAffiliationEvent(Base):
    __tablename__ = "organization_affiliation_events"
    __table_args__ = (
        CheckConstraint(
            "to_status IN ('INVITED', 'PENDING', 'ACTIVE', 'REJECTED', 'SUSPENDED', 'ENDED')",
            name="ck_organization_affiliation_event_status",
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    affiliation_id = Column(String, ForeignKey("organization_affiliations.id"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    from_status = Column(String(24), nullable=True)
    to_status = Column(String(24), nullable=False)
    reason = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class CareConnection(Base):
    __tablename__ = "care_connections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('INITIATED', 'ACCEPTED', 'DECLINED', 'CLOSED')",
            name="ck_care_connection_status",
        ),
        UniqueConstraint(
            "patient_id", "provider_id", "organization_id",
            name="uq_care_connection_patient_provider_org",
        ),
        Index("ix_care_connection_patient_status", "patient_id", "status"),
        Index("ix_care_connection_provider_status", "provider_id", "status"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(String, ForeignKey("healthcare_providers.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="INITIATED", index=True)
    reason = Column(String(1000), nullable=False)
    provider_response = Column(String(1000), nullable=True)
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)


class ProviderRecordRequest(Base):
    __tablename__ = "provider_record_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_provider_record_request_status",
        ),
        Index("ix_record_request_patient_status", "patient_id", "status"),
        Index("ix_record_request_provider_status", "provider_id", "status"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider_id = Column(String, ForeignKey("healthcare_providers.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("healthcare_organizations.id"), nullable=False, index=True)
    resource_types = Column(JSON, nullable=False, default=list)
    purpose = Column(String(24), nullable=False, default="TREATMENT")
    requested_duration_days = Column(Integer, nullable=False)
    reason = Column(String(1000), nullable=False)
    status = Column(String(24), nullable=False, default="REQUESTED", index=True)
    response_reason = Column(String(1000), nullable=True)
    consent_id = Column(String, ForeignKey("consents.id"), nullable=True, index=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)
