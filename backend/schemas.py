from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

RoleLiteral = Literal["patient", "doctor", "lab", "lab_technician", "lab_supervisor", "admin"]
FHIRResourceType = Literal[
    "Patient",
    "Practitioner",
    "Organization",
    "Document",
    "ServiceRequest",
    "Specimen",
    "Observation",
    "DiagnosticReport",
]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, strip_whitespace=True)
    email: EmailStr
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)
    role: RoleLiteral
    identity_subject: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class PublicUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=120, strip_whitespace=True)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ServiceRequestCreate(BaseModel):
    patient_email: EmailStr
    lab_email: EmailStr
    test_code: str = Field(default="24323-8", min_length=1, max_length=40)
    test_display: str = Field(default="Comprehensive metabolic panel", min_length=1, max_length=160)
    note: Optional[str] = Field(default=None, max_length=500)


class ObservationIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    display: str = Field(min_length=1, max_length=160)
    value: float
    unit: str = Field(min_length=1, max_length=40)


class DiagnosticReportCreate(BaseModel):
    service_request_id: str
    observations: List[ObservationIn] = Field(min_length=1, max_length=50)
    conclusion: str = Field(min_length=1, max_length=2000)


class DiagnosticReportAmendment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conclusion: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class TechnicianAssignment(BaseModel):
    technician_email: EmailStr


class LaboratoryMembershipCreate(BaseModel):
    laboratory_email: EmailStr
    technician_email: EmailStr


class SpecimenCreate(BaseModel):
    type_code: str = Field(default="122555007", min_length=1, max_length=40)
    type_display: str = Field(default="Venous blood specimen", min_length=1, max_length=160)


class ConsentGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doctor_email: EmailStr
    organization_id: str | None = Field(default=None, min_length=1, max_length=255)
    resource_types: List[FHIRResourceType] = Field(
        default_factory=lambda: ["Patient", "ServiceRequest", "Observation", "DiagnosticReport"],
        min_length=1,
    )
    duration_days: int = Field(default=30, ge=1, le=30)

class OrganizationPractitionerCreate(BaseModel):
    organization_email: EmailStr
    practitioner_email: EmailStr


class OrganizationMembershipOut(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    practitioner_id: str
    practitioner_name: str
    active: bool


class ConsentOut(BaseModel):
    id: str
    patient_id: str
    grantee_id: str
    organization_id: Optional[str] = None
    purpose: str = "TREATMENT"
    resource_types: List[str]
    granted_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool


OrganizationType = Literal["HOSPITAL", "CLINIC", "DIAGNOSTIC_LABORATORY", "OTHER"]
OrganizationStatus = Literal["PENDING", "UNDER_REVIEW", "APPROVED", "REJECTED", "SUSPENDED"]
ProviderStatus = Literal["PENDING", "UNDER_REVIEW", "VERIFIED", "REJECTED", "SUSPENDED"]


class OrganizationApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=2, max_length=200, strip_whitespace=True)
    display_name: str = Field(min_length=2, max_length=160, strip_whitespace=True)
    organization_type: OrganizationType
    registration_authority: str | None = Field(default=None, max_length=160, strip_whitespace=True)
    registration_identifier: str | None = Field(default=None, max_length=160, strip_whitespace=True)
    address: Dict[str, str] = Field(default_factory=dict, max_length=12)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40, strip_whitespace=True)
    administrative_contact_name: str = Field(min_length=2, max_length=120, strip_whitespace=True)
    administrative_contact_email: EmailStr
    evidence_references: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_references")
    @classmethod
    def evidence_references_are_opaque(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or len(value) > 160 or "://" in value or value.startswith("/"):
                raise ValueError("Evidence references must be opaque identifiers, not URLs or paths")
        return values


class OrganizationApplicationOut(BaseModel):
    id: str
    organization_id: str
    legal_name: str
    display_name: str
    organization_type: str
    registration_authority: str | None
    registration_identifier: str | None
    address: Dict[str, str]
    contact_email: str | None
    contact_phone: str | None
    administrative_contact_name: str
    administrative_contact_email: str
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None
    decision_reason: str | None
    evidence_references: List[str]


class OrganizationDirectoryOut(BaseModel):
    id: str
    legal_name: str
    display_name: str
    organization_type: str
    registration_authority: str | None
    registration_identifier: str | None
    address: Dict[str, str]
    contact_email: str | None


class RegistryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["UNDER_REVIEW", "APPROVED", "REJECTED", "SUSPENDED", "REINSTATED"]
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class ProviderApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    professional_name: str = Field(min_length=2, max_length=160, strip_whitespace=True)
    registration_authority: str = Field(min_length=2, max_length=160, strip_whitespace=True)
    registration_number: str = Field(min_length=2, max_length=120, strip_whitespace=True)
    qualifications: List[str] = Field(min_length=1, max_length=12)
    specialization: str | None = Field(default=None, max_length=120, strip_whitespace=True)
    public_profile: str | None = Field(default=None, max_length=1000, strip_whitespace=True)
    public_contact_email: EmailStr | None = None
    evidence_references: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("qualifications")
    @classmethod
    def validate_qualifications(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 120 for value in values):
            raise ValueError("Qualifications must be between 1 and 120 characters")
        return [value.strip() for value in values]

    @field_validator("evidence_references")
    @classmethod
    def evidence_references_are_opaque(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value or len(value) > 160 or "://" in value or value.startswith("/"):
                raise ValueError("Evidence references must be opaque identifiers, not URLs or paths")
        return values


class ProviderApplicationOut(BaseModel):
    id: str
    provider_id: str
    professional_name: str
    registration_authority: str | None
    registration_number: str | None
    qualifications: List[str]
    specialization: str | None
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None
    decision_reason: str | None
    evidence_references: List[str] | None = None


class ProviderDirectoryOut(BaseModel):
    id: str
    professional_name: str
    qualifications: List[str]
    specialization: str | None
    public_profile: str | None
    public_contact_email: str | None
    registration_authority: str
    registration_number: str
    organizations: List[OrganizationDirectoryOut]


class AffiliationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(min_length=1, max_length=64)
    organization_role: Literal["PROVIDER"] = "PROVIDER"
    invitation_message: str | None = Field(default=None, max_length=500)


class AffiliationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVED", "REJECTED", "SUSPENDED", "ENDED"]
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class AffiliationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["ACCEPTED", "REJECTED"]
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class AffiliationOut(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    provider_id: str
    professional_name: str
    organization_role: str
    status: str
    invited_at: datetime
    accepted_at: datetime | None
    effective_from: datetime | None
    effective_until: datetime | None
    decided_at: datetime | None
    decision_reason: str | None


class ProviderProfileOut(BaseModel):
    id: str
    account_id: str
    professional_name: str
    registration_authority: str | None
    registration_number: str | None
    qualifications: List[str]
    specialization: str | None
    public_profile: str | None
    public_contact_email: str | None
    status: str
    fhir_resource_id: str | None
    submitted_at: datetime | None
    decision_reason: str | None


class CrossHospitalExchangeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=64)
    requesting_organization_id: str = Field(min_length=1, max_length=64)
    source_organization_id: str = Field(min_length=1, max_length=64)
    resource_types: List[FHIRResourceType] = Field(min_length=1, max_length=8)
    requested_duration_days: int = Field(ge=1, le=30)
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class CrossHospitalExchangeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVED", "REJECTED", "REVOKED"]
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class CrossHospitalExchangeOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    requesting_organization_id: str
    requesting_organization_name: str
    requesting_provider_id: str
    requesting_provider_name: str
    source_organization_id: str
    source_organization_name: str
    resource_types: List[str]
    purpose: str
    requested_duration_days: int
    reason: str
    status: str
    consent_id: str | None
    response_reason: str | None
    requested_at: datetime
    responded_at: datetime | None
    expires_at: datetime | None


class CrossOrganizationDocumentImportOut(BaseModel):
    id: str
    exchange_request_id: str
    source_document_id: str
    source_organization_id: str
    receiving_organization_id: str
    importing_provider_id: str
    consent_id: str
    checksum: str
    integrity_verified: bool
    status: str
    failure_reason: str | None
    imported_at: datetime | None
    created_at: datetime


class PrescriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=64)
    organization_id: str = Field(min_length=1, max_length=64)
    medication_name: str = Field(min_length=2, max_length=200, strip_whitespace=True)
    dosage: str = Field(min_length=1, max_length=120, strip_whitespace=True)
    route: str | None = Field(default=None, max_length=80, strip_whitespace=True)
    frequency: str = Field(min_length=1, max_length=120, strip_whitespace=True)
    duration: str | None = Field(default=None, max_length=120, strip_whitespace=True)
    quantity: str | None = Field(default=None, max_length=120, strip_whitespace=True)
    instructions: str | None = Field(default=None, max_length=1000, strip_whitespace=True)
    activate: bool = True


class PrescriptionTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ACTIVE", "CANCELLED", "COMPLETED", "STOPPED"]
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class PrescriptionOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    provider_id: str
    provider_name: str
    organization_id: str
    organization_name: str
    medication_name: str
    dosage: str
    route: str | None
    frequency: str
    duration: str | None
    quantity: str | None
    instructions: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class PhysicianClinicalReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=64)
    organization_id: str = Field(min_length=1, max_length=64)
    diagnostic_report_id: str | None = Field(default=None, max_length=64)
    service_request_id: str | None = Field(default=None, max_length=64)
    status: Literal["REVIEWED", "FOLLOW_UP_REQUIRED"]
    clinical_note: str | None = Field(default=None, max_length=2000, strip_whitespace=True)


class PhysicianClinicalReviewOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    provider_id: str
    provider_name: str
    organization_id: str
    organization_name: str
    diagnostic_report_id: str | None
    service_request_id: str | None
    status: str
    clinical_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class RegistryHistoryOut(BaseModel):
    id: str
    decision: str
    reason: str
    reviewer_id: str
    created_at: datetime
    method: str | None = None
    source: str | None = None


class CareConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str = Field(min_length=1, max_length=64)
    organization_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class CareConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["ACCEPTED", "DECLINED", "CLOSED"]
    response: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class CareConnectionOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    provider_id: str
    provider_name: str
    organization_id: str
    organization_name: str
    status: str
    reason: str
    provider_response: str | None
    initiated_at: datetime
    responded_at: datetime | None
    closed_at: datetime | None


class ProviderRecordRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str = Field(min_length=1, max_length=64)
    organization_id: str = Field(min_length=1, max_length=64)
    resource_types: List[FHIRResourceType] = Field(min_length=1, max_length=8)
    requested_duration_days: int = Field(ge=1, le=30)
    reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class ProviderRecordRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVED", "REJECTED"]
    response_reason: str = Field(min_length=3, max_length=1000, strip_whitespace=True)


class ProviderRecordRequestOut(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    provider_id: str
    provider_name: str
    organization_id: str
    organization_name: str
    resource_types: List[str]
    purpose: str
    requested_duration_days: int
    reason: str
    status: str
    response_reason: str | None
    consent_id: str | None
    requested_at: datetime
    responded_at: datetime | None
