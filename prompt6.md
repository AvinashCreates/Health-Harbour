# HEALTHHARBOR — COPILOT MASTER PROMPT
# MILESTONE 6: COMPLETE FHIR R4 INTEROPERABILITY
## Clinical Resource Mapping, HAPI FHIR Persistence, Synchronization & Reconciliation

You are acting as the Principal Healthcare Interoperability Architect, Senior Backend Engineer, FHIR R4 Specialist, Database Architect, and Integration Security Engineer for the existing HealthHarbor project.

Your mission is to complete Milestone 6: establish a reliable, standards-based FHIR R4 interoperability layer connecting HealthHarbor's existing application data with a HAPI FHIR R4 server.

This is an existing full-stack application. You must extend the current implementation rather than creating a new project.

The objective is not merely to generate FHIR JSON or call a FHIR endpoint.

The objective is to demonstrate that HealthHarbor can correctly create, validate, persist, retrieve, update, reference, synchronize, and reconcile clinical resources through FHIR R4.

---

# 1. PRODUCT VISION

HealthHarbor is a consent-aware healthcare information exchange platform.

Its purpose is to allow patients to share medical records with verified healthcare providers across participating healthcare organizations.

The platform already has foundations for:

- Patient and provider identities.
- Healthcare organizations.
- Provider verification.
- Organization affiliations.
- Care connections.
- Provider record-access requests.
- Patient-controlled consent.
- Clinical document upload and storage.
- Private document retrieval.
- Document integrity checks.
- Encryption at rest.
- Document scanning lifecycle.
- Audit logging.
- Hyperledger Fabric integration boundaries.

Milestone 6 must connect these existing capabilities to a coherent FHIR R4 interoperability architecture.

**FHIR is the interoperability standard. It must not replace HealthHarbor's application authorization system.**

The application database remains authoritative for:

- Account ownership.
- User authentication mapping.
- Provider verification.
- Organization membership.
- Care-request workflows.
- Consent decisions.
- Current authorization.
- Document ownership.
- Application workflow state.

HAPI FHIR provides the standards-based representation and exchange of appropriate healthcare resources.

Never assume that the existence of a FHIR resource automatically grants a user permission to access it.

---

# 2. MANDATORY REPOSITORY INSPECTION

Before making changes, inspect the complete existing implementation.

Read:

- `prompt.md`
- `PROMPT5.MD`
- `README.md`
- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `TESTING_REPORT.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `INTEGRATION_GUIDE.md`

Inspect:

### Backend

- SQLAlchemy models.
- Pydantic schemas.
- FastAPI routers.
- Authentication dependencies.
- Authorization services.
- Consent services.
- Clinical file services.
- Document storage.
- Audit services.
- Transactional outbox.
- Alembic migration history.
- Existing integration clients.

### FHIR

- Current HAPI FHIR configuration.
- Existing FHIR client.
- Existing resource mappings.
- FHIR identifiers.
- Patient, Practitioner and Organization references.
- DocumentReference and Binary handling.
- Consent representation.
- Existing synchronization logic.
- FHIR error handling.

### Infrastructure

- Docker Compose.
- HAPI FHIR server version.
- PostgreSQL configuration.
- Keycloak integration.
- Fabric gateway.
- Environment configuration.

### Frontend

- Patient workspace.
- Doctor workspace.
- Registry workspace.
- Sharing workspace.
- Files workspace.
- Existing API client and state handling.

Do not assume that the current code matches documentation.

Inspect actual source files and tests.

---

# 3. PRESERVATION AND SAFETY RULES

Before implementation:

1. Run `git status --short`.
2. Inspect existing uncommitted changes.
3. Identify the current migration head.
4. Identify the existing HAPI FHIR version.
5. Identify existing FHIR resource mappings.
6. Identify the current outbox implementation.
7. Identify the current application-to-FHIR identity mapping.

Never:

- Run `git reset --hard`.
- Run `git clean`.
- Discard existing work.
- Rewrite historical migrations.
- Modify historical audit records.
- Modify historical audit entry #33.
- Run experimental migrations against the user's existing PostgreSQL database.
- Commit changes without explicit permission.
- Replace existing integrations with fake implementations.
- Put real patient information into test fixtures.

Use synthetic clinical data exclusively.

---

# 4. STAGE A — FHIR ARCHITECTURE GAP ANALYSIS

Before implementing resources, create a complete inventory.

For each relevant application entity, identify:

1. Its existing database model.
2. Its current application identifier.
3. Its FHIR resource representation.
4. Its FHIR identifier strategy.
5. Its reference relationships.
6. Its ownership and authorization rules.
7. Its synchronization direction.
8. Its source of truth.
9. Its failure and retry behavior.

Produce a resource-mapping matrix.

At minimum, assess the following:

| HealthHarbor entity | FHIR R4 resource |
|---|---|
| Patient account/profile | Patient |
| Verified doctor | Practitioner |
| Doctor's organization affiliation | PractitionerRole |
| Healthcare organization | Organization |
| Patient consent | Consent |
| Uploaded clinical document | DocumentReference |
| Document binary content | Binary, where appropriate |
| Laboratory order | ServiceRequest |
| Laboratory result | DiagnosticReport |
| Individual laboratory observation | Observation |
| Medication prescription | MedicationRequest |
| Clinical provenance | Provenance |
| Security and access events | AuditEvent |

This is a mapping assessment, not an instruction to create every resource immediately.

Only implement resources supported by actual application data and workflows.

Do not invent clinical facts to populate FHIR resources.

Document resources that are not yet supported by the application.

---

# 5. STAGE B — FHIR R4 CLIENT ARCHITECTURE

Create or improve a centralized FHIR integration layer.

Do not place direct HAPI HTTP requests throughout individual routers.

Establish clear responsibilities:

- FHIR client.
- Authentication/configuration.
- Resource serializers and mappers.
- Resource validation.
- Reference resolution.
- Persistence operations.
- Retrieval operations.
- Update operations.
- Synchronization service.
- Retry and error handling.
- Reconciliation service.

Use the existing Python dependencies wherever possible.

Do not introduce unnecessary FHIR libraries.

If a new library is needed, evaluate its compatibility with the existing Python version and project requirements before adding it.

The integration must support:

- Create.
- Read.
- Update.
- Search.
- Conditional create or equivalent idempotent behavior where appropriate.
- Delete only when the application lifecycle and retention rules explicitly permit it.

Use the correct FHIR R4 interaction semantics.

Do not implement unsupported interactions by pretending they are standard FHIR operations.

---

# 6. STAGE C — IDENTITY MAPPING AND REFERENCE INTEGRITY

This is a critical requirement.

HealthHarbor must maintain reliable relationships between internal application identities and FHIR resource identities.

Implement a stable identity-mapping strategy.

Examples:

- Application patient ID → FHIR Patient identifier.
- Application provider ID → FHIR Practitioner identifier.
- Application affiliation ID → FHIR PractitionerRole identifier.
- Application organization ID → FHIR Organization identifier.
- Application document ID → FHIR DocumentReference identifier.

Requirements:

1. Use stable identifiers.
2. Avoid generating a new FHIR resource on every synchronization.
3. Prevent duplicate Patient, Practitioner, and Organization resources.
4. Maintain correct references.
5. Handle missing references safely.
6. Handle conflicting identifiers.
7. Handle resource-not-found responses.
8. Prevent cross-patient reference leakage.
9. Preserve application ownership.
10. Never trust client-supplied FHIR references as authorization proof.

Do not expose internal database primary keys unnecessarily.

Use a documented identifier strategy.

## Reference examples

A DocumentReference must point to the correct patient.

A PractitionerRole must reference the correct Practitioner and Organization.

A DiagnosticReport must reference the appropriate patient and relevant Observations.

A Consent resource must represent the correct patient and applicable authorization context.

Verify that all references point to resources that actually exist.

---

# 7. STAGE D — PATIENT, PROVIDER AND ORGANIZATION RESOURCES

Implement or complete the following resource mappings.

## 7.1 Patient

Map the existing patient profile to FHIR Patient.

Use only information that exists and is appropriate to exchange.

Requirements:

- Stable identifier.
- Appropriate active status.
- Correct identifier system.
- Appropriate name and demographic fields where available.
- No invented values.
- Consistent application-to-FHIR mapping.

Do not expose sensitive patient information through public directory APIs.

## 7.2 Practitioner

Map verified healthcare providers to Practitioner.

Requirements:

- Stable identifier.
- Active status reflecting the current application state.
- Appropriate professional identification fields where available.
- No false qualifications.
- No fabricated medical license details.

Only approved and verified providers should be represented as active verified providers.

Do not treat a self-declared role as proof of professional verification.

## 7.3 PractitionerRole

Map provider affiliations to PractitionerRole.

Represent:

- Practitioner reference.
- Organization reference.
- Active status.
- Available specialty or role information where supported.
- Effective period where available.

Provider status and affiliation status must remain independently controlled.

Suspending an organization must not silently rewrite historical provider identity information.

## 7.4 Organization

Map approved healthcare organizations to Organization.

Represent:

- Stable identifier.
- Active status.
- Name.
- Organization type where supported.
- Contact or address information where appropriate.

Do not expose private onboarding evidence.

Do not fabricate official organization identifiers.

---

# 8. STAGE E — CONSENT INTEROPERABILITY

Map existing HealthHarbor consent decisions to FHIR R4 Consent.

Do not create a second consent engine.

The existing application consent system remains authoritative for authorization.

FHIR Consent should accurately represent:

- Patient reference.
- Status.
- Scope.
- Applicable purpose.
- Authorized actor.
- Resource scope.
- Effective period.
- Provision and applicable restrictions.

Inspect the exact existing Consent model before defining mappings.

Requirements:

1. Approved application consent can be represented in FHIR.
2. Rejected requests do not create an active consent.
3. Revoked consent is reflected appropriately.
4. Expired consent is represented consistently.
5. Consent updates do not grant permissions accidentally.
6. A FHIR Consent resource cannot override application authorization.
7. A provider cannot change a patient's consent by modifying FHIR data.
8. Missing or failed synchronization is visible.

Test the relationship between internal consent and FHIR Consent.

Do not claim that FHIR Consent synchronization itself enforces access.

---

# 9. STAGE F — DOCUMENTREFERENCE AND BINARY INTEROPERABILITY

Extend the existing clinical document system.

Do not duplicate the current file-storage architecture.

## DocumentReference

Represent existing clinical documents using FHIR R4 DocumentReference.

Where appropriate, include:

- Stable identifier.
- Status.
- DocStatus.
- Type.
- Category.
- Subject reference.
- Date.
- Author.
- Custodian.
- Content metadata.
- Attachment content type.
- Attachment size.
- Attachment hash.
- Appropriate attachment URL or reference.

Use only available and valid metadata.

Do not fabricate authors or issuing organizations.

## Binary

Inspect the current encrypted storage system before deciding how to expose Binary content.

Important:

- Never bypass document authorization through HAPI FHIR.
- Never create a publicly accessible Binary URL.
- Never return unencrypted stored content.
- Never expose internal storage keys.
- Never assume a DocumentReference URL is safe simply because it is a FHIR reference.

Choose and document the appropriate approach:

1. Store Binary resources in HAPI FHIR with a properly protected access model, if the deployment supports it.
2. Keep binary content in HealthHarbor's private encrypted storage and use a controlled authenticated retrieval integration.
3. Use another standards-compliant approach supported by the actual architecture.

The choice must be justified.

The patient's consent must still be checked before document retrieval.

A direct HAPI endpoint must not become an authorization bypass.

## Synchronization

When a document is uploaded and successfully processed:

1. Confirm ownership.
2. Confirm document processing status.
3. Confirm required malware scanning status.
4. Confirm encryption/storage status.
5. Construct the FHIR representation.
6. Persist or queue the FHIR resource.
7. Record synchronization status.
8. Handle failure and retry.

Do not synchronize rejected or unscanned documents as available clinical documents.

---

# 10. STAGE G — CLINICAL RESOURCE WORKFLOWS

Connect existing clinical workflows to appropriate FHIR resources where supported.

Prioritize:

### Laboratory orders

Use ServiceRequest when an actual laboratory service request exists.

Represent:

- Patient.
- Requesting practitioner.
- Performing organization where known.
- Clinical intent.
- Requested service.
- Status.
- Authored date.
- Relevant identifiers.

### Laboratory observations

Use Observation for actual measured results.

Represent:

- Patient.
- Observation code.
- Value.
- Unit.
- Effective time.
- Status.
- Appropriate reference ranges when known.

### Diagnostic reports

Use DiagnosticReport for the laboratory or diagnostic report.

Represent:

- Patient.
- Status.
- Category.
- Code.
- Effective period.
- Issuing organization.
- Result references.
- Supporting document references.

### Medication requests

Use MedicationRequest only when a real prescription workflow exists.

Do not create fake medication orders to demonstrate FHIR support.

If the current application does not yet have the relevant workflow, document it as a future integration rather than inventing a partial clinical process.

---

# 11. STAGE H — TRANSACTIONAL OUTBOX AND RELIABLE SYNCHRONIZATION

This is one of the most important stages.

Inspect and reuse the existing transactional outbox.

FHIR synchronization must not depend on an unreliable background HTTP call after a database transaction.

Implement reliable synchronization for the resources supported by the current project.

## Required behavior

1. Application transaction updates its authoritative database state.
2. The corresponding synchronization event is written atomically to the outbox.
3. A worker processes pending events.
4. The worker constructs the appropriate FHIR resource.
5. HAPI FHIR receives the request.
6. The worker validates the response.
7. Successful synchronization is recorded.
8. Failed synchronization is retained for retry.

Handle:

- Network timeout.
- Connection refusal.
- HAPI unavailable.
- Authentication failure.
- Invalid FHIR resource.
- HTTP 400.
- HTTP 401/403.
- HTTP 404.
- HTTP 409.
- HTTP 429.
- HTTP 5xx.
- Duplicate event delivery.
- Worker restart.
- Partial synchronization.

## Idempotency

A repeated outbox event must not create duplicate FHIR resources.

Use stable identifiers and appropriate conditional interactions.

Do not use random new identifiers on retries.

## Retry behavior

Implement bounded retries and appropriate backoff.

Do not retry permanent validation failures indefinitely.

Track:

- Attempt count.
- Last attempt.
- Last error category.
- Next retry time.
- Synchronization status.
- Successful synchronization time.

Do not expose sensitive resource payloads in error messages.

## Reconciliation

Create a safe reconciliation mechanism.

It should identify discrepancies between application records and FHIR resources.

Examples:

- Application resource exists but FHIR resource is missing.
- FHIR resource exists but local synchronization state is missing.
- FHIR resource has an unexpected version.
- Reference points to a missing resource.
- Resource is marked inactive in one system but active in another.

Reconciliation must not silently overwrite data.

Define which system is authoritative for each field.

Require safe, explicit remediation for conflicting data.

---

# 12. STAGE I — MULTI-ORGANIZATION INTEROPERABILITY

HealthHarbor's long-term objective is secure exchange across different healthcare organizations.

For this milestone, implement the foundations without prematurely building a distributed hospital federation.

The initial architecture remains one shared HealthHarbor deployment with strict organization and patient isolation.

Requirements:

- Stable organization identifiers.
- Consistent practitioner affiliations.
- Consistent patient references.
- Organization-scoped metadata.
- Secure resource lookup.
- No cross-tenant data leakage.
- Patient-controlled sharing.
- FHIR references that remain valid across supported workflows.

Do not claim independent hospital federation is implemented.

Do not create separate FHIR servers for every organization unless the current architecture and infrastructure explicitly support it.

Document the future federation boundary.

---

# 13. STAGE J — FHIR VALIDATION AND CONFORMANCE

Validate generated resources against FHIR R4 semantics.

Use HAPI FHIR's validation capabilities or a compatible validator where available.

Validate:

- Resource type.
- Required fields.
- Identifier systems.
- Code systems.
- Cardinality.
- Reference syntax.
- Resource status.
- Date/time formats.
- Bundle structure.
- Profile conformance where applicable.

Use appropriate standard terminologies.

Do not invent coding-system URLs or terminology codes.

Do not claim complete national or international profile conformance unless the relevant profiles have actually been implemented and tested.

Document unsupported profiles and terminology gaps.

---

# 14. STAGE K — FHIR SECURITY

FHIR must never become an alternate path around HealthHarbor authorization.

Apply the following requirements:

- Authenticate integration clients.
- Restrict access to HAPI endpoints.
- Do not expose administrative HAPI interfaces publicly.
- Enforce patient ownership.
- Enforce provider verification.
- Enforce organization membership where applicable.
- Enforce current consent before clinical document retrieval.
- Avoid exposing internal identifiers unnecessarily.
- Prevent cross-patient reference manipulation.
- Avoid sensitive data in logs.
- Protect FHIR search results.
- Prevent unauthorized resource enumeration.
- Handle deleted, revoked, and expired resources consistently.

Test attempts to retrieve another patient's resource.

Test direct Binary retrieval.

Test access after consent revocation.

Test access after provider suspension.

Test access after organization suspension.

The backend must check current application state.

Do not rely on FHIR resource visibility as the sole security boundary.

---

# 15. STAGE L — FRONTEND INTEROPERABILITY VISIBILITY

Extend the existing workspaces only where useful.

Do not create a separate FHIR administration application.

### Patient workspace

Where appropriate, show:

- Clinical document FHIR synchronization status.
- Whether a record is pending synchronization.
- Whether synchronization failed.
- Consent status.
- Document metadata.
- Record availability.

Patients should not need to understand raw FHIR JSON.

### Doctor workspace

Show:

- Authorized clinical records.
- Relevant document metadata.
- Available laboratory reports.
- Applicable consent.
- Record availability.
- Clear synchronization or retrieval errors.

### Administrative workspace

Provide controlled operational visibility into:

- Failed FHIR synchronization.
- Pending events.
- Retry status.
- Reconciliation discrepancies.
- Integration health.

Never expose full clinical contents to administrators who do not have an appropriate clinical access basis.

Do not create fake integration-status indicators.

Every displayed status must come from real backend state.

---

# 16. STAGE M — TESTING REQUIREMENTS

Write meaningful tests for all implemented resources.

## Identity mapping tests

- Patient mapping.
- Practitioner mapping.
- Organization mapping.
- PractitionerRole mapping.
- Stable identifiers.
- Duplicate prevention.
- Reference integrity.
- Missing reference handling.

## Consent tests

- Approved consent mapping.
- Rejected request behavior.
- Revoked consent mapping.
- Expired consent behavior.
- No accidental access grant.
- Application consent remains authoritative.

## Document tests

- DocumentReference generation.
- Attachment metadata.
- Hash consistency.
- Binary behavior.
- Encrypted storage compatibility.
- Scanning-state enforcement.
- No direct authorization bypass.

## Clinical resource tests

Where supported:

- ServiceRequest.
- Observation.
- DiagnosticReport.
- MedicationRequest.

Test valid and invalid resource payloads.

## Outbox tests

- Atomic event creation.
- Successful synchronization.
- Failed synchronization.
- Retry.
- Bounded retry.
- Duplicate delivery.
- Worker restart.
- Permanent failure.
- Reconciliation.

## Security tests

- Unauthorized FHIR retrieval.
- Cross-patient resource access.
- Cross-organization access.
- Consent revocation.
- Expired consent.
- Suspended provider.
- Suspended organization.
- Inactive affiliation.
- Direct Binary access.
- Identifier manipulation.

## Integration tests

If a disposable HAPI FHIR R4 instance is available:

1. Create synthetic Patient.
2. Retrieve Patient.
3. Create Practitioner.
4. Create Organization.
5. Create PractitionerRole.
6. Create Consent.
7. Create DocumentReference.
8. Retrieve DocumentReference.
9. Verify references.
10. Test an update.
11. Test duplicate synchronization.
12. Test server-unavailable behavior.
13. Restore service and verify retry.

Do not claim live HAPI testing if the server was unavailable.

---

# 17. DATABASE AND MIGRATION REQUIREMENTS

Inspect existing schema before adding tables or columns.

Potential additions may include:

- FHIR resource mappings.
- FHIR synchronization state.
- Resource version tracking.
- Reconciliation state.

These are conceptual requirements, not mandatory duplicate models.

Reuse existing outbox and integration tables.

If a migration is required:

- Make it additive.
- Preserve existing data.
- Add appropriate constraints and indexes.
- Do not rewrite previous migrations.
- Test using isolated SQLite.
- Test using disposable PostgreSQL if available.
- Run `alembic check`.

Never access the user's existing PostgreSQL database for experimental migration testing.

---

# 18. INFRASTRUCTURE AND CONFIGURATION

Inspect the current Docker Compose and HAPI configuration.

Provide a reproducible HAPI FHIR R4 integration environment.

Requirements:

- Correct FHIR R4 server configuration.
- Correct database connectivity.
- Health checks.
- Appropriate startup dependencies.
- Persistent storage where required.
- Safe environment variables.
- No hardcoded production credentials.
- Clear development and production configuration boundaries.

Do not upgrade HAPI blindly.

Confirm compatibility with the existing version before changing it.

If Docker is unavailable, implement configuration and automated tests that can run independently, and clearly report that live infrastructure was not verified.

---

# 19. DOCUMENTATION

Update:

- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `TESTING_REPORT.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `INTEGRATION_GUIDE.md`
- `README.md`

Add a dedicated FHIR architecture document if useful.

Document:

1. Resource mapping matrix.
2. Identifier strategy.
3. Source-of-truth policy.
4. Reference strategy.
5. FHIR client architecture.
6. HAPI configuration.
7. Synchronization lifecycle.
8. Outbox processing.
9. Retry behavior.
10. Reconciliation.
11. Security boundaries.
12. Unsupported resources.
13. Terminology limitations.
14. Actual test evidence.

Clearly separate implemented functionality from future plans.

---

# 20. IMPLEMENTATION EXECUTION ORDER

Follow this sequence:

### Phase 1 — Inspect and assess

Understand current models, mappings, integrations, outbox, and tests.

Produce a gap analysis.

### Phase 2 — Define interoperability architecture

Create the resource matrix, identifier strategy, source-of-truth policy, and synchronization design.

### Phase 3 — Complete identity resources

Implement Patient, Practitioner, Organization, and PractitionerRole mapping.

### Phase 4 — Complete consent interoperability

Map the existing application consent model to FHIR Consent.

### Phase 5 — Complete document interoperability

Implement DocumentReference and the selected protected Binary/content retrieval strategy.

### Phase 6 — Connect clinical workflows

Integrate ServiceRequest, Observation, DiagnosticReport, and MedicationRequest only where actual workflows exist.

### Phase 7 — Reliable synchronization

Complete outbox delivery, retry, idempotency, and reconciliation.

### Phase 8 — Security and validation

Test reference integrity, access control, FHIR validation, and cross-organization isolation.

### Phase 9 — Frontend visibility

Show meaningful synchronization and record status in existing workspaces.

### Phase 10 — Final verification

Run regression, migration, integration, security, and documentation checks.

Do not generate the entire implementation in one operation.

Complete each phase incrementally.

---

# 21. FINAL ACCEPTANCE CRITERIA

Milestone 6 is complete only when:

1. The FHIR resource mapping architecture is documented.
2. Patient mapping works.
3. Practitioner mapping works.
4. Organization mapping works.
5. PractitionerRole mapping works.
6. Consent mapping reflects actual application consent.
7. DocumentReference mapping works.
8. Binary/content retrieval respects application authorization.
9. Supported clinical workflows use semantically correct FHIR resources.
10. Resource references remain valid.
11. Stable identifiers prevent duplicate resource creation.
12. FHIR synchronization uses reliable persistence and retry mechanisms.
13. Reconciliation identifies synchronization discrepancies.
14. FHIR validation is demonstrated for supported resources.
15. Cross-patient and cross-organization isolation is tested.
16. Consent revocation continues to block access.
17. Existing encryption and document-scanning safeguards remain intact.
18. Existing backend regression tests pass.
19. New FHIR tests pass.
20. Documentation reflects actual functionality.
21. No historical audit record has been modified.
22. No unrequested Git commit has been created.

If an item cannot be verified, mark it **NOT VERIFIED**.

Do not mark the milestone complete simply because code was written.

---

# 22. FINAL REPORT FORMAT

At completion, provide:

## Implemented
Actual resource mappings and integration functionality.

## FHIR Resource Matrix
For each resource:
- Implemented or not implemented.
- Application source.
- FHIR representation.
- Identifier strategy.
- Reference relationships.
- Persistence status.

## HAPI FHIR Integration
- Server version.
- FHIR R4 confirmation.
- Create/read/update evidence.
- Validation results.
- Authentication status.
- Live integration status.

## Synchronization
- Outbox behavior.
- Retry mechanism.
- Idempotency.
- Failure handling.
- Reconciliation.

## Security
- Patient isolation.
- Provider authorization.
- Consent enforcement.
- Binary protection.
- Cross-organization authorization.

## Database
- New models.
- Migration revision.
- Constraints and indexes.
- SQLite verification.
- PostgreSQL verification.

## Testing
Report exact commands and outcomes.

Separate:
- Passed.
- Failed.
- Skipped.
- Not available.
- Not verified.

## Files Changed
List important modified and created files.

## Remaining Risks
Identify genuine limitations.

## Git Status
Confirm that no unrequested commit was created.

---

# FINAL ENGINEERING PRINCIPLE

HealthHarbor is intended to solve healthcare interoperability, not merely store healthcare documents.

FHIR must be implemented correctly, with meaningful resources, stable identifiers, valid references, reliable persistence, and secure access.

Never sacrifice clinical correctness for the appearance of interoperability.

Never allow FHIR to bypass patient consent.

Never claim an external integration works without evidence.

Build a system that can demonstrate a real patient record moving through a secure, standards-based healthcare exchange workflow.

**Start by inspecting the repository and existing FHIR implementation. Preserve all existing work. Implement incrementally, test continuously, and report honestly.**