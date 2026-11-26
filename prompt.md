# ROLE: Senior Full-Stack Engineer, Healthcare Interoperability Architect, DevSecOps Engineer

You are responsible for completing my existing final-year project, **HealthHarbor**, into a fully integrated, demonstrable healthcare interoperability platform.

Work directly inside the existing repository using GitHub Copilot Agent mode in VS Code.

You must inspect the existing source code, understand the architecture, identify incomplete implementations, and finish the project systematically.

Do NOT rebuild the project from scratch.
Do NOT replace working modules with generic implementations.
Do NOT remove existing features.
Do NOT introduce unnecessary technologies or architectural complexity.

---

# 1. PROJECT OBJECTIVE

HealthHarbor is a secure, consent-aware healthcare data exchange platform connecting:

- Patients
- Physicians
- Healthcare organizations
- Laboratory supervisors
- Laboratory technicians
- Administrators

The system uses HL7 FHIR R4 for healthcare interoperability, Keycloak for identity management, PostgreSQL for persistence, and Hyperledger Fabric for selected audit and provenance events.

Its primary objective is to let patients control access to their healthcare records while supporting secure collaboration between healthcare professionals and organizations.

Use synthetic patient and clinical data exclusively.

# 2. EXISTING TECHNOLOGY STACK

Preserve the current technology stack:

Frontend:
- React
- Existing Vite setup
- Existing CSS and UI components

Backend:
- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

Authentication:
- Keycloak
- OpenID Connect
- OAuth 2.0 Authorization Code Flow with PKCE
- JWT validation

Healthcare interoperability:
- HAPI FHIR R4
- HL7 FHIR resources

Blockchain:
- Hyperledger Fabric
- Go chaincode
- Existing HTTP Gateway adapter
- Transactional outbox

Infrastructure:
- Docker
- Docker Compose
- Existing environment configuration

Testing:
- Python unittest
- Existing frontend build scripts
- OWASP ZAP
- k6

Do not change the technology stack without a demonstrated technical necessity.

# 3. IMPORTANT EXISTING IMPLEMENTATION

Before making changes, inspect:

- PROJECT_STATUS.md
- README.md
- Backend source
- Frontend source
- Database models
- Alembic migrations
- API routes
- Authentication services
- Consent authorization services
- FHIR integration
- Fabric chaincode and adapter
- Docker Compose files
- Keycloak realm configuration
- Existing tests
- Security scripts

The project already has substantial implementation.

Existing features include:

1. Role-based authentication.
2. Patient-only local registration.
3. Administrator-provisioned staff.
4. Patient consent management.
5. Resource-specific consent.
6. Consent expiry and immediate revocation.
7. Physician-specific and organization-based consent.
8. Administrator-managed organization memberships.
9. Named-practitioner organization access.
10. Treatment-only organization grants.
11. Laboratory workflow.
12. Clinical file management.
13. Off-chain clinical document storage.
14. Local audit hash-chain verification.
15. HAPI FHIR integration.
16. Keycloak integration.
17. Hyperledger Fabric chaincode and adapter.
18. PostgreSQL and Alembic migrations.
19. OWASP ZAP runner.
20. k6 load-testing runner.

Treat these as existing capabilities to verify and complete, not as reasons to recreate them.

# 4. TEMPORARILY DEFERRED ISSUE

The historical audit-chain integrity mismatch beginning at entry #33 is explicitly OUT OF SCOPE for this implementation pass.

Do not:

- Modify historical audit records.
- Rewrite historical hashes.
- Reset the audit database.
- Delete audit entries.
- Attempt to conceal historical verification failures.
- Spend implementation time investigating the #33 mismatch.

Preserve all existing audit records and existing verification behavior.

You may continue implementing and testing future audit writes, audit concurrency protections, and new-event integrity without attempting to repair historical records.

Record this deferred issue in the project documentation as:

"Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged."

# 5. IMPLEMENTATION PHASES

Complete the following phases in order.

## PHASE 0 — Repository inspection and planning

First:

1. Inspect the repository structure.
2. Read the implementation status document.
3. Inspect the actual implementation of every integration.
4. Check Git status and existing uncommitted changes.
5. Identify the active branch.
6. Identify missing dependencies and environment requirements.
7. Identify incomplete functions, placeholder implementations, mocked integrations, and TODOs.
8. Identify existing tests and their coverage.

Do not overwrite existing work.

Create or update:

- IMPLEMENTATION_STATUS.md
- ARCHITECTURE_REVIEW.md
- COMPLETION_ROADMAP.md

These documents must reflect actual code, not assumptions.

Proceed with implementation after completing the inspection. Do not stop after merely producing a report.

## PHASE 1 — Application stability

Ensure the existing application starts reliably.

Verify:

- PostgreSQL starts and becomes healthy.
- Backend connects to PostgreSQL.
- HAPI FHIR starts and exposes R4 metadata.
- Backend health checks accurately report dependency readiness.
- Frontend connects to the backend through the correct IPv4 API address.
- CORS configuration is correct.
- Login works from the browser.
- All existing role workspaces load.
- API timeout and error handling work.
- Docker Compose profiles and service dependencies are correct.

The current development setup has a separate Vite process. Document how to start it.

Do not change working Docker networking configuration without identifying a concrete problem.

## PHASE 2 — Database and migration completion

Verify all existing Alembic migrations.

Pay particular attention to the latest organization-consent migration:

`71b6c4a2d9e1`

Tasks:

1. Inspect the migration and corresponding models.
2. Check migration ordering and dependencies.
3. Test migration on a fresh SQLite database.
4. Test migration against a backed-up PostgreSQL database.
5. Verify organization and practitioner membership persistence.
6. Verify consent persistence and expiration.
7. Verify existing records remain compatible.
8. Verify application startup does not silently create production tables.
9. Verify rollback behavior where safe and supported.

Never delete or reset the existing PostgreSQL database.

Before applying migrations to existing data, require a verified backup.

## PHASE 3 — Complete live Keycloak authentication

Use the existing Keycloak realm and client configuration.

Complete and verify:

1. Realm import.
2. Browser login using Authorization Code + PKCE.
3. JWT signature validation.
4. Issuer validation.
5. Audience validation.
6. Expiration validation.
7. Subject validation.
8. Application-role mapping.
9. Patient registration and verified-email provisioning.
10. Administrator-provisioned staff accounts.
11. User-to-application-profile linking.
12. Token refresh.
13. Logout.
14. Expired-token behavior.
15. Unauthorized-role rejection.
16. Disabled-user behavior.

Verify that frontend and backend authentication modes are consistent.

Do not bypass token validation to make login succeed.

Do not introduce default production credentials or hardcoded secrets.

## PHASE 4 — Complete HAPI FHIR R4 interoperability

HAPI FHIR 7.4.0 is already configured for R4 and has successfully started against PostgreSQL.

Now prove real interoperability.

Inspect the existing FHIR adapter and application service layer.

Verify the implemented resources, including:

- Patient
- Practitioner
- Organization
- ServiceRequest
- Specimen
- Observation
- DiagnosticReport
- Consent
- DocumentReference

For each supported resource:

1. Create a synthetic resource.
2. Validate it using HAPI `$validate` where supported.
3. Persist it through the actual HAPI server.
4. Retrieve it from HAPI.
5. Update it using version-aware operations.
6. Verify references.
7. Verify application-level authorization.
8. Verify error handling for invalid resources.
9. Verify persistence after service restart.

Do not simulate HAPI responses in tests presented as live integration tests.

Use authoritative HAPI reads wherever the architecture requires them.

Verify that the API does not falsely report success when HAPI is unavailable.

## PHASE 5 — Complete patient consent and authorization

This is a core project feature.

Verify all existing consent scenarios against live PostgreSQL and HAPI.

Patient consent must support:

- A specific physician.
- An organization and named physician.
- Resource-specific permissions.
- Defined validity of 1–30 days.
- Automatic server-side expiry.
- Immediate revocation.
- Treatment-only purpose for organization grants.
- Active organization membership.
- Patient access history.

Verify authorization at the backend for:

- Patient resource reads.
- Clinical file downloads.
- DocumentReference access.
- ServiceRequest creation.
- Observation and DiagnosticReport access where implemented.
- Physician access.
- Organization-based access.
- Laboratory workflows.

Test the following denial scenarios:

- Expired consent.
- Revoked consent.
- Removed organization membership.
- Wrong physician.
- Wrong patient.
- Wrong resource type.
- Wrong purpose.
- Unauthorized role.
- Unassigned technician.
- Unowned laboratory request.

Do not rely on frontend restrictions alone.

Verify that a revoked consent immediately blocks subsequent requests.

Ensure organization consent never unintentionally grants access to every organization member.

## PHASE 6 — Complete Hyperledger Fabric integration

Inspect the existing Go chaincode, Gateway adapter, and transactional outbox.

Do not replace the current implementation.

Complete the actual deployment and integration.

Tasks:

1. Verify both Go modules.
2. Build the adapter image.
3. Start the existing two-organization Fabric test network.
4. Configure peer endorsement according to the existing deployment guidance.
5. Deploy the chaincode.
6. Configure Gateway connectivity.
7. Verify identity and certificate handling.
8. Submit a synthetic audit/provenance event from the backend.
9. Verify the event is committed on the ledger.
10. Capture and verify its transaction ID.
11. Verify outbox retry behavior.
12. Verify duplicate submission handling.
13. Verify rejected event types.
14. Verify failure recovery after Gateway unavailability.
15. Verify commit status is only recorded after confirmed ledger commitment.

Only approved metadata, pseudonymous references, and permitted hashes should be submitted.

Never submit patient names, clinical documents, medical records, or unnecessary personal information to Fabric.

Do not mark a transaction committed merely because the Gateway accepted an HTTP request.

## PHASE 7 — Complete laboratory workflow

Verify the complete workflow:

REQUESTED
→ ACCEPTED
→ ASSIGNED
→ SPECIMEN_REGISTERED
→ PROCESSING
→ RESULTS_SUBMITTED
→ FINALIZED
→ PHYSICIAN_REVIEWED

Verify:

- Physician creates a ServiceRequest.
- Correct laboratory receives the request.
- Laboratory supervisor accepts it.
- Supervisor assigns a technician.
- Technician registers the specimen.
- Technician submits observations and results.
- Laboratory finalizes the report.
- Physician reviews the result.

Enforce ownership, membership, assignment, authorization, and transition ordering.

Verify the appropriate FHIR resources are persisted in HAPI.

Prevent invalid transitions and duplicate requests.

Use synthetic clinical data.

## PHASE 8 — Clinical file security

Review file upload and download functionality.

Existing restrictions include:

- PDF
- JPEG
- PNG
- TXT
- CSV
- Maximum 10 MiB

Verify:

1. Server-side file validation.
2. MIME-type validation.
3. Safe filename handling.
4. Path traversal protection.
5. File size enforcement.
6. Authenticated downloads.
7. Patient ownership checks.
8. Physician Document consent checks.
9. Laboratory assignment restrictions.
10. DocumentReference creation and persistence.
11. File hashing.
12. Storage persistence after container restart.

Add malware scanning only if a practical, maintainable integration can be implemented in the existing environment.

Do not store clinical files on the blockchain.

## PHASE 9 — Security verification

Complete a security review of the existing application.

Review:

- Authentication and session management.
- Authorization and privilege escalation.
- IDOR.
- SQL injection.
- XSS.
- CSRF where applicable.
- CORS.
- File upload vulnerabilities.
- JWT validation.
- Secret management.
- Rate limiting.
- Error disclosure.
- Logging of sensitive information.
- Organization membership authorization.
- Consent enforcement.

Run the existing OWASP ZAP passive baseline against the local application.

Use the existing loopback-only safety restrictions.

Do not target external systems.

Produce:

`SECURITY_ASSESSMENT.md`

Include findings, severity, evidence, remediation, and unresolved risks.

Do not claim that a vulnerability is fixed without testing it.

## PHASE 10 — Performance and reliability

Run the existing k6 load-test suite against the actual local application.

Measure:

- Health endpoint response.
- Authentication.
- Authenticated profile requests.
- Patient resource reads.
- File listing.
- Consent checks.
- ServiceRequest listing.

Use synthetic accounts and data.

Capture:

- Request count.
- Throughput.
- Average latency.
- p95 latency.
- p99 latency where available.
- Error rate.
- Failed requests.

Do not fabricate performance numbers.

Do not label a runner smoke test as a performance benchmark.

Investigate bottlenecks only after obtaining actual results.

Replace process-local login rate limiting with a shared store before claiming horizontal API scalability.

## PHASE 11 — Backup and recovery

Create and verify a PostgreSQL backup and restore procedure.

Requirements:

1. Document backup commands.
2. Preserve database ownership and permissions.
3. Verify backup integrity.
4. Restore into an isolated test database.
5. Verify schema and essential records.
6. Verify application connectivity after restoration.
7. Document recovery steps.
8. Document file-storage backup and restoration.

Never test recovery by overwriting the live database.

Do not remove Docker volumes.

## PHASE 12 — Frontend completion

Inspect every role workspace.

Verify:

Patient:
- Dashboard.
- Clinical files.
- Consent management.
- Sharing with physicians and organizations.
- Access history.
- Revocation.

Physician:
- Patient access requests.
- Consent-aware patient records.
- Clinical document viewing.
- ServiceRequest creation.
- Laboratory results review.

Laboratory supervisor:
- Incoming requests.
- Acceptance.
- Technician assignment.
- Workflow monitoring.

Laboratory technician:
- Assigned requests.
- Specimen registration.
- Processing.
- Result submission.

Administrator:
- User provisioning.
- Organization management.
- Physician membership management.
- Audit tools.

Improve loading states, error states, empty states, responsive layout, and form validation.

Preserve the existing visual identity and design direction.

Do not redesign the entire application unnecessarily.

Run the production build and resolve actual errors.

# 6. ENGINEERING RULES

Follow these rules throughout the work:

1. Inspect before modifying.
2. Preserve working code.
3. Do not remove existing features.
4. Do not invent successful integrations.
5. Do not replace live integration tests with mocks and claim completion.
6. Keep clinical data off-chain.
7. Use synthetic data exclusively.
8. Never hardcode secrets.
9. Do not reset databases.
10. Do not delete Docker volumes.
11. Do not stop unknown processes.
12. Do not disable authentication or authorization to bypass errors.
13. Do not silently suppress failing tests.
14. Do not claim production readiness prematurely.
15. Keep code modular and maintainable.
16. Add regression tests for every bug fixed.
17. Keep documentation synchronized with actual implementation.
18. Preserve historical audit records and defer the #33 investigation.

Before changing files:

- Inspect `git status`.
- Identify existing uncommitted changes.
- Do not overwrite user modifications.
- Create a checkpoint commit only with my approval.

For database changes, require a verified backup before applying them to existing PostgreSQL data.

# 7. EXECUTION STRATEGY

Work in small, independently verifiable stages.

For every phase:

1. Explain the identified gap.
2. Identify the relevant files.
3. Implement the necessary changes.
4. Run focused tests.
5. Run relevant regression tests.
6. Run the integration test where applicable.
7. Report actual command output and results.
8. Update implementation documentation.
9. Identify remaining limitations.

Do not attempt to modify the entire project in one giant operation.

If a service is unavailable, diagnose the actual cause. Do not silently substitute a mock.

If a step requires my credentials, approval, or manual environment setup, stop at that step and give me precise instructions.

Do not proceed with destructive operations without explicit approval.

Continue to the next independent phase whenever the previous phase has been successfully verified.

# 8. FINAL ACCEPTANCE CRITERIA

The project should only be considered functionally complete when the following can be demonstrated:

- All application services start reliably.
- All role workspaces function.
- Keycloak login and refresh work.
- PostgreSQL persists application data.
- HAPI FHIR R4 performs actual resource CRUD.
- Consent is enforced server-side.
- Consent expiry and revocation work.
- Named-practitioner organization authorization works.
- Clinical files remain off-chain.
- The full laboratory workflow works.
- Fabric receives and commits permitted events.
- Committed transaction IDs can be verified.
- New audit events preserve chain integrity.
- Historical audit mismatch #33 remains documented as deferred, with no historical records altered.
- Existing and newly added tests pass.
- Frontend production build passes.
- OWASP ZAP assessment is completed.
- Actual k6 results are recorded.
- PostgreSQL backup and isolated restore are verified.
- Documentation accurately describes the working system.

# 9. REQUIRED FINAL DOCUMENTATION

Maintain these files:

- README.md
- PROJECT_STATUS.md
- IMPLEMENTATION_STATUS.md
- ARCHITECTURE_REVIEW.md
- COMPLETION_ROADMAP.md
- SECURITY_ASSESSMENT.md
- DEPLOYMENT_GUIDE.md
- TESTING_REPORT.md

Document exact commands, environment variables, service startup order, test results, and limitations.

Clearly distinguish:

- Implemented.
- Unit tested.
- Integration tested with mocks.
- Verified against a real local service.
- Not yet verified.
- Deferred.

# 10. START NOW

Begin with PHASE 0.

Inspect the actual repository and compare the source code against PROJECT_STATUS.md.

Then create/update the implementation documents and proceed with the highest-priority unfinished work.

Do not stop after writing a plan.

Your objective is to finish and verify the existing HealthHarbor system, not merely produce code that looks complete.

At every stage, prioritize correctness, security, interoperability, maintainability, and demonstrable results.