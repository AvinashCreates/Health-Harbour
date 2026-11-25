import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, Column, String, DateTime, ForeignKey, JSON, Integer, UniqueConstraint
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)


class Consent(Base):
    __tablename__ = "consents"
    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("users.id"), nullable=False)
    grantee_id = Column(String, ForeignKey("users.id"), nullable=False)
    resource_types = Column(JSON, nullable=False)  # list[str]
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


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
