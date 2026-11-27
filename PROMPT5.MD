# COPILOT MASTER PROMPT — HEALTHHARBOR MILESTONE 5
## Security Hardening, Encrypted Document Storage & Reliable Healthcare Integrations

Act as the lead software architect, application security engineer, backend engineer, integration engineer, and test engineer for the existing HealthHarbor project.

Your task is to strengthen the existing implementation so that its security guarantees and external integrations are demonstrable through actual tests.

This is a continuation of the existing repository. Do not rebuild the project or replace its architecture.

# 1. PRODUCT PRINCIPLE

HealthHarbor is a consent-aware healthcare information exchange platform.

Its central purpose is to let patients securely share medical documents and records with verified doctors and healthcare organizations.

The patient must remain in control of access.

The following principles are mandatory:

- Authentication is not authorization.
- A care connection is not consent.
- An organization affiliation is not consent.
- A document identifier is not permission.
- A blockchain event is not permission.
- Frontend visibility is not authorization.
- A successful database write is not proof of successful external synchronization.

Every sensitive operation must be enforced by the backend using current application state.

# 2. CURRENT IMPLEMENTATION — PRESERVE IT

The latest implementation includes:

- Local `document_storage` adapter.
- Private storage modes.
- Storage-key validation.
- Expanded clinical document categories.
- Duplicate active-document checksum rejection.
- Audited upload rejection.
- Audited denied-download events.
- Existing ownership and consent enforcement.
- Revocation and expiry enforcement.
- Provider, affiliation, and organization authorization.
- Patient/provider Files workspace category options.

Important files include:

- `document_storage.py`
- `files.py`
- `care.py`
- Existing consent and authorization services.
- Existing FHIR integration.
- Existing Fabric gateway and chaincode.
- Existing audit and transactional-outbox implementation.

Latest reported verification:

- Focused clinical-file tests: 12 passed.
- Targeted backend regression: 60 passed, 1 PostgreSQL-only skipped.
- `test_api.py`: passed.
- `test_security.py`: passed.
- SQLite migration: passed.
- `alembic check`: no schema drift.
- Python compilation: passed.
- `git diff --check`: passed.

Outstanding verification:

- Frontend production build and browser acceptance.
- PostgreSQL migration testing.
- Live HAPI persistence.
- Live Fabric delivery.
- Application-level encryption at rest.
- Antivirus integration.

Do not assume the reported results are still true. Inspect the current repository and rerun relevant checks.

# 3. PRESERVATION RULES

Before making changes:

1. Inspect `git status --short`.
2. Review uncommitted changes.
3. Read `prompt.md` and project documentation.
4. Inspect the existing document-storage implementation.
5. Inspect file upload and download authorization.
6. Inspect existing FHIR and Fabric integrations.
7. Inspect current migration history and test infrastructure.

Never:

- Run `git reset --hard`.
- Run `git clean`.
- Discard existing changes.
- Rewrite historical migrations.
- Delete or modify historical audit records.
- Modify historical audit entry #33.
- Connect to or modify the user's existing PostgreSQL database.
- Commit without explicit permission.
- Claim a live integration works without testing it.

Use synthetic patient and clinical data only.

# 4. STAGE A — CLOSE EXISTING VERIFICATION GAPS

Before adding features, verify the existing implementation.

## Frontend

Attempt:

- Production build.
- Frontend test suite, if present.
- Browser acceptance tests, if a suitable harness is available.
- Patient document upload workflow.
- Patient document listing workflow.
- Provider authorized document access.
- Provider denied document access.
- Consent revocation workflow.

If Node/npm are unavailable, report the exact limitation.

Do not silently skip frontend verification and mark it successful.

## PostgreSQL

If a disposable PostgreSQL environment is available:

- Create an isolated temporary database.
- Run migrations from the appropriate preceding revision to the current head.
- Run `alembic check`.
- Test document-related constraints and indexes.
- Run relevant PostgreSQL-specific tests.

Never use the existing project database for experimental testing.

If PostgreSQL is unavailable, explicitly report the limitation.

## Regression

Run the complete backend suite, API smoke tests, security smoke tests, Python compilation, and `git diff --check`.

Resolve genuine regressions before continuing.

# 5. STAGE B — APPLICATION-LEVEL ENCRYPTION AT REST

Implement a secure encryption strategy for clinical documents.

## Requirements

Inspect the existing storage abstraction before making changes.

Encryption must be integrated into the storage service rather than scattered throughout API routes.

Use established cryptographic libraries and authenticated encryption.

Do not invent cryptographic algorithms.

The design must support:

- Encryption before persistent storage.
- Authenticated decryption during authorized retrieval.
- Integrity verification.
- Unique nonces or IVs as required by the selected algorithm.
- Safe key identification and key-version metadata.
- Configurable key management.
- Clear separation between application data and encryption keys.

Use envelope encryption if it fits the existing architecture.

Design the system so that production key management can later use a managed KMS.

## Key management

Never:

- Hardcode encryption keys.
- Commit secrets.
- Store encryption keys beside encrypted documents.
- Log key material.
- Return keys through API responses.
- Use a predictable fallback key.

For local development, provide a clearly documented configuration mechanism.

If the encryption key is missing or invalid, fail safely. Never silently store plaintext while claiming encryption is enabled.

## Compatibility

Inspect whether any existing documents are stored unencrypted.

Do not silently change the interpretation of existing files.

If a migration or re-encryption process is needed, design an explicit, reversible operational procedure with verification and backup requirements.

Do not automatically rewrite existing user files during application startup.

## Tests

Verify:

- Successful encryption and decryption.
- Incorrect key rejection.
- Ciphertext tampering detection.
- Unique nonce behavior.
- Missing-key failure.
- Invalid metadata handling.
- No plaintext leakage to persistent storage.
- No key leakage in logs or API responses.
- Existing authorization checks remain mandatory before decryption.

# 6. STAGE C — MALWARE-SCANNING INTEGRATION

Introduce an antivirus scanning abstraction for uploaded documents.

Do not pretend file-extension or MIME validation is antivirus scanning.

## Architecture

Create a scanner interface that supports:

- Scan request.
- Clean result.
- Malicious result.
- Unsupported result.
- Scanner unavailable.
- Timeout or operational failure.

Integrate a real scanner adapter where the environment supports it, such as ClamAV.

Do not download unknown executables or install system-wide services without authorization.

The application must behave safely if the scanner is unavailable.

## Upload lifecycle

Define an explicit document processing lifecycle.

For example:

- RECEIVED
- QUARANTINED
- SCANNING
- CLEAN
- REJECTED
- SCAN_FAILED

Inspect existing status conventions before creating enums or models.

A document must not become downloadable merely because the upload endpoint returned successfully.

Only documents that pass the configured validation and scanning policy may become available for authorized retrieval.

If scanning is unavailable:

- Keep the document unavailable.
- Record the processing state.
- Provide a clear user-facing status.
- Permit safe retry.
- Do not silently bypass scanning.

Use appropriate transaction and storage-cleanup behavior to avoid orphaned files.

## Tests

Test:

- Clean file.
- Malicious test fixture.
- Unsupported file.
- Scanner unavailable.
- Scanner timeout.
- Duplicate upload.
- Failed scan retry.
- Unauthorized download of quarantined files.
- No public access to quarantined files.

Use safe synthetic test fixtures.

# 7. STAGE D — HAPI FHIR R4 PERSISTENCE

The objective is to prove that HealthHarbor can persist and retrieve appropriate clinical-document metadata through HAPI FHIR.

Inspect the current integration first.

Use the existing HAPI FHIR R4 configuration and resource mappings.

## Requirements

Implement or complete the appropriate persistence workflow for:

- DocumentReference.
- Binary, where appropriate.
- Patient.
- Practitioner.
- PractitionerRole.
- Organization.
- Consent.
- Provenance or AuditEvent where semantically appropriate.

Do not create misleading FHIR resources.

Do not create a FHIR resource for every internal application table.

## Synchronization

Establish a clear source-of-truth policy.

For example:

- Application database: application ownership, access decisions, and workflow state.
- HAPI FHIR: interoperable clinical resource representation.

Document the exact responsibility of each system.

Implement reliable synchronization using the existing transactional outbox if appropriate.

Handle:

- HAPI unavailable.
- Network timeout.
- Authentication failure.
- Invalid FHIR response.
- Duplicate submission.
- Retry.
- Permanent integration failure.
- Reconciliation after recovery.

A failed FHIR request must not silently disappear.

Do not claim synchronization succeeded until a successful response is confirmed and the result is recorded.

Do not allow HAPI FHIR unavailability to bypass backend consent authorization.

## Verification

If a live HAPI instance is available:

- Create synthetic FHIR resources.
- Persist them.
- Retrieve them.
- Verify identifiers and references.
- Verify document metadata.
- Verify Binary behavior where implemented.
- Test failure and recovery.

If no live instance is available, use isolated integration tests and clearly label live persistence as NOT VERIFIED.

Never use real patient records.

# 8. STAGE E — HYPERLEDGER FABRIC DELIVERY RELIABILITY

Inspect existing Go chaincode, gateway, and outbox implementation.

Do not redesign the blockchain architecture without evidence of a concrete problem.

## Objective

Prove that approved application events can be delivered reliably to the Fabric network.

Potential event categories:

- Document uploaded.
- Document shared.
- Consent granted.
- Consent revoked.
- Document accessed.
- Document made unavailable.

Only use events that are genuinely implemented and relevant.

## Security requirements

Never place on-chain:

- Patient names.
- Provider names.
- Medical documents.
- Prescriptions.
- Diagnoses.
- Laboratory results.
- Raw personal identifiers.
- Access tokens.
- Encryption keys.

Use pseudonymous references and integrity hashes where appropriate.

Do not make Fabric the authorization source.

The backend's current consent and access-control state remains authoritative.

## Reliability requirements

Verify:

- Outbox event creation.
- Event delivery.
- Transaction confirmation.
- Duplicate delivery handling.
- Retry behavior.
- Failed event tracking.
- Recovery after network interruption.
- Idempotency.
- No event loss after application restart.

Do not mark an event as successfully committed before confirmation.

Do not invent transaction IDs or claim ledger persistence without evidence.

If Fabric is unavailable, preserve the event safely and report the integration as NOT VERIFIED.

# 9. STAGE F — SECURITY REVIEW

Perform a focused security review of the complete clinical-file workflow.

Inspect:

- Authentication and account mapping.
- Authorization and ownership.
- Consent scope.
- Provider verification.
- Organization status.
- Active affiliation.
- Document storage.
- Encryption and key handling.
- File upload validation.
- Malware scanning.
- Download behavior.
- Audit logging.
- FHIR synchronization.
- Fabric event delivery.
- Error handling.
- Sensitive information exposure.

Pay particular attention to:

1. IDOR and document-ID enumeration.
2. Path traversal.
3. Unauthorized downloads.
4. Stale authorization state.
5. Consent revocation races.
6. Cross-tenant access.
7. Plaintext document leakage.
8. Encryption-key leakage.
9. Unsafe temporary files.
10. Duplicate event delivery.
11. Failed synchronization.
12. Excessive audit information.

Use current backend database state for authorization.

Do not rely on frontend checks or stale JWT role claims.

Document vulnerabilities discovered and their remediation.

Do not claim a formal penetration test unless one was actually performed.

# 10. STAGE G — USER EXPERIENCE

Extend existing interfaces only where needed.

### Patient workspace

The patient should be able to understand:

- Whether an upload succeeded.
- Whether scanning is pending.
- Whether a document is clean or rejected.
- Whether a document is available.
- Who has permission to access it.
- Whether consent has expired or been revoked.

### Provider workspace

The provider should see:

- Authorized patient records only.
- Document processing status where relevant.
- Applicable consent scope.
- Clear denied-access explanations.
- Safe document retrieval errors.

Never reveal unauthorized patient information to improve the interface.

Use real API responses.

Do not introduce fake success states or placeholder functionality.

# 11. DATABASE AND MIGRATION RULES

Inspect the existing database design before adding tables or fields.

Avoid unnecessary schema changes.

If a migration is required:

- Make it additive where possible.
- Preserve existing data.
- Add appropriate constraints and indexes.
- Do not rewrite old migrations.
- Test on isolated SQLite.
- Test on disposable PostgreSQL if available.
- Run `alembic check`.

Do not run experimental migrations against the user's existing database.

# 12. IMPLEMENTATION ORDER

Work incrementally:

1. Repository inspection.
2. Existing verification gaps.
3. Security architecture review.
4. Encryption implementation.
5. Antivirus scanner abstraction and lifecycle.
6. HAPI FHIR reliability.
7. Fabric delivery reliability.
8. Frontend status improvements.
9. Full regression and security testing.
10. Documentation.

Do not attempt to implement everything in one giant code-generation operation.

Complete each stage with tests before moving forward.

If a stage depends on unavailable infrastructure, implement only what can be safely verified and report the remaining work.

# 13. DOCUMENTATION

Update the existing project documentation:

- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `TESTING_REPORT.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `INTEGRATION_GUIDE.md`
- `README.md`

Document:

- Encryption architecture.
- Key management limitations.
- Scanner configuration.
- Document lifecycle.
- FHIR synchronization strategy.
- Fabric delivery strategy.
- Retry and failure behavior.
- Test evidence.
- Remaining production limitations.

Never describe a planned integration as an implemented integration.

# 14. FINAL ACCEPTANCE CRITERIA

Milestone 5 can be considered complete only when:

1. Encryption at rest is genuinely implemented and tested.
2. Encryption keys are managed separately from document storage.
3. Plaintext is not silently persisted when encryption is required.
4. Document scanning has a real integration adapter and safe failure behavior.
5. Unscanned or rejected documents cannot be downloaded.
6. FHIR persistence and retrieval are demonstrated or explicitly marked unverified.
7. Fabric delivery and confirmation are demonstrated or explicitly marked unverified.
8. Outbox retry and idempotency behavior are tested.
9. Existing consent authorization remains intact.
10. Revocation and expiry continue to block access.
11. Existing backend regression tests pass.
12. New security tests pass.
13. Frontend verification is reported accurately.
14. Documentation reflects actual behavior.
15. Historical audit entry #33 remains untouched.
16. No unrequested commit is created.

# 15. FINAL REPORT

At completion, provide:

## Implemented
Actual changes by component.

## Encryption
Algorithm, key-management approach, storage behavior, and limitations.

## Malware Scanning
Scanner adapter, lifecycle, failure behavior, and verification.

## FHIR
Resources, persistence results, retrieval results, and synchronization status.

## Fabric
Events, delivery evidence, confirmation, retries, and failure behavior.

## Security
Authorization guarantees and security issues addressed.

## Testing
Exact commands and results, separated into:
- Passed
- Failed
- Skipped
- Not available
- Not verified

## Database
Migration changes and isolated database verification.

## Files Changed
Important files and their responsibilities.

## Remaining Risks
Honest production-readiness gaps.

## Git Status
Confirm no unrequested commit was made.

---

# FINAL ENGINEERING PRINCIPLE

HealthHarbor must not merely look secure.

It must demonstrate that unauthorized users cannot access clinical documents, that stored documents receive the protection claimed, and that external integrations handle failure without silently losing information.

Prioritize patient privacy, correctness, reliability, and verifiable evidence over feature count.

Begin with repository inspection. Preserve all existing work and implement incrementally.