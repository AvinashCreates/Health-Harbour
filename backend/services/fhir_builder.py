"""Builds FHIR R4-shaped JSON resources. Simplified relative to the full
HL7 FHIR spec (no FHIR server-generated meta.versionId etc.) but structurally
correct: real resourceType values, Reference syntax ("Patient/<id>"), and
real coding systems (LOINC, SNOMED CT) rather than made-up fields."""

from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_patient(user) -> dict:
    return {
        "resourceType": "Patient",
        "id": user.fhir_resource_id or user.id,
        "identifier": [{"system": "urn:healthcare-exchange:user", "value": user.id}],
        "name": [{"text": user.full_name}],
        "active": True,
    }


def build_practitioner(user) -> dict:
    return {
        "resourceType": "Practitioner",
        "id": user.fhir_resource_id or user.id,
        "identifier": [{"system": "urn:healthcare-exchange:user", "value": user.id}],
        "name": [{"text": user.full_name}],
        "active": True,
    }


def build_healthcare_practitioner(provider, account) -> dict:
    resource = {
        "resourceType": "Practitioner",
        "id": provider.fhir_resource_id or provider.id,
        "identifier": [{
            "system": "urn:healthharbor:provider",
            "value": provider.id,
        }],
        "active": provider.status == "VERIFIED",
        "name": [{"text": provider.professional_name or account.full_name}],
    }
    if provider.registration_authority or provider.registration_number:
        identifiers = []
        if provider.registration_authority:
            identifiers.append({"system": "urn:healthharbor:registration-authority", "value": provider.registration_authority})
        if provider.registration_number:
            identifiers.append({"system": "urn:healthharbor:registration-number", "value": provider.registration_number})
        resource["identifier"].extend(identifiers)
    if provider.specialization:
        resource["qualification"] = [{"code": {"text": provider.specialization}}]
    return resource


def build_healthcare_organization(organization) -> dict:
    identifiers = [{"system": "urn:healthharbor:organization", "value": organization.id}]
    if organization.registration_authority or organization.registration_identifier:
        if organization.registration_authority:
            identifiers.append({"system": "urn:healthharbor:registration-authority", "value": organization.registration_authority})
        if organization.registration_identifier:
            identifiers.append({"system": "urn:healthharbor:registration-number", "value": organization.registration_identifier})
    resource = {
        "resourceType": "Organization",
        "id": organization.fhir_resource_id or organization.id,
        "identifier": identifiers,
        "active": organization.status == "APPROVED",
        "name": organization.display_name or organization.legal_name,
    }
    if organization.address:
        resource["address"] = [{"text": " ".join(str(value) for value in organization.address.values())}]
    return resource


def build_practitioner_role(affiliation, provider, organization) -> dict:
    resource = {
        "resourceType": "PractitionerRole",
        "id": affiliation.id,
        "identifier": [{"system": "urn:healthharbor:affiliation", "value": affiliation.id}],
        "active": affiliation.status == "ACTIVE",
        "practitioner": {"reference": f"Practitioner/{provider.fhir_resource_id or provider.id}"},
        "organization": {"reference": f"Organization/{organization.fhir_resource_id or organization.id}"},
        "code": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/practitioner-role", "code": "provider", "display": "Provider"}]}],
    }
    period = {}
    if affiliation.effective_from:
        period["start"] = affiliation.effective_from.isoformat()
    if affiliation.effective_until:
        period["end"] = affiliation.effective_until.isoformat()
    if period:
        resource["period"] = period
    return resource


def build_organization(user) -> dict:
    return {
        "resourceType": "Organization",
        "id": user.fhir_resource_id or user.id,
        "identifier": [{"system": "urn:healthcare-exchange:laboratory", "value": user.id}],
        "name": user.full_name,
        "active": True,
    }


def build_service_request(fhir_id, patient_ref, requester_ref, test_code, test_display, note=None) -> dict:
    resource = {
        "resourceType": "ServiceRequest",
        "id": fhir_id,
        "status": "active",
        "intent": "order",
        "category": [{
            "coding": [{"system": "http://snomed.info/sct", "code": "108252007", "display": "Laboratory procedure"}]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": test_code, "display": test_display}],
            "text": test_display,
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "requester": {"reference": f"Practitioner/{requester_ref}"},
        "authoredOn": now_iso(),
    }
    if note:
        resource["note"] = [{"text": note}]
    return resource


def build_observation(fhir_id, patient_ref, service_request_fhir_id, code, display, value, unit) -> dict:
    return {
        "resourceType": "Observation",
        "id": fhir_id,
        "status": "final",
        "basedOn": [{"reference": f"ServiceRequest/{service_request_fhir_id}"}],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": code, "display": display}],
            "text": display,
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "effectiveDateTime": now_iso(),
        "valueQuantity": {"value": value, "unit": unit},
    }


def build_diagnostic_report(
    fhir_id, patient_ref, service_request_fhir_id, observation_fhir_ids,
    lab_ref, conclusion, status="final",
) -> dict:
    return {
        "resourceType": "DiagnosticReport",
        "id": fhir_id,
        "status": status,
        "basedOn": [{"reference": f"ServiceRequest/{service_request_fhir_id}"}],
        "code": {"text": "Laboratory report"},
        "subject": {"reference": f"Patient/{patient_ref}"},
        "performer": [{"reference": f"Organization/{lab_ref}"}],
        "effectiveDateTime": now_iso(),
        "issued": now_iso(),
        "result": [{"reference": f"Observation/{oid}"} for oid in observation_fhir_ids],
        "conclusion": conclusion,
    }


def build_specimen(fhir_id, patient_ref, service_request_fhir_id, type_code, type_display) -> dict:
    return {
        "resourceType": "Specimen",
        "id": fhir_id,
        "status": "available",
        "type": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": type_code,
                "display": type_display,
            }],
            "text": type_display,
        },
        "subject": {"reference": f"Patient/{patient_ref}"},
        "request": [{"reference": f"ServiceRequest/{service_request_fhir_id}"}],
        "collection": {"collectedDateTime": now_iso()},
    }


def build_consent(
    fhir_id,
    patient_ref,
    practitioner_ref,
    resource_types,
    starts_at,
    ends_at,
    active=True,
    organization_ref=None,
    purpose="TREATMENT",
) -> dict:
    purpose_codes = {
        "TREATMENT": ("TREAT", "Treatment"),
    }
    purpose_code, purpose_display = purpose_codes[purpose]
    actors = [{
        "role": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                "code": "PRCP",
                "display": "Primary information recipient",
            }],
        },
        "reference": {"reference": f"Practitioner/{practitioner_ref}"},
    }]
    if organization_ref:
        actors.append({
            "role": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                    "code": "ORG",
                    "display": "Organization",
                }],
            },
            "reference": {"reference": f"Organization/{organization_ref}"},
        })
    consent = {
        "resourceType": "Consent",
        "id": fhir_id,
        "status": "active" if active else "inactive",
        "scope": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/consentscope",
                "code": "patient-privacy",
                "display": "Privacy Consent",
            }],
        },
        "category": [{
            "coding": [{
                "system": "http://loinc.org",
                "code": "59284-0",
                "display": "Consent Document",
            }],
        }],
        "patient": {"reference": f"Patient/{patient_ref}"},
        "dateTime": starts_at.isoformat(),
        "performer": [{"reference": f"Patient/{patient_ref}"}],
        "provision": {
            "type": "permit",
            "period": {"start": starts_at.isoformat(), "end": ends_at.isoformat()},
            "actor": actors,
            "purpose": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                    "code": purpose_code,
                    "display": purpose_display,
                }],
                "text": purpose_display,
            }],
            "code": [{
                "coding": [{
                    "system": "urn:healthharbor:consent-resource-type",
                    "code": resource_type,
                    "display": resource_type,
                }],
                "text": resource_type,
            } for resource_type in resource_types],
        },
    }
    return consent
