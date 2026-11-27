# HealthHarbor — Milestone 8: Clinical Workflow Implementation

## Project Location

`/home/pamarthi-avinash/Downloads/healthcare-exchange`

You are continuing development of my existing final-year project, **HealthHarbor: A Secure, Consent-Aware FHIR and Permissioned Blockchain Framework for Interoperable Healthcare Data Exchange**.

Your task is to implement Milestone 8: Clinical Workflows.

This is an existing full-stack application. You must extend its architecture rather than create a separate application or replace working modules.

---

# 1. Existing Technology Stack

Preserve and use the existing stack:

- Frontend: React + Vite
- Backend: FastAPI + Python
- ORM: SQLAlchemy
- Database: PostgreSQL-compatible schema, with SQLite for local testing
- Migrations: Alembic
- Authentication: Keycloak OIDC/OAuth2 Authorization Code + PKCE, with existing local development authentication
- Healthcare interoperability: HL7 FHIR R4 through HAPI FHIR integration
- Blockchain: Hyperledger Fabric with Go chaincode and existing HTTP Gateway
- Background processing: Existing FHIR transactional outbox and worker
- Testing: Existing unittest conventions and security/API smoke tests

Inspect the actual repository before implementation. Do not assume filenames, model structures, endpoints, or frontend routes without inspecting them.

# 2. Environment Constraints

My laptop currently has limited resources and mobile data.

Therefore:

- Do not install Docker.
- Do not download Docker images.
- Do not install HAPI FHIR or Hyperledger Fabric locally.
- Do not install PostgreSQL solely for this milestone.
- Do not introduce large dependencies without a strong reason.
- Use the existing Python environment and SQLite for local testing.
- Mock unavailable external infrastructure.
- Clearly distinguish mocked integration tests from real infrastructure verification.

Do not sacrifice architectural correctness just to make local tests pass.

# 3. Critical Security and Preservation Rules

These requirements are mandatory.

1. Preserve existing authentication and authorization.
2. Never allow users to assign privileged roles to themselves.
3. Patient ownership must be verified on every patient-sensitive operation.
4. Provider verification and organization affiliation must be checked.
5. Care connection does not automatically grant clinical record access.
6. An access request does not equal consent.
7. Organization affiliation does not equal consent.
8. FHIR resource existence does not equal authorization.
9. Blockchain confirmation does not equal authorization.
10. Every sensitive clinical operation must verify current consent, resource scope, expiry, revocation, organization status, and relevant user permissions.
11. Clinical files must remain in private application storage.
12. Never place clinical document contents, prescriptions, laboratory results, or personal health information on the blockchain.
13. Blockchain must contain only the existing approved tamper-evident event metadata and pseudonymous references/hashes.
14. Do not weaken existing security checks to make a workflow function.
15. Use synthetic clinical data only.

Preservation:

- Inspect Git status before changes.
- Preserve all existing uncommitted work.
- Never use `git reset --hard`.
- Never use `git clean`.
- Never commit changes unless explicitly authorized.
- Never experiment on my existing PostgreSQL database.
- Historical audit entry #33 must remain completely untouched.
- Never rewrite, delete, repair, or re-hash historical audit records.

# 4. First: Repository and Architecture Inspection

Before coding, inspect:

- Existing user, patient, provider, organization, and affiliation models.
- ClinicalFile and document metadata models.
- Consent and access-request models.
- Cross-hospital exchange implementation.
- FHIRSyncOutbox and worker.
- Existing FHIR resource mappings.
- Audit logger and blockchain event allowlist.
- Existing API routers and authorization dependencies.
- React dashboards and API client.
- Existing test suites and migration history.

Identify reusable components and avoid duplicating existing functionality.

Produce a short implementation plan before making changes.

# 5. Clinical Workflow Architecture

Implement these workflows in a coherent manner.

## A. Lab Orders

Doctors should be able to create laboratory diagnostic orders for their patients.

Requirements:

- Only verified and authorized healthcare providers may create orders.
- Patient must have an appropriate care relationship.
- Validate patient identity and provider organization.
- Capture test name, clinical indication, priority, ordering provider, patient, organization, creation time, and status.
- Support order statuses such as draft, active, cancelled, completed.
- Patients should be able to view their authorized orders.
- Laboratory personnel should see only orders assigned to their organization and within their authorization scope.
- Prevent unauthorized modifications.
- Record relevant state transitions in the audit log.

FHIR mapping:

- Use FHIR ServiceRequest.
- Maintain stable resource identifiers.
- Synchronize through the existing FHIR outbox.
- Do not directly bypass the outbox for ordinary background synchronization.

## B. Laboratory Reports

Implement diagnostic report submission by authorized laboratory personnel.

Requirements:

- Only verified lab personnel with appropriate organizational affiliation may submit results.
- Reports must reference valid orders.
- Verify patient and organization ownership.
- Capture report title, test details, result summary, interpretation, issuing laboratory, author, and timestamps.
- Support report states such as preliminary, final, amended, and cancelled.
- Prevent unauthorized changes to finalized reports.
- Maintain report history and traceable amendments.
- Support private file attachments using existing secure file storage.
- Never expose private files through public or predictable storage paths.

FHIR mapping:

- Use DiagnosticReport.
- Use DocumentReference for appropriate report attachments.
- Link reports to their ServiceRequest.
- Synchronize through FHIRSyncOutbox.

Do not store real patient data in development fixtures.

## C. Clinical Observations

Implement structured clinical observations associated with laboratory reports and patients.

Requirements:

- Support suitable observation categories.
- Capture observation code, display name, value, unit, reference range when available, interpretation, effective date, performer, and status.
- Validate values and units.
- Preserve the distinction between missing, unknown, and zero values.
- Link observations to the correct patient and report.
- Restrict access using current authorization and consent.
- Maintain appropriate audit events.

FHIR mapping:

- Use FHIR Observation.
- Use appropriate references to Patient, DiagnosticReport, and ServiceRequest where applicable.
- Ensure stable identifiers and valid references.

Do not invent medical diagnoses or automatically interpret results as a clinical decision.

## D. Prescriptions

Implement a prescription workflow for verified healthcare providers.

Requirements:

- Only authorized providers may create prescriptions.
- Validate patient and provider authorization.
- Capture medication name, dosage, route, frequency, duration, quantity, instructions, author, and timestamps where applicable.
- Validate required fields.
- Support draft, active, cancelled, completed, and stopped states where appropriate.
- Patients may view their authorized prescriptions.
- Unauthorized users must not modify prescriptions.
- Maintain amendment and cancellation history.
- Do not implement medication dispensing or pharmacy integrations unless existing architecture already supports them.

FHIR mapping:

- Use FHIR MedicationRequest.
- Use Medication and dosage structures appropriately.
- Synchronize through the existing FHIR outbox.

Do not invent prescriptions or recommend medication dosages.

## E. Physician Review

Implement a workflow for doctors to review diagnostic reports and observations.

Requirements:

- Only authorized providers may review clinical results.
- Verify patient identity, organization affiliation, and current consent.
- Display linked orders, reports, and observations.
- Allow a doctor to record a review status and clinical note.
- Support pending, reviewed, and follow-up-required states.
- Record reviewing provider and review timestamp.
- Maintain an audit trail.
- Do not automatically convert laboratory results into diagnoses.

FHIR mapping:

- Use appropriate FHIR DiagnosticReport and Observation references.
- Consider Task or another suitable FHIR resource for workflow tracking where justified.
- Keep local workflow state and FHIR state consistent through the existing outbox.

# 6. Patient Dashboard

Extend the existing React application.

Patients should be able to view:

- Their laboratory orders.
- Order status.
- Available diagnostic reports.
- Associated observations.
- Prescriptions.
- Physician review status.
- Relevant clinical history.

Requirements:

- Use the existing authentication flow.
- Fetch data through authenticated backend APIs.
- Display loading, empty, error, and unauthorized states.
- Never expose another patient's information.
- Do not rely on frontend hiding as an authorization mechanism.
- Preserve existing UI architecture and styling conventions.

# 7. Provider Dashboard

Extend the existing provider dashboard.

Provide appropriate workflows for:

- Creating laboratory orders.
- Viewing authorized patient orders.
- Reviewing laboratory reports.
- Viewing structured observations.
- Creating prescriptions.
- Recording physician reviews.
- Viewing relevant workflow history.

Do not give every provider access to every patient.

# 8. Laboratory Dashboard

If the existing role and organization architecture supports it, implement a laboratory dashboard.

It should support:

- Viewing orders assigned to the authorized laboratory organization.
- Viewing order details within permitted scope.
- Submitting preliminary and final reports.
- Managing report amendments through traceable operations.
- Viewing submission status.

Do not allow lab personnel to impersonate doctors or modify prescriptions.

# 9. Authorization and Consent Enforcement

This is one of the most important parts of the milestone.

Every clinical endpoint must enforce server-side authorization.

Implement reusable authorization logic where appropriate.

Test these scenarios:

- Patient attempts to access another patient's records.
- Doctor accesses a patient without a valid care relationship.
- Doctor accesses a patient without appropriate consent.
- Consent expires.
- Consent is revoked.
- Consent does not include the requested resource type.
- Provider affiliation becomes inactive.
- Organization becomes inactive.
- Lab personnel attempt to access another organization's orders.
- Lab personnel attempt to modify a finalized report.
- Unauthorized user attempts prescription creation.
- Unauthorized user attempts clinical report modification.

Recheck authorization before sensitive file downloads and clinical mutations.

Avoid relying on authorization checks performed only when a page is first loaded.

# 10. FHIR Synchronization

Integrate all new clinical entities with the existing FHIR synchronization architecture.

Required mappings:

| Clinical workflow | FHIR resource |
|---|---|
| Laboratory order | ServiceRequest |
| Laboratory report | DiagnosticReport |
| Clinical observation | Observation |
| Report attachment | DocumentReference |
| Prescription | MedicationRequest |
| Workflow tracking | Task, where appropriate |

Requirements:

- Stable resource identifiers.
- Valid resource references.
- Correct patient references.
- Correct organization and practitioner references.
- Idempotent event processing.
- Retry and permanent-failure handling through existing outbox logic.
- No duplicate resources from repeated processing.
- Useful synchronization status and error visibility.
- Reconciliation support where already available.

Do not claim that live HAPI synchronization works unless it is actually tested against a live HAPI instance.

# 11. Audit and Blockchain Integration

Extend existing audit and blockchain allowlist behavior carefully.

Record security-relevant events such as:

- Laboratory order creation and cancellation.
- Report submission and amendment.
- Observation creation and amendment.
- Prescription creation and cancellation.
- Physician review.
- Unauthorized clinical access attempts.
- FHIR synchronization success or failure where appropriate.

Use the existing audit architecture.

Never store clinical data in blockchain transactions.

Use only approved metadata and pseudonymous references.

Do not modify historical audit records.

# 12. Database and Migrations

Implement SQLAlchemy models and Alembic migrations as required.

Requirements:

- Appropriate foreign keys.
- Unique constraints where needed.
- Indexes for common patient, provider, organization, and status queries.
- Correct deletion behavior.
- Explicit state-transition validation.
- Avoid duplicate or unnecessary models.
- Preserve PostgreSQL compatibility.
- Test migrations against a new disposable SQLite database.

Never use my existing PostgreSQL database for experimental migrations.

# 13. Testing Requirements

Add meaningful backend tests for:

- Lab order creation and authorization.
- Lab order cancellation.
- Lab report submission.
- Invalid report-to-order relationships.
- Report amendment and finalization restrictions.
- Observation validation and access control.
- Prescription creation and authorization.
- Prescription cancellation and amendment.
- Physician review.
- Consent revocation and expiry.
- Cross-patient access denial.
- Cross-organization access denial.
- FHIR outbox event creation.
- Duplicate synchronization processing.
- Audit event generation.

Frontend checks should cover available static diagnostics and existing build tooling.

Use deterministic synthetic test fixtures.

Do not weaken security checks just to pass tests.

# 14. Validation

Run available checks:

- Focused new backend tests.
- Existing relevant backend regression suite.
- API smoke tests.
- Security smoke tests.
- Python compilation.
- SQLite Alembic migration chain.
- `alembic check`.
- `git diff --check`.
- Frontend diagnostics and build if Node/npm are already available.

Do not install Node or download large packages merely to force a frontend build.

Clean up only temporary files created by this task. Do not delete existing project files or user work.

# 15. Completion Report

At the end, provide:

1. Architecture inspected.
2. Implementation plan followed.
3. Features implemented.
4. Database models and migration details.
5. Backend endpoints added or modified.
6. Frontend screens and components added or modified.
7. FHIR mappings implemented.
8. Consent and authorization protections.
9. Audit and blockchain integration.
10. Exact test counts and results.
11. Migration and validation results.
12. Git status.
13. Confirmation that no commit was created.
14. Confirmation that historical audit entry #33 was untouched.
15. Limitations and integrations not verified.

Classify every important result as:

- Implemented.
- Locally tested.
- Mocked integration tested.
- Live infrastructure verified.
- Not verified.

## Completion Standard

Do not mark the entire milestone complete merely because the code compiles.

The clinical workflows must work coherently across backend, frontend, authorization, persistence, audit, and FHIR outbox integration.

If the full milestone is too large to implement safely in one pass, complete it incrementally in this order:

1. Lab Orders.
2. Laboratory Reports.
3. Clinical Observations.
4. Prescriptions.
5. Physician Review.
6. Patient, Provider, and Laboratory dashboards.
7. Full regression and security validation.

Start by inspecting the repository and Git status. Preserve existing functionality and uncommitted work. Do not commit.