import os
from typing import Any
from urllib.parse import urljoin

import httpx


class FHIRIntegrationError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def fhir_mode() -> str:
    mode = os.getenv("FHIR_MODE", "local").lower()
    if mode not in {"local", "hapi"}:
        raise FHIRIntegrationError("FHIR_MODE must be either 'local' or 'hapi'")
    return mode


def _base_url() -> str:
    base_url = os.getenv("FHIR_SERVER_URL", "").rstrip("/")
    if not base_url:
        raise FHIRIntegrationError("FHIR_MODE=hapi requires FHIR_SERVER_URL")
    return base_url


def _client() -> httpx.Client:
    headers = {"Accept": "application/fhir+json"}
    bearer_token = os.getenv("FHIR_SERVER_BEARER_TOKEN")
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    return httpx.Client(
        headers=headers,
        timeout=httpx.Timeout(connect=3.0, read=15.0, write=15.0, pool=3.0),
        follow_redirects=False,
    )


def _raise_for_fhir_error(response: httpx.Response, action: str) -> None:
    if response.is_success:
        return
    try:
        body = response.json()
    except ValueError:
        body = {}
    issues = body.get("issue", []) if isinstance(body, dict) else []
    details = "; ".join(
        str(issue.get("diagnostics", issue.get("code", "FHIR operation failed")))
        for issue in issues[:3]
        if isinstance(issue, dict)
    )
    if not details:
        details = f"HTTP {response.status_code}"
    status_code = (
        409 if response.status_code in (409, 412)
        else 422 if response.status_code in (400, 422)
        else 503
    )
    raise FHIRIntegrationError(f"HAPI FHIR {action} failed: {details}", status_code=status_code)


def check_r4_server() -> dict[str, Any]:
    if fhir_mode() != "hapi":
        return {"mode": "local"}
    try:
        with _client() as client:
            response = client.get(urljoin(_base_url() + "/", "metadata"), headers={"Accept": "application/fhir+json"})
            _raise_for_fhir_error(response, "capability check")
            capability = response.json()
    except FHIRIntegrationError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise FHIRIntegrationError("Unable to reach HAPI FHIR capability endpoint") from exc
    if not isinstance(capability, dict):
        raise FHIRIntegrationError("HAPI FHIR returned an invalid CapabilityStatement")
    fhir_version = capability.get("fhirVersion")
    if capability.get("resourceType") != "CapabilityStatement" or fhir_version != "4.0.1":
        raise FHIRIntegrationError(f"Expected HAPI FHIR R4 (4.0.1), server reported {fhir_version!r}")
    return {"mode": "hapi", "fhir_version": fhir_version}


def _referenced_resources(resource: dict[str, Any]):
    def visit(value):
        if isinstance(value, dict):
            reference = value.get("reference")
            if isinstance(reference, str) and "/" in reference and not reference.startswith("#"):
                parts = reference.rstrip("/").split("/")
                if len(parts) >= 2 and parts[-2] in {
                    "Patient", "Practitioner", "Organization", "DocumentReference", "ServiceRequest",
                    "Specimen", "Observation", "DiagnosticReport", "Consent",
                }:
                    yield parts[-2], parts[-1]
            for nested in value.values():
                yield from visit(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from visit(nested)

    yield from visit(resource)


def validate_references(resource: dict[str, Any]) -> None:
    resource_id = resource.get("id")
    references = {
        (resource_type, reference_id)
        for resource_type, reference_id in _referenced_resources(resource)
        if not (resource_type == resource.get("resourceType") and reference_id == resource_id)
    }
    if not references:
        return
    try:
        with _client() as client:
            for resource_type, reference_id in references:
                response = client.get(f"{_base_url()}/{resource_type}/{reference_id}")
                if response.status_code == 404:
                    raise FHIRIntegrationError(
                        f"FHIR reference {resource_type}/{reference_id} does not exist",
                        status_code=422,
                    )
                _raise_for_fhir_error(response, "reference validation")
    except FHIRIntegrationError:
        raise
    except httpx.HTTPError as exc:
        raise FHIRIntegrationError("HAPI FHIR reference validation is unavailable") from exc


def persist_resource(resource: dict[str, Any]) -> dict[str, Any]:
    if fhir_mode() == "local":
        return resource
    if fhir_mode() != "hapi":
        raise FHIRIntegrationError("FHIR_MODE must be either 'local' or 'hapi'")
    resource_type = resource.get("resourceType")
    resource_id = resource.get("id")
    if not isinstance(resource_type, str) or not isinstance(resource_id, str):
        raise FHIRIntegrationError("FHIR resources require resourceType and id before persistence")

    validate_references(resource)
    try:
        with _client() as client:
            validation = client.post(
                f"{_base_url()}/{resource_type}/$validate",
                json=resource,
                headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
            )
            _raise_for_fhir_error(validation, "R4 validation")
            operation_outcome = validation.json()
            if not isinstance(operation_outcome, dict):
                raise FHIRIntegrationError("HAPI FHIR $validate returned an invalid OperationOutcome")
            issues = operation_outcome.get("issue", [])
            if not isinstance(issues, list):
                raise FHIRIntegrationError("HAPI FHIR $validate returned an invalid issue list")
            errors = [issue for issue in issues if isinstance(issue, dict)
                      and issue.get("severity") in ("error", "fatal")]
            if errors:
                descriptions = "; ".join(
                    issue.get("diagnostics", issue.get("code", "Invalid FHIR resource"))
                    for issue in errors[:3]
                )
                raise FHIRIntegrationError(
                    f"HAPI FHIR validation rejected resource: {descriptions}",
                    status_code=422,
                )

            headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
            meta = resource.get("meta")
            version = meta.get("versionId") if isinstance(meta, dict) else None
            if version:
                headers["If-Match"] = f'W/"{version}"'
            response = client.put(
                f"{_base_url()}/{resource_type}/{resource_id}",
                json=resource,
                headers=headers,
            )
            _raise_for_fhir_error(response, "resource persistence")
            return response.json()
    except httpx.HTTPError as exc:
        raise FHIRIntegrationError("Unable to validate or persist resource in HAPI FHIR") from exc
    except ValueError as exc:
        raise FHIRIntegrationError("HAPI FHIR returned a non-JSON response") from exc


def retrieve_resource(resource_type: str, resource_id: str) -> dict[str, Any] | None:
    if fhir_mode() == "local":
        return None
    if fhir_mode() != "hapi":
        raise FHIRIntegrationError("FHIR_MODE must be either 'local' or 'hapi'")
    try:
        with _client() as client:
            response = client.get(f"{_base_url()}/{resource_type}/{resource_id}")
            if response.status_code == 404:
                return None
            _raise_for_fhir_error(response, "resource retrieval")
            resource = response.json()
    except httpx.HTTPError as exc:
        raise FHIRIntegrationError("Unable to retrieve resource from HAPI FHIR") from exc
    except ValueError as exc:
        raise FHIRIntegrationError("HAPI FHIR returned a non-JSON resource") from exc
    if not isinstance(resource, dict):
        raise FHIRIntegrationError("HAPI FHIR returned an invalid resource")
    if resource.get("resourceType") != resource_type or resource.get("id") != resource_id:
        raise FHIRIntegrationError("HAPI FHIR returned a mismatched resource identity")
    return resource


def authoritative_resource(resource_type: str, resource_id: str, local_data: dict[str, Any]) -> dict[str, Any]:
    if fhir_mode() == "local":
        return local_data
    resource = retrieve_resource(resource_type, resource_id)
    if resource is None:
        raise FHIRIntegrationError(
            f"FHIR resource {resource_type}/{resource_id} does not exist in the configured server",
            status_code=404,
        )
    return resource
