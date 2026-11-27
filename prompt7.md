# MILESTONE 7: HOSPITAL & MULTI-ORGANIZATION HEALTHCARE EXCHANGE
## HealthHarbor — Cross-Hospital Interoperability, Tenant Isolation, Organization-Scoped Authorization & Controlled Clinical Data Sharing

You are acting as a **Senior Healthcare Software Architect, Backend Engineer, Security Engineer, FHIR Interoperability Engineer, and Full-Stack Developer**.

Your task is to implement Milestone 7 of my existing final-year project, **HealthHarbor**.

This is an extension of an existing application. You must inspect and understand the current codebase before making changes. Do not create a separate application, replace the architecture, or rebuild working modules unnecessarily.

The objective is to transform HealthHarbor into a secure multi-organization healthcare exchange platform in which independent hospitals and healthcare organizations can collaborate while maintaining strict tenant isolation and patient-controlled authorization.

---

# 1. PROJECT CONTEXT

HealthHarbor is a consent-aware healthcare data exchange platform.

### Existing technology stack

- Frontend: React + Vite
- Backend: FastAPI / Python
- ORM: SQLAlchemy
- Database: PostgreSQL
- Migrations: Alembic
- Authentication: Keycloak OIDC / OAuth2 Authorization Code + PKCE
- Local development authentication mode
- FHIR interoperability: HAPI FHIR R4
- Blockchain: Hyperledger Fabric
- Chaincode: Go
- Integration: HTTP Gateway and transactional outbox
- Infrastructure: Docker Compose
- Testing: Python backend tests, API/security smoke tests, and integration tests

### Existing implementation milestones

Milestone 1: Identity and authentication.

Milestone 2: Healthcare registry, provider verification, organization applications, affiliations, and organization administration.

Milestone 3: Patient-provider care connections and consent-based record-access requests.

Milestone 4: Clinical document exchange and private document storage.

Milestone 5: Document encryption, integrity verification, malware scanning integration, and file security states.

Milestone 6: Durable FHIR synchronization outbox, stable resource identities, Patient, Practitioner, Organization and PractitionerRole mappings, retries, reconciliation, and administration APIs.

### Important existing implementation details

Inspect the actual repository rather than assuming these details remain unchanged.

Previous migration:
`c7f3a9d1e4b2`

This introduced durable FHIR synchronization infrastructure.

The previous backend verification reported:
- 71 targeted backend tests passed.
- One PostgreSQL-only audit test skipped.
- API and security smoke scripts passed.
- SQLite migration and Alembic schema checks passed.
- Live HAPI integration, PostgreSQL migration, frontend production build, and live Fabric delivery were not verified.

Treat these as historical results, not proof of the current repository's condition.

---

# 2. PRIMARY OBJECTIVE

Implement a genuine multi-hospital healthcare exchange workflow.

Example:

- Hospital A has a registered patient.
- The patient receives treatment at Hospital A.
- The patient later visits Hospital B.
- Hospital B needs access to selected medical records from Hospital A.
- Hospital B submits a legitimate access request.
- The patient reviews and approves or rejects the request.
- Only approved resources within the approved scope become accessible.
- Hospital B can access the permitted records through secure application APIs.
- The access is recorded in the audit system.
- Revoking consent immediately prevents subsequent access.

This workflow must work across different organizations.

**Do not implement unrestricted organization-to-organization data sharing.**

An organization relationship, provider affiliation, care connection, FHIR resource, blockchain transaction, or access request does not independently authorize clinical record access.

The current database authorization model and active patient consent remain authoritative.

---

# 3. MANDATORY PRESERVATION RULES

Before implementation:

1. Inspect `git status`.
2. Identify all existing modifications and untracked files.
3. Read the README, architecture documentation, project instructions, and previous milestone reports.
4. Inspect existing models, services, routers, authorization dependencies, migrations, FHIR integration, audit infrastructure, blockchain integration, and frontend routes.
5. Identify existing multi-organization capabilities and extend them rather than duplicating them.

Strictly preserve:

- All existing user work and uncommitted modifications.
- Existing authentication behavior.
- Existing patient consent and revocation behavior.
- Existing clinical document encryption and malware scanning protections.
- Existing FHIR outbox and synchronization mechanisms.
- Existing blockchain integration.
- Existing audit history.

**Historical audit entry #33 must remain completely untouched.**

Never:
- Run `git reset --hard`.
- Run `git clean`.
- Delete or overwrite existing project work.
- Rewrite, delete, re-hash, or repair historical audit entries.
- Use real patient information.
- Commit changes without my explicit permission.
- Experiment against my existing PostgreSQL database.

Use synthetic data only.

---

# 4. MULTI-TENANT ARCHITECTURE

Implement organization-aware data access and authorization.

First inspect the existing database schema and determine how organizations, providers, affiliations, patients, care connections, consents, documents, and clinical records are represented.

Do not introduce a second organization model if a suitable one already exists.

### Required behavior

Every organization-scoped operation must establish:

- The authenticated user.
- Their current provider or administrative identity.
- Their active organization affiliation.
- Their organization membership status.
- Their organization verification and suspension status.
- Their permitted organization role.
- The resource's owning organization.
- The patient's ownership relationship.
- Whether a valid patient consent authorizes the requested action.

Use current database state for authorization, not stale JWT role or affiliation claims.

### Tenant isolation

Enforce tenant boundaries at the backend service and database-query levels.

Examples:

- Hospital A administrators cannot list Hospital B's patients.
- Hospital A providers cannot inspect Hospital B's internal records.
- Hospital B cannot modify Hospital A's original clinical documents.
- An organization cannot modify another organization's provider affiliations.
- An organization cannot approve its own verification application through unauthorized endpoints.
- Organization administrators cannot access platform-wide administrative operations.
- Suspended organizations cannot perform clinical exchange operations.

Do not rely exclusively on frontend filtering.

Return appropriate authorization errors without leaking whether unauthorized resources exist.

Where appropriate, use centralized tenant-scoping helpers or authorization services rather than duplicating fragile checks across routers.

If PostgreSQL Row-Level Security is suitable for the existing architecture, evaluate it and document the decision. Do not introduce it without a reliable connection-context and transaction strategy.

---

# 5. ORGANIZATION-TO-ORGANIZATION EXCHANGE WORKFLOW

Implement an explicit workflow for cross-hospital clinical record exchange.

### A. Exchange request

An authorized provider from Hospital B should be able to initiate a clinical exchange request for a patient.

The request must include:

- Patient reference.
- Requesting organization.
- Requesting provider.
- Source organization, where known.
- Purpose of access.
- Requested record categories.
- Requested resource scope.
- Requested validity period.
- Request status.
- Creation timestamp.
- Decision history.

Use existing care-request and consent models where possible.

Avoid creating redundant request models if the existing architecture can support this safely.

### B. Patient decision

The patient must be able to:

- View the requesting organization.
- View the requesting provider.
- Understand the purpose of the request.
- Review the requested resource categories.
- Approve or reject the request.
- See the request's validity period.
- Revoke previously granted access.

Approval must create or activate the appropriate existing consent representation.

Rejection must not create active consent.

A request must never become approved simply because a provider or organization is affiliated with a hospital.

### C. Access enforcement

Before returning any protected record, check:

1. User authentication.
2. Active provider identity.
3. Provider verification.
4. Active affiliation with the requesting organization.
5. Organization verification and status.
6. Patient ownership and identity relationship.
7. Current active consent.
8. Consent expiry.
9. Consent revocation.
10. Requested resource scope.
11. Permitted purpose and operation.
12. Resource availability and security-processing status.

Use the existing authorization architecture and centralize the checks.

Never trust a client-provided organization ID, patient ID, FHIR reference, document ID, or resource owner field as authorization evidence.

---

# 6. CROSS-HOSPITAL CLINICAL DOCUMENT EXCHANGE

Extend the existing secure document exchange implementation.

Required behavior:

- Patients can view records associated with their care.
- Authorized providers can retrieve permitted records from another hospital.
- Original source documents remain associated with their originating organization.
- The receiving hospital must not silently become the owner of the source document.
- Any permitted copy or import must be represented as a separate, traceable operation.
- Preserve document integrity and original metadata.
- Preserve encryption and malware-scanning protections.
- Do not expose private storage paths or encryption keys.
- Do not permit unscanned, malicious, failed-processing, or otherwise unavailable documents to become downloadable.
- Revocation must block subsequent downloads and retrieval.

If document imports are implemented, track:

- Source organization.
- Receiving organization.
- Source document reference.
- Importing provider.
- Import timestamp.
- Integrity/checksum verification result.
- Original document provenance.
- Applicable patient consent.

Do not duplicate document bytes unnecessarily.

---

# 7. FHIR R4 CROSS-ORGANIZATION INTEROPERABILITY

Extend the existing Milestone 6 FHIR architecture.

Do not create an unrelated FHIR integration layer.

Use the existing HAPI FHIR R4 client, resource identity mappings, outbox, retry mechanism, and reconciliation infrastructure.

### Required capabilities

- Represent organizations with stable FHIR Organization identities.
- Represent providers and their organizational roles correctly.
- Maintain PractitionerRole organization references.
- Preserve patient identity mappings.
- Support organization-aware resource references.
- Maintain correct DocumentReference references.
- Maintain appropriate Consent representations.
- Preserve Provenance and AuditEvent information where supported by the existing design.

### Cross-organization resource access

FHIR resource availability must not imply authorization.

The backend must check current application authorization before returning protected resources.

Direct HAPI FHIR access must not create an alternate route around application security.

If the existing architecture allows direct HAPI access, inspect and document the exposure. Restrict access through appropriate network, gateway, or application controls.

### Resource ownership

Maintain clear distinctions between:

- Resource originating organization.
- Patient owner.
- Current custodian.
- Requesting organization.
- Receiving organization.
- Authorized provider.

Do not incorrectly overwrite the source organization when another hospital reads or imports a resource.

### Synchronization

Use the existing durable outbox for all applicable changes.

Ensure:
- Idempotent processing.
- Retry behavior.
- Permanent-failure tracking.
- Reconciliation.
- Stable resource identifiers.
- No duplicate resource creation.
- No silent overwrites.
- Organization references remain consistent.

Do not claim successful remote synchronization without actual HAPI confirmation.

---

# 8. HOSPITAL DIRECTORY AND EXCHANGE DISCOVERY

Improve the organization directory to support multi-hospital workflows.

Provide appropriate views for:

### Patients
- Available verified hospitals.
- Their existing care relationships.
- Cross-hospital exchange requests.
- Active sharing permissions.
- Previously shared records.
- Revoked and expired permissions.

### Providers
- Their verified organization.
- Their active affiliations.
- Available cross-hospital request workflows.
- Pending exchange requests.
- Approved access scopes.
- Access history.

### Organization administrators
- Organization profile.
- Verified providers.
- Active affiliations.
- Organization-level exchange activity.
- Requests initiated by their organization.
- Operational synchronization status.

### Platform administrators
- Organization verification oversight.
- Organization suspension and reinstatement.
- High-level exchange monitoring.
- Organization status and integration health.

Do not expose patient clinical information in organization-level dashboards unless explicitly authorized.

---

# 9. AUDITABILITY AND ACCOUNTABILITY

Every sensitive cross-organization action must produce appropriate audit evidence.

Examples:

- Exchange request creation.
- Patient approval or rejection.
- Consent revocation.
- Cross-hospital document retrieval.
- Clinical resource retrieval.
- Document import.
- Failed authorization attempts.
- Organization suspension affecting active exchanges.
- FHIR synchronization failure where relevant.

Audit records should identify:

- Actor.
- Actor organization.
- Patient reference.
- Source organization.
- Receiving/requesting organization.
- Action.
- Resource type and pseudonymous resource reference.
- Timestamp.
- Outcome.
- Relevant consent reference.

Avoid placing clinical content, credentials, tokens, or unnecessary personal information in audit events.

Use the existing append-only audit infrastructure.

Never modify historical audit records, particularly audit entry #33.

---

# 10. HYPERLEDGER FABRIC INTEGRATION

Inspect the existing Fabric implementation before changing it.

Do not replace the existing chaincode or blockchain architecture unnecessarily.

Evaluate which cross-organization events should be recorded on the permissioned ledger.

Potential events include:

- Organization exchange request created.
- Patient consent granted.
- Patient consent revoked.
- Cross-organization document exchange completed.
- Integrity verification completed.

Only record appropriately minimized, pseudonymous, tamper-evident metadata.

Never store:
- Clinical document contents.
- Patient names.
- Medical histories.
- Authentication credentials.
- Access tokens.
- Encryption keys.
- Direct identifiers.

Blockchain must remain an audit and integrity layer, not an authorization engine.

Application authorization must continue to use current database state.

Use durable delivery and idempotency where the existing Fabric outbox architecture supports it.

Do not report ledger confirmation unless the Fabric network actually confirms the transaction.

If Fabric is unavailable in the development environment, implement and test the appropriate adapter boundaries without pretending that live delivery occurred.

---

# 11. FRONTEND IMPLEMENTATION

Extend the existing React application consistently.

Do not create a disconnected demonstration interface.

Build functional, API-backed workflows.

### Patient workspace

Add or extend:

- Hospital exchange requests.
- Request details.
- Patient approval and rejection.
- Active cross-hospital permissions.
- Revocation controls.
- Shared clinical document history.
- Source hospital information.
- Exchange activity history.

### Provider workspace

Add or extend:

- Hospital directory.
- Cross-hospital exchange initiation.
- Requested record categories.
- Pending request status.
- Approved record access.
- Source organization identification.
- Secure document retrieval.
- Exchange activity.

### Organization administrator workspace

Add or extend:

- Organization information.
- Provider affiliations.
- Exchange request monitoring.
- Organization-level operational status.
- FHIR synchronization visibility.

### UX requirements

- Clear loading states.
- Empty states.
- Error handling.
- Authorization-denied messages.
- Pending, approved, rejected, expired, and revoked states.
- Accessible forms and controls.
- Responsive design.
- Consistent visual language.

Do not display fake success notifications.

Do not use hardcoded clinical records as if they were real API results.

---

# 12. SECURITY TESTING — HIGHEST PRIORITY

Build an explicit tenant-isolation and cross-organization authorization test suite.

At minimum, test the following scenarios.

### Tenant isolation

1. Hospital A administrator cannot list Hospital B's providers.
2. Hospital A administrator cannot modify Hospital B's affiliations.
3. Hospital A provider cannot access Hospital B's private records without authorization.
4. Hospital B cannot alter the source hospital's original document.
5. A suspended organization cannot initiate exchanges.
6. A suspended provider cannot access cross-hospital resources.
7. A provider cannot impersonate another organization by changing request parameters.
8. A client cannot bypass organization restrictions by modifying resource IDs.

### Consent security

9. An access request alone does not authorize record retrieval.
10. Provider affiliation alone does not authorize record retrieval.
11. Organization verification alone does not authorize record retrieval.
12. Patient rejection does not create active consent.
13. Expired consent blocks subsequent access.
14. Revoked consent blocks subsequent access.
15. Consent for one document category does not authorize unrelated categories.
16. Consent for one patient cannot authorize access to another patient's records.
17. A provider cannot broaden an approved scope through modified API parameters.

### Document security

18. Unauthorized document download is denied.
19. Cross-organization retrieval preserves source ownership.
20. Unscanned or malicious documents remain inaccessible.
21. Imported document metadata retains provenance.
22. Revocation blocks subsequent document retrieval.

### FHIR security

23. FHIR resource references cannot bypass tenant authorization.
24. Direct Binary retrieval cannot bypass consent.
25. A failed FHIR synchronization does not grant access.
26. A stale FHIR resource does not override current database authorization.

### Audit and blockchain

27. Sensitive exchange operations produce appropriate audit records.
28. Audit events do not contain clinical document contents or secrets.
29. Blockchain delivery failures do not grant authorization.
30. Duplicate event delivery does not create duplicate logical operations.

Use the existing testing conventions.

Include both positive and negative authorization tests.

---

# 13. DATABASE AND MIGRATIONS

Inspect the existing schema before designing migrations.

Use additive migrations wherever possible.

Requirements:

- Preserve existing patient, organization, provider, affiliation, consent, care-request, document, and FHIR relationships.
- Use foreign keys and appropriate indexes.
- Add uniqueness constraints where required.
- Ensure ownership and source-organization references are unambiguous.
- Prevent duplicate exchange operations.
- Maintain backward compatibility where practical.
- Avoid destructive schema changes.

Test migrations using:

1. Disposable SQLite database.
2. Disposable PostgreSQL database, if available.

Never use the existing personal PostgreSQL database.

Run:
- Alembic upgrade to head.
- Alembic schema consistency checks.
- Relevant migration regression tests.

Document PostgreSQL-specific behavior separately if it cannot be verified.

---

# 14. DOCUMENTATION

Update the actual project documentation.

Include:

- Multi-organization architecture.
- Tenant isolation model.
- Cross-hospital exchange lifecycle.
- Patient consent lifecycle.
- Organization and provider authorization rules.
- FHIR resource ownership and identity mapping.
- Document provenance and custody.
- Audit and Fabric event boundaries.
- API endpoint documentation.
- Database model changes.
- Environment configuration.
- Local development setup.
- Security limitations.
- Integration verification status.

Add architecture diagrams where appropriate.

The documentation must distinguish implemented features from integrations that have not been verified.

---

# 15. IMPLEMENTATION STRATEGY

Work incrementally.

### Phase 1 — Repository inspection
Understand current architecture and identify missing capabilities.

### Phase 2 — Tenant isolation
Implement and test organization-scoped access controls.

Do not proceed until tenant-isolation tests pass.

### Phase 3 — Cross-hospital exchange lifecycle
Implement exchange requests, patient decisions, consent enforcement, and revocation.

### Phase 4 — Clinical document exchange
Implement source ownership, provenance, secure retrieval, and optional controlled import.

### Phase 5 — FHIR interoperability
Extend existing FHIR mappings and durable synchronization infrastructure.

### Phase 6 — Audit and Fabric integration
Extend existing accountability and ledger mechanisms without storing sensitive clinical data.

### Phase 7 — Frontend workflows
Connect patient, provider, organization, and platform administration interfaces to actual APIs.

### Phase 8 — Verification
Run backend, migration, security, API, frontend, and integration tests.

Fix regressions before reporting completion.

---

# 16. QUALITY REQUIREMENTS

The implementation must be:

- Secure by default.
- Tenant-isolated.
- Patient-consent-aware.
- Auditable.
- Idempotent where appropriate.
- Maintainable.
- Modular.
- Testable.
- Consistent with existing architecture.
- Suitable for a credible academic software engineering demonstration.

Avoid:

- Fake blockchain functionality.
- Fake FHIR synchronization.
- Hardcoded exchange approvals.
- Trusting frontend authorization.
- Unrestricted hospital-to-hospital access.
- Duplicate organization models.
- Duplicate consent systems.
- Unnecessary microservices.
- Unnecessary architectural rewrites.
- Hardcoded secrets.
- Silent exception handling.
- Insecure document copying.
- Claims of production readiness without evidence.

Do not introduce unnecessary complexity just to make the architecture look impressive.

---

# 17. FINAL ACCEPTANCE CRITERIA

Milestone 7 is complete only when the following workflow is demonstrably functional:

1. Hospital A and Hospital B exist as separate verified organizations.
2. Each organization has independently affiliated verified providers.
3. A synthetic patient has clinical records originating from Hospital A.
4. A provider at Hospital B initiates a cross-hospital access request.
5. The patient sees the requesting hospital, provider, purpose, and requested scope.
6. The patient approves the request.
7. Hospital B's authorized provider retrieves only the approved records.
8. The retrieved records retain their source organization and provenance.
9. All relevant access operations produce audit evidence.
10. FHIR synchronization is performed through the existing outbox architecture.
11. Revoking consent blocks subsequent access.
12. Hospital A cannot access Hospital B's private data without appropriate authorization.
13. Hospital B cannot access unrelated patients' data.
14. Suspended organizations and providers cannot continue unauthorized exchange operations.
15. Existing application workflows and security tests continue passing.

A mocked integration is not equivalent to live HAPI or Fabric verification.

---

# 18. FINAL REPORT — REQUIRED FORMAT

At completion, provide a detailed implementation report using these sections:

## A. Executive Summary
What was implemented and whether Milestone 7 is complete, partially complete, or blocked.

## B. Architecture Changes
Explain the tenant-isolation and cross-hospital architecture.

## C. Database Changes
List every migration, new model, modified model, relationship, constraint, and index.

## D. Backend Changes
List implemented APIs, services, authorization checks, and workflows.

## E. Frontend Changes
List patient, provider, organization, and platform administrator UI changes.

## F. FHIR Integration
Explain resource mappings, organization references, outbox behavior, retries, and actual HAPI verification.

## G. Fabric Integration
Explain the recorded event types and actual transaction-delivery verification.

## H. Security Verification
Provide a scenario-by-scenario table of passed, failed, skipped, and not-run tests.

## I. Test Results
Report exact commands and actual results.

## J. Unverified Items
Clearly identify all features that could not be verified.

## K. Files Changed
List important added and modified files.

## L. Git Status
Confirm whether changes remain uncommitted. Do not commit without permission.

## M. Remaining Risks
Identify security, privacy, interoperability, and deployment limitations.

---

# FINAL INSTRUCTION

Build Milestone 7 into the existing HealthHarbor project.

Do not merely create documentation, mockups, or placeholder endpoints.

Inspect the repository, identify the actual implementation gaps, and implement the highest-priority missing functionality end to end.

Prioritize **strict tenant isolation and patient-controlled cross-hospital access** over adding superficial features.

Preserve all existing work, preserve historical audit entry #33, avoid the existing PostgreSQL database, use synthetic data, and do not create a Git commit.

If a required external service is unavailable, implement the correct integration boundary, test what can be tested, and clearly report what remains unverified.

I expect a working, secure, maintainable multi-organization healthcare exchange implementation — not just a prototype that looks functional.