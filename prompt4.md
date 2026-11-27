# COPILOT MASTER PROMPT — HEALTHHARBOR MILESTONE 4
## Secure Clinical Document Exchange, Consent-Enforced Access & FHIR Interoperability

You are acting as the lead software architect, senior full-stack engineer, application security engineer, and test engineer for **HealthHarbor**.

Your responsibility is to continue developing the existing HealthHarbor repository into a coherent, secure, consent-aware healthcare information exchange platform.

This is an existing project. Do not replace it with a new implementation, generate a disconnected demo, or redesign the architecture without first understanding the current codebase.

---

# 1. PRODUCT VISION — NON-NEGOTIABLE

HealthHarbor is intended to let patients securely share prescriptions, laboratory reports, diagnostic documents, and other medical records with verified healthcare providers across participating healthcare organizations.

The fundamental workflow is:

1. Patients discover verified doctors and healthcare organizations.
2. Patients initiate care connections.
3. Doctors respond to care requests.
4. Providers can request specific patient records.
5. Patients explicitly approve or reject those requests.
6. Approved requests create the existing consent records.
7. Patients and authorized providers exchange clinical documents.
8. Every important action is auditable.
9. Patients can revoke access.
10. Expired, revoked, suspended, or otherwise invalid permissions must immediately prevent further access.

**The patient remains in control of their medical information.**

A care connection is not consent.  
A record request is not consent.  
An organization affiliation is not consent.  
A blockchain event is not consent.

Only a valid authorization decision enforced by the backend can grant access.

---

# 2. EXISTING ARCHITECTURE — PRESERVE IT

First inspect the complete repository and existing implementation.

Expected architecture:

- Frontend: React + Vite
- Backend: FastAPI
- Language: Python
- ORM: SQLAlchemy
- Migrations: Alembic
- Database: PostgreSQL
- Authentication: Keycloak using OIDC/OAuth2 Authorization Code + PKCE
- Interoperability: HAPI FHIR R4
- Blockchain: Hyperledger Fabric
- Chaincode: Go
- Gateway: HTTP adapter
- Event delivery: transactional outbox
- Deployment: Docker Compose
- Testing: unittest-style backend tests, security tests, OWASP ZAP and k6 where available

Inspect the actual repository before assuming every component is implemented or operational.

Read:

- `prompt.md`
- `README.md`
- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `TESTING_REPORT.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `INTEGRATION_GUIDE.md`
- Existing backend models, schemas, services, routes, dependencies and migrations
- Existing frontend workspaces and API client
- Existing FHIR and blockchain integration code
- Existing tests and fixtures

Preserve existing architectural decisions unless a demonstrable security or correctness issue requires a change.

---

# 3. MANDATORY PRESERVATION RULES

Before changing anything:

1. Run `git status --short`.
2. Inspect existing uncommitted changes.
3. Identify the current migration head.
4. Inspect the latest care-request implementation and migration:
   `f4c1a6d2e9b7_patient_provider_care_requests.py`
5. Inspect the existing consent and file-access implementation.
6. Understand the existing audit and transactional-outbox architecture.

Never:

- Run `git reset --hard`.
- Run `git clean`.
- Discard, overwrite, or revert user changes.
- Rewrite migration history.
- Delete or repair historical audit records.
- Modify historical audit entry #33.
- Introduce fake clinical records or real patient information.
- Commit changes unless explicitly requested.
- Claim an integration or test passed when it was not executed.

Use synthetic data exclusively.

---

# 4. FIRST TASK — CLOSE PREVIOUS VERIFICATION GAPS

Before implementing Milestone 4, investigate the outstanding verification gaps.

### Frontend verification

Attempt the frontend production build using the existing environment.

If Node/npm are unavailable:

- Do not install unknown scripts or modify the system environment.
- Do not pretend the build succeeded.
- Record the exact blocker.
- Continue only with checks that can genuinely be performed.

Run browser acceptance tests only if a suitable browser or test harness is available.

### PostgreSQL migration verification

Check whether an isolated disposable PostgreSQL environment is available.

If available:

- Create a separate temporary database.
- Test migration from the preceding migration through the current head.
- Verify the registry and care-request migrations.
- Run Alembic schema consistency checks.
- Verify constraints and indexes.
- Never connect to or modify the user's existing PostgreSQL database.

If PostgreSQL tooling is unavailable, document the limitation.

### Regression verification

Run:

- Full backend test suite.
- Existing API smoke tests.
- Existing security smoke tests.
- Python compilation.
- `git diff --check`.

Do not conceal skipped tests.

If a critical regression is discovered, diagnose it before proceeding.

---

# 5. MILESTONE 4 — SECURE CLINICAL DOCUMENT EXCHANGE

Implement a complete, backend-enforced document exchange workflow.

The implementation should support a patient uploading a medical document and explicitly sharing it with a provider who has valid consent.

## 5.1 Patient document management

Patients should be able to:

- Upload a clinical document.
- View their own uploaded documents.
- See document metadata.
- Identify document type and issuing organization where known.
- View when a document was uploaded.
- View its current sharing permissions.
- See which authorized providers can access it.
- Review document-access history.
- Remove a document from active availability where permitted by the project's retention rules.

Do not expose patient documents through public URLs or unauthenticated static directories.

Implement document ownership at the backend.

A patient must never be able to access another patient's document by changing an identifier.

## 5.2 Supported document types

Inspect the current FHIR and application models before selecting the final document types.

Design an extensible classification system that can initially support:

- Laboratory reports
- Prescriptions
- Diagnostic reports
- Medical certificates
- Clinical notes
- Discharge summaries
- Other supporting medical documents

Do not assume that every uploaded PDF is a valid clinical document.

Store descriptive metadata separately from the binary file.

## 5.3 Secure upload handling

Implement secure upload validation.

Requirements:

- Allowlisted file extensions and MIME types.
- Actual content-type validation rather than trusting browser-supplied MIME values.
- Configurable file-size limits.
- Safe filenames and generated storage identifiers.
- Path traversal protection.
- Duplicate and integrity detection where appropriate.
- File checksum generation.
- Safe handling of malformed or unsupported files.
- Authentication and authorization before accepting uploads.
- Clear API error responses.

Never trust a client-provided patient ID, owner ID, storage path, or authorization status.

The backend must derive ownership from the authenticated identity and verified application-level account mapping.

Do not implement antivirus scanning as a fictional feature. If no scanner exists, document that limitation and design a safe integration point.

## 5.4 Private document storage

Create or improve a storage abstraction.

The application should not depend directly on publicly accessible file paths.

Separate:

- Storage interface
- Local development storage adapter
- Document metadata persistence
- Authorization service
- Download delivery

The local development adapter must store files outside publicly served frontend directories.

Never expose internal storage paths through API responses.

Use established cryptographic libraries and managed key material if application-level encryption is implemented. Do not invent cryptographic algorithms or hardcode encryption keys.

If managed KMS integration is not available, clearly document the local prototype's storage-encryption limitations and define the production KMS integration boundary.

Do not claim production-grade encryption merely because HTTPS is enabled.

## 5.5 Consent-enforced document access

This is the most important requirement.

Every document read or download must be authorized by the backend using current database state.

The authorization decision must verify:

1. The authenticated user.
2. The patient's ownership of the document.
3. The provider's verified identity.
4. The provider's current active status.
5. The provider's active affiliation with the relevant organization, where applicable.
6. The organization's current approved and active status.
7. The existence of an applicable consent record.
8. The consent's resource scope.
9. The consent's purpose and validity period.
10. The consent's current revocation status.

Use the existing consent model and authorization services wherever possible.

Do not introduce a second competing consent system.

Authorization must not rely exclusively on stale JWT claims or frontend state.

A previously authorized provider must lose access when:

- Consent is revoked.
- Consent expires.
- The provider is suspended.
- The organization is suspended.
- The relevant affiliation becomes inactive.
- The resource falls outside the granted scope.

Test each scenario.

## 5.6 Document sharing workflow

Build a clear workflow:

**Patient uploads document → Patient selects an eligible provider → Patient reviews requested scope → Patient explicitly grants consent → Provider accesses authorized document.**

Also support the existing care-request workflow:

**Provider requests records → Patient reviews request → Patient approves or rejects → Approval creates the existing consent record → Authorized document access becomes available.**

Important:

- Do not automatically share all documents.
- Do not grant access because a provider belongs to an organization.
- Do not treat an accepted care connection as permission to access records.
- Do not let a provider approve their own access request.
- Do not let a patient approve a request on behalf of another patient.
- Do not allow a provider to access records merely by guessing document identifiers.

The patient must understand what they are sharing and with whom.

## 5.7 Secure download API

Implement authenticated document retrieval.

Possible route design, subject to existing API conventions:

- `POST /api/v1/documents`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `GET /api/v1/documents/{document_id}/download`
- `DELETE /api/v1/documents/{document_id}`

Adapt these routes to the existing architecture rather than creating duplicate endpoints.

Requirements:

- Every download must pass server-side authorization.
- Return only the requested document.
- Use safe content-disposition headers.
- Prevent path traversal and storage identifier manipulation.
- Avoid exposing internal storage locations.
- Use appropriate cache-control headers for sensitive clinical data.
- Log successful and denied access attempts without logging clinical document contents.
- Do not create public or permanent share links.

A download URL must not bypass authentication or consent checks.

## 5.8 Patient and provider interfaces

Extend the existing React workspaces.

Do not create an unrelated standalone frontend.

### Patient workspace

Add a document-management area that supports:

- Uploading documents.
- Viewing document metadata.
- Reviewing document categories.
- Viewing active sharing permissions.
- Reviewing pending record requests.
- Approving or rejecting requests.
- Revoking consent.
- Viewing document-access history.

### Doctor workspace

Add a patient-records area that supports:

- Viewing patients with whom the provider has an established care connection.
- Viewing records only when valid consent exists.
- Viewing authorized document metadata.
- Downloading authorized documents.
- Viewing the applicable consent scope and expiry.
- Seeing a clear denied-access state when permission is unavailable.

Do not expose unauthorized patient information merely to make the interface look populated.

### Registry and organization workspace

Maintain existing responsibilities.

Organization administrators should not receive automatic access to patient documents.

---

# 6. FHIR R4 INTEROPERABILITY

HealthHarbor must use FHIR as an interoperability layer rather than treating its internal database as the only representation of clinical records.

Inspect the existing HAPI FHIR integration before implementation.

Use appropriate FHIR R4 resources where semantically correct:

- `DocumentReference`
- `Binary`
- `Patient`
- `Practitioner`
- `PractitionerRole`
- `Organization`
- `Consent`
- `Provenance`
- `AuditEvent`

Use `DiagnosticReport`, `Observation`, `MedicationRequest`, or other resources when the actual clinical meaning justifies them.

Important:

- Do not map every internal application object to an arbitrary FHIR resource.
- Do not create misleading clinical resources.
- Do not place clinical binary contents into ordinary application logs.
- Do not assume a successful local database write means HAPI FHIR synchronization succeeded.
- Document the source of truth and synchronization strategy.
- Handle HAPI FHIR unavailability without silently losing records.
- Use retryable integration patterns where appropriate.

If the existing transactional outbox is suitable, reuse it.

FHIR identifiers and references must be consistent and must not expose another patient's records.

Use synthetic FHIR data for tests.

---

# 7. HYPERLEDGER FABRIC INTEGRATION

Inspect the current chaincode and gateway before extending blockchain functionality.

Blockchain must support tamper-evident evidence, not become a storage location for medical records.

Potential allowlisted events:

- Document uploaded.
- Document shared.
- Consent granted.
- Consent revoked.
- Document accessed.
- Document made unavailable.

Only emit events that fit the existing architecture and security model.

Requirements:

- No patient names on-chain.
- No provider names on-chain.
- No medical document contents on-chain.
- No prescriptions, laboratory results, or diagnoses on-chain.
- No raw personal identifiers on-chain.
- Use pseudonymous references and integrity hashes where appropriate.
- Do not expose blockchain transaction identifiers as proof of clinical correctness.
- Do not claim a blockchain transaction succeeded unless a committed result is confirmed.

Use the transactional outbox if already implemented.

If Fabric is unavailable, preserve the pending event safely and report the integration as unverified.

Do not make core patient access authorization dependent on an unavailable blockchain network.

The authoritative access decision remains the backend's current authorization state.

---

# 8. AUDIT AND SECURITY

Extend the existing audit architecture.

Record meaningful events such as:

- Document upload.
- Document metadata access.
- Document download.
- Upload rejection.
- Unauthorized access attempt.
- Consent approval.
- Consent revocation.
- Document removal or archival.

Audit records should capture appropriate actor, action, resource reference, timestamp, outcome, and correlation information.

Never log:

- Medical document contents.
- Passwords.
- Access tokens.
- Refresh tokens.
- Encryption keys.
- Unnecessary sensitive clinical information.

Maintain append-only audit behavior.

Never rewrite, delete, reset, re-hash, hide, or repair historical audit entries.

**Historical audit entry #33 must remain untouched.**

Add tests that verify audit behavior without targeting or changing historical records.

---

# 9. DATABASE AND MIGRATIONS

Inspect existing models before adding new ones.

Potential entities may include:

- ClinicalDocument
- DocumentMetadata
- DocumentStorageReference
- DocumentAccessEvent

These are conceptual names, not instructions to create duplicate models.

Reuse existing models where appropriate.

Requirements:

- Correct foreign keys.
- Appropriate indexes.
- Ownership constraints.
- Referential integrity.
- Tenant and organization isolation.
- Safe migration defaults.
- No destructive migration.
- No rewriting existing migration files.

Create a new additive Alembic migration only if the schema genuinely requires one.

Test the migration using:

1. Fresh isolated SQLite database.
2. Disposable PostgreSQL database if tooling is available.
3. `alembic check`.

Never run experimental migrations against the user's existing PostgreSQL database.

---

# 10. REQUIRED TESTING

Write tests before declaring the milestone complete.

### Upload tests

- Authorized patient upload succeeds.
- Unauthenticated upload fails.
- Unsupported file type is rejected.
- Oversized upload is rejected.
- Malformed upload is handled safely.
- Filename and path traversal attempts are rejected.
- A patient cannot upload under another patient's identity.

### Ownership tests

- Patient can view their own documents.
- Patient cannot view another patient's documents.
- Patient cannot download another patient's documents.
- Changing a document ID does not bypass ownership checks.

### Consent tests

- Provider cannot download without consent.
- Approved consent permits only the authorized scope.
- Rejected requests create no consent.
- Revoked consent blocks future downloads.
- Expired consent blocks future downloads.
- Out-of-scope documents remain inaccessible.
- A care connection alone grants no access.

### Provider and organization tests

- Unverified provider is denied.
- Suspended provider is denied.
- Inactive affiliation is denied where required.
- Suspended organization is denied where required.
- Unauthorized organization administrator is denied.
- Stale JWT role or status claims do not override current database state.

### Audit tests

- Successful access creates an appropriate audit event.
- Denied access is recorded where applicable.
- Audit records do not contain clinical contents or secrets.
- Historical audit history remains unchanged.

### FHIR tests

- Valid DocumentReference mapping.
- Correct patient and organization references.
- Appropriate Binary handling.
- FHIR service unavailable behavior.
- Retry or failure handling.
- No accidental PHI leakage into logs.

### Frontend tests

- Upload workflow.
- Consent review workflow.
- Revocation workflow.
- Provider document visibility.
- Unauthorized access state.
- Loading and error states.

Do not weaken existing tests to make new tests pass.

---

# 11. ENGINEERING QUALITY

Follow the existing codebase conventions.

Prioritize:

- Separation of concerns.
- Small, maintainable services.
- Strong typing and validation.
- Clear authorization boundaries.
- Reusable API clients.
- Consistent error handling.
- Transaction safety.
- Database integrity.
- Secure defaults.
- Useful developer documentation.

Do not introduce unnecessary dependencies.

Do not create placeholder buttons or fake workflows.

Do not hardcode test users, patient records, provider identities, or production credentials into the application.

Do not make frontend-only authorization decisions.

Do not silently swallow errors from FHIR, Fabric, storage, or the database.

Do not claim an external integration is operational without evidence.

---

# 12. IMPLEMENTATION EXECUTION PLAN

Work in these stages.

### Stage A — Repository assessment

Inspect current implementation, architecture, tests, migrations, and uncommitted changes.

Produce a concise gap analysis for document exchange.

Identify reusable components and security risks.

### Stage B — Architecture and authorization design

Define:

- Document lifecycle.
- Storage abstraction.
- Ownership model.
- Consent authorization flow.
- API contract.
- FHIR mapping.
- Audit events.
- Failure handling.
- Migration requirements.

Do not begin by generating frontend screens.

### Stage C — Backend implementation

Implement the document metadata model, storage service, upload validation, ownership checks, authorization service, secure download endpoints, audit integration, and FHIR integration.

### Stage D — Frontend implementation

Extend existing patient and doctor workspaces using real backend APIs.

Ensure every visible action works.

### Stage E — Tests and security verification

Run focused tests first, then the complete regression suite.

Test authorization failures as carefully as successful workflows.

### Stage F — Documentation

Update:

- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `TESTING_REPORT.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `INTEGRATION_GUIDE.md`
- `README.md`

Document actual implementation and verification status.

---

# 13. FINAL ACCEPTANCE CRITERIA

Milestone 4 is complete only when:

1. Patients can upload and manage their own clinical documents.
2. Documents are stored outside publicly accessible frontend directories.
3. Providers can access documents only with valid patient consent.
4. Consent scope is enforced for each document request.
5. Revocation and expiry block subsequent access.
6. Provider and organization suspension block access as required.
7. Ownership and tenant-isolation tests pass.
8. Secure download endpoints are implemented.
9. Audit events are generated appropriately.
10. FHIR interoperability is implemented to the extent claimed.
11. Frontend workflows use real backend APIs.
12. Existing backend regression tests pass.
13. New focused tests pass.
14. Migration checks pass in available isolated environments.
15. Documentation reflects actual implementation.
16. No historical audit record has been modified.
17. No unrequested Git commit has been created.

If an acceptance criterion cannot be verified, label it **NOT VERIFIED**. Do not mark the milestone complete by assumption.

---

# 14. FINAL REPORT FORMAT

At completion, provide:

## Implemented
List actual backend, frontend, database, security, audit, and FHIR changes.

## API Changes
List new or modified routes and their authorization behavior.

## Security Guarantees
Explain what the backend actually enforces.

## Database Changes
List new models, migration revision, constraints, and indexes.

## Testing Results
Report exact commands and outcomes.

Separate:
- Passed
- Failed
- Skipped
- Not available
- Not verified

## Integration Status
Report actual HAPI FHIR, Keycloak, Fabric, and storage integration status.

## Files Changed
List important changed files.

## Remaining Risks
Identify prototype limitations and production-readiness gaps.

## Git Status
Confirm whether changes were committed. Do not commit without explicit authorization.

---

# FINAL INSTRUCTION

Think like an engineer building infrastructure that could eventually handle sensitive healthcare information.

Do not optimize for the number of files changed, the number of features added, or the appearance of a completed dashboard.

Optimize for correctness, privacy, interoperability, reliability, and patient control.

**Build a working, verifiable document-exchange workflow — not another healthcare CRUD application.**

Start with repository inspection and verification. Then implement this milestone incrementally, preserving all existing project work.