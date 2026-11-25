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


def build_consent(fhir_id, patient_ref, practitioner_ref, resource_types, starts_at, ends_at, active=True) -> dict:
    return {
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
        "performer": [{"reference": f"Practitioner/{practitioner_ref}"}],
        "provision": {
            "type": "permit",
            "period": {"start": starts_at.isoformat(), "end": ends_at.isoformat()},
            "code": [{
                "coding": [{
                    "system": "urn:wirachain:consent-resource-type",
                    "code": resource_type,
                    "display": resource_type,
                }],
                "text": resource_type,
            } for resource_type in resource_types],
        },
    }
