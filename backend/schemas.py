from datetime import datetime
from typing import List, Literal, Optional

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


class TechnicianAssignment(BaseModel):
    technician_email: EmailStr


class LaboratoryMembershipCreate(BaseModel):
    laboratory_email: EmailStr
    technician_email: EmailStr


class SpecimenCreate(BaseModel):
    type_code: str = Field(default="122555007", min_length=1, max_length=40)
    type_display: str = Field(default="Venous blood specimen", min_length=1, max_length=160)


class ConsentGrant(BaseModel):
    doctor_email: EmailStr
    resource_types: List[FHIRResourceType] = Field(
        default_factory=lambda: ["Patient", "ServiceRequest", "Observation", "DiagnosticReport"],
        min_length=1,
    )
    duration_days: int = Field(default=30, ge=1, le=30)


class ConsentOut(BaseModel):
    id: str
    patient_id: str
    grantee_id: str
    resource_types: List[str]
    granted_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool
