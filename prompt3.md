# MASTER PROMPT — HEALTHHARBOR MILESTONE 3
## Patient Discovery, Provider Connection & Consent-Based Care Initiation

You are continuing development of **HealthHarbor**, an interoperable, consent-aware healthcare data exchange platform.

This is an existing project with implemented architecture and previous milestones. You must extend the existing system rather than replace it or create a parallel implementation.

Your task is to complete the next milestone in alignment with the project's original vision, architecture, security principles, and implementation structure.

---

# 1. PRODUCT IDEOLOGY — DO NOT LOSE THIS

HealthHarbor is not intended to be another hospital-management CRUD application.

The core problem it addresses is:

A patient may visit multiple doctors, clinics, laboratories, and hospitals. Their prescriptions, laboratory reports, diagnostic records, and other important medical documents become fragmented across different healthcare providers.

Patients should be able to securely access and share their medical information with verified healthcare professionals, even when those professionals belong to different organizations.

The patient must remain in control of their information.

The platform must establish trust between:
- Patients
- Verified doctors
- Verified healthcare organizations
- Laboratory professionals
- Platform administrators

Every exchange must have a legitimate recipient, a clear purpose, appropriate authorization, and an auditable history.

**Build a real workflow, not merely screens that demonstrate the idea.**

# 2. EXISTING IMPLEMENTATION — PRESERVE IT

The previous milestones have established:

- React + Vite frontend
- FastAPI backend
- PostgreSQL database
- SQLAlchemy and Alembic migrations
- Keycloak authentication using OIDC/OAuth2 and PKCE
- HAPI FHIR R4 integration
- Hyperledger Fabric integration with Go chaincode and an HTTP gateway
- Off-chain clinical document storage
- Consent-based access control
- Application-level audit logging
- Patient, physician, healthcare organization, laboratory, and platform-admin roles

Milestone 2 implemented:

- Organization applications and manual verification
- Provider applications and manual verification
- Organization and provider suspension workflows
- Verified provider and organization directories
- Provider affiliations
- Organization-scoped administration
- Platform-admin affiliation oversight
- Registry review history
- Database-backed authorization checks
- Frontend Care Network / Registry Review workspace

Important verification results from Milestone 2:

- Backend: 57 passed, 1 PostgreSQL-only test skipped
- Registry API: 7 tests passed
- SQLite migration and Alembic checks passed
- Frontend production build and browser acceptance remain unverified
- Registry migration has not yet been tested against disposable PostgreSQL

Migration:
`2a7f9c6d4e81_healthcare_registry.py`

Frontend:
`RegistryWorkspace.jsx`

Read the actual repository before making assumptions.

# 3. FIRST TASK — CLOSE THE PREVIOUS MILESTONE'S VERIFICATION GATES

Before implementing new features:

1. Inspect the repository's current Git status and existing uncommitted changes.
2. Read:
   - `prompt.md`
   - `README.md`
   - `PROJECT_STATUS.md`
   - `IMPLEMENTATION_STATUS.md`
   - `ARCHITECTURE_REVIEW.md`
   - `SECURITY_ASSESSMENT.md`
   - `TESTING_REPORT.md`
   - `INTEGRATION_GUIDE.md`
3. Inspect the actual registry migration, registry API, service layer, frontend workspace, and related tests.
4. Determine whether Node.js and npm are available. If unavailable, report that honestly. Do not silently skip the frontend build and claim it passed.
5. Run the frontend production build when the required environment is available.
6. Perform browser acceptance testing when browser tooling is available.
7. Test the registry migration on a separate disposable PostgreSQL database.
8. Never use the existing project PostgreSQL database for migration experiments.
9. Never run destructive database commands against existing project data.
10. Record exact commands, outcomes, failures, and environmental limitations.

Do not alter implementation code merely to make a test pass. Investigate the cause and fix only genuine defects.

# 4. MILESTONE 3 — PATIENT DISCOVERY AND PROVIDER CONNECTION

Once the previous verification gates are addressed, implement the next coherent product workflow.

## A. Patient discovery

A patient should be able to:

- Browse verified healthcare organizations.
- Search for verified doctors.
- Filter providers by relevant available information, such as specialization, organization, or location, where the existing data model supports it.
- View a doctor's professional profile.
- See the doctor's verification status.
- See the healthcare organization or organizations with which the doctor is affiliated.
- Distinguish verified providers from pending, rejected, or suspended providers.

Only approved and active providers and organizations should appear as available healthcare choices.

Do not expose private verification evidence, confidential application data, or internal administrative notes in public directories.

Do not invent professional qualifications or claim official medical-license verification when no official verification integration exists.

## B. Patient-to-provider initiation

A patient must have a clear way to initiate a relationship or communication with a verified provider.

Design and implement a backend-supported workflow.

A possible lifecycle:

`INITIATED → ACCEPTED / DECLINED → CLOSED`

Adapt this to the existing domain model if a better structure already exists.

The workflow should support:

- Patient identity
- Selected verified provider
- Relevant healthcare organization
- Reason for initiating contact
- Request timestamp
- Current request status
- Provider response
- Relevant audit events

A provider must not automatically gain access to a patient's medical information simply because the patient initiated contact.

A care relationship and authorization to access records are separate concepts.

## C. Provider-initiated record requests

A verified provider should be able to request specific medical information from a patient when there is a legitimate care-related reason.

The request must identify:

- Requesting provider
- Provider's organization
- Patient
- Requested record categories or resources
- Purpose of access
- Requested access duration
- Request status

The patient must be able to review and respond to the request.

No record access should be granted merely because a provider created a request.

## D. Patient-controlled consent

Implement a clear consent decision workflow.

The patient must be able to:

- Review who is requesting access.
- Identify the actual doctor.
- Identify the doctor's affiliated organization.
- Review the stated purpose.
- Review the requested information scope.
- Review the requested duration.
- Approve or reject the request.
- Revoke previously granted consent.

Consent must remain resource-scoped and must respect the existing consent implementation.

Do not introduce a second, conflicting consent system.

Every authorization decision must be enforced by the backend using current database state.

Frontend visibility is not authorization.

## E. Provider workspace

Extend the existing provider workspace so doctors can:

- View incoming patient connection requests.
- View record-access requests.
- Review request details.
- Accept or decline appropriate requests.
- View patients who have initiated contact.
- See which records have actually been shared with them.
- Understand the scope and expiry of their access.

A provider must never see a patient's private records merely because they can see a connection request.

## F. Patient workspace

Extend the patient workspace so patients can:

- Discover verified providers and organizations.
- Initiate contact with a provider.
- Track outgoing requests.
- View provider responses.
- Review incoming record requests.
- Approve or reject record requests.
- View active sharing permissions.
- Revoke access.
- Review their sharing and access history.

The UI must explain the recipient, organization, purpose, scope, and duration clearly.

Avoid confusing consent screens that encourage patients to approve everything.

---

# 5. SECURITY REQUIREMENTS

These requirements are mandatory.

1. Enforce authorization on the backend for every protected operation.
2. Never trust frontend role checks as security controls.
3. Never trust stale JWT role or affiliation claims when the current database state can be checked.
4. Suspended providers must not initiate new patient-access workflows.
5. Suspended organizations must not continue receiving access through old affiliations.
6. Organization administrators must only manage their own organizations.
7. Patients must only manage their own requests and consent.
8. Providers must only access requests addressed to them.
9. Prevent IDOR vulnerabilities by checking ownership and authorization for every resource.
10. Prevent patients from being impersonated through manipulated request payloads.
11. Prevent users from assigning themselves privileged roles or provider verification status.
12. Validate consent scope, expiry, revocation, and recipient identity server-side.
13. Record important request, approval, rejection, revocation, and access events.
14. Avoid exposing private application evidence or unnecessary personal information.
15. Add tests for cross-tenant access and unauthorized request manipulation.

Never weaken existing security controls to simplify implementation.

# 6. FHIR INTEROPERABILITY

HealthHarbor must use FHIR as an actual interoperability layer, not as a decorative integration.

Inspect the existing HAPI FHIR integration before designing resource mappings.

Where appropriate, consider:

- `Patient`
- `Practitioner`
- `PractitionerRole`
- `Organization`
- `Consent`
- `Provenance`
- `AuditEvent`

Use existing resource conventions where available.

Do not create duplicate FHIR resources unnecessarily.

Maintain consistent mapping between application identities and FHIR identities.

Do not claim that a FHIR resource has been successfully persisted or exchanged unless the integration has actually been tested.

# 7. ARCHITECTURE AND IMPLEMENTATION RULES

Before implementation:

1. Map the existing patient, provider, organization, affiliation, consent, and audit models.
2. Identify reusable APIs and services.
3. Identify missing database relationships.
4. Design the request lifecycle and state transitions.
5. Define authorization rules for each transition.
6. Identify necessary additive migrations.
7. Define frontend workflows.
8. Define test cases.

Then implement incrementally.

Use the existing architecture and naming conventions.

Do not:
- Rewrite the application.
- Replace Keycloak.
- Replace the FHIR server.
- Introduce another database.
- Duplicate existing consent functionality.
- Create unnecessary microservices.
- Add blockchain writes for ordinary UI interactions.
- Store clinical documents or personally identifiable information on Fabric.
- Introduce unrelated features just to increase project complexity.

# 8. CROSS-ORGANIZATION DESIGN PRINCIPLE

The long-term goal is for different healthcare organizations to exchange information seamlessly.

For the current prototype, establish a secure shared exchange platform with organization isolation.

A patient from Organization A must be able to share authorized information with a verified provider from Organization B.

The backend must validate:

- Provider identity
- Provider verification status
- Organization status
- Active provider affiliation
- Patient identity
- Consent recipient
- Resource scope
- Purpose
- Expiry
- Revocation

Do not pretend that every hospital already operates an independent federated node.

Design the architecture so future federation is possible without prematurely implementing a distributed multi-hospital network.

# 9. FUTURE MILESTONE DIRECTION — SECURE CLINICAL RECORD EXCHANGE

Do not implement the entire future roadmap in this milestone.

However, make architectural decisions that support the following next milestone:

A patient can securely share a prescription, laboratory report, diagnostic report, discharge summary, or other clinical document with a verified provider at another organization.

The eventual exchange workflow must include:

- Private off-chain file storage
- Authenticated document access
- Encryption in transit and at rest
- Integrity verification
- FHIR metadata and resource mapping
- Consent enforcement before every protected access
- Expiring and revocable access
- Audit logging
- Appropriate minimal, pseudonymous Fabric integrity events

Clinical documents must never be stored directly on the blockchain.

Do not use public file URLs or unrestricted download links.

# 10. TESTING REQUIREMENTS

Add meaningful tests for:

- Patient provider discovery
- Hidden or unavailable suspended providers
- Organization isolation
- Patient initiating a provider connection
- Provider accepting or declining a request
- Provider accessing another provider's request
- Patient accessing another patient's request
- Provider requesting specific records
- Patient approving and rejecting requests
- Consent expiry
- Consent revocation
- Suspended provider access
- Suspended organization access
- Affiliation removal
- Cross-organization sharing authorization
- Audit event generation
- Invalid state transitions
- IDOR and manipulated request payloads

Run the full backend suite after implementation.

Run migration checks on SQLite and a separate disposable PostgreSQL database.

Run the frontend production build.

Perform browser acceptance testing where tooling is available.

Report skipped tests explicitly.

# 11. DEVELOPMENT PROCESS

Work in the following sequence:

**Stage 1 — Repository and architecture review**

Understand the actual implementation and produce a gap analysis.

**Stage 2 — Workflow and security design**

Document the lifecycle, database changes, API contracts, authorization rules, and UI flows.

**Stage 3 — Backend implementation**

Implement models, schemas, services, APIs, migrations, authorization, and audit events.

**Stage 4 — Backend verification**

Run focused tests, security regressions, full backend tests, and migration checks.

**Stage 5 — Frontend implementation**

Integrate the patient and provider workflows with actual backend APIs.

**Stage 6 — Frontend verification**

Run production build and browser acceptance tests.

**Stage 7 — Documentation**

Update project status, implementation status, testing report, architecture review, security assessment, integration guide, and README.

Do not report a stage as complete without evidence.

If a stage is blocked by missing dependencies or unavailable tooling, record the limitation and continue only with work that can be safely verified.

# 12. NON-NEGOTIABLE PRESERVATION RULES

- Inspect Git status before modifying files.
- Preserve all existing user changes.
- Do not discard, reset, overwrite, or clean unrelated files.
- Do not run destructive Git commands.
- Do not commit unless explicitly instructed.
- Do not modify the existing project PostgreSQL database.
- Use separate disposable databases for migration testing.
- Do not modify, delete, rewrite, reset, rehash, conceal, or attempt to repair historical audit entry #33.
- Do not claim production readiness.
- Use synthetic patient and clinical data only.
- Do not use real patient information for testing.
- Do not fabricate test results or integration success.

# 13. FINAL DELIVERY REPORT

At completion, provide:

1. What was implemented.
2. Which existing components were reused.
3. Database and migration changes.
4. API endpoints added or changed.
5. Frontend workflows added or changed.
6. Authorization and security controls.
7. FHIR integration status.
8. Tests executed and exact results.
9. Frontend build and browser verification status.
10. PostgreSQL migration verification status.
11. Known limitations and unresolved risks.
12. Files modified.
13. Recommended next milestone.

Clearly separate:
- Implemented
- Tested and passed
- Partially tested
- Not tested
- Not implemented

The objective is not to maximize the number of features.

The objective is to make HealthHarbor a coherent, secure, demonstrable healthcare exchange system where a patient can find a verified doctor, establish contact, and deliberately authorize access to medical information.

**Build the healthcare exchange workflow. Do not turn the project into another generic hospital management system.**