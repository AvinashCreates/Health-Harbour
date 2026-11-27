# HealthHarbor — Milestone 7.2: Local Concurrency, Recovery & Security Validation

You are working on my existing final-year project, **HealthHarbor**, located at:

`/home/pamarthi-avinash/Downloads/healthcare-exchange`

Your task is to strengthen the reliability, concurrency safety, and security of the existing cross-hospital healthcare exchange and FHIR synchronization implementation.

## Important environment constraints

- I currently have limited mobile data.
- Do NOT download Docker images or install Docker.
- Do NOT download or install HAPI FHIR, Hyperledger Fabric, PostgreSQL, or other large infrastructure.
- Use the existing Python environment, SQLite, and locally available dependencies.
- Use mocks and controlled test doubles for external services.
- Do not claim that mocked integration tests prove live integration works.

## Critical preservation rules

1. Inspect the current Git status and existing implementation before changing anything.
2. Preserve all existing uncommitted work.
3. Never run `git reset --hard` or `git clean`.
4. Never commit changes unless I explicitly authorize it.
5. Do not use my existing PostgreSQL database for experimental migrations.
6. Historical audit entry #33 must remain completely untouched.
7. Never rewrite, delete, repair, or re-hash historical audit records.
8. Never store clinical document contents or sensitive patient information on the blockchain.
9. Use synthetic test data only.

## Task 1 — Consent revocation and concurrent access

Review the cross-hospital document retrieval and consent authorization implementation.

Test these situations:

- A document retrieval request begins while consent is valid.
- Consent is revoked before the retrieval authorization decision completes.
- Two requests attempt to access a document while consent is being revoked.
- Consent expires during an exchange request.
- A provider attempts access after their organization affiliation becomes inactive.
- A provider attempts to access a document outside the granted resource scope.

Determine whether the existing transaction boundaries and authorization checks prevent unauthorized access.

Implement appropriate fixes where necessary.

Do not introduce a claim that every possible concurrency race is solved merely because SQLite tests pass.

## Task 2 — FHIR outbox idempotency

Review `FHIRSyncOutbox` and its worker.

Test:

- The same outbox event is processed more than once.
- Two worker executions encounter the same pending event.
- The worker crashes after an external operation but before marking the event complete.
- A previously failed event is retried.
- A permanently failed event is not retried indefinitely.
- Duplicate FHIR resources are not created unnecessarily.

Implement safe idempotency and duplicate-processing protection.

Use stable event identifiers and appropriate database constraints or transaction handling where justified by the existing architecture.

Do not silently discard failed events.

## Task 3 — Worker recovery

Verify:

- The worker starts correctly through the application lifespan.
- A worker restart does not lose pending events.
- Interrupted events can be recovered.
- Retry counts and error information remain traceable.
- A failed event does not prevent unrelated events from being processed.
- Shutdown does not corrupt pending event state.

Add tests for these scenarios using lightweight test doubles.

## Task 4 — Audit integrity

Review audit logging around:

- Consent approval.
- Consent rejection.
- Consent revocation.
- Cross-hospital document access.
- Document import.
- FHIR synchronization success and failure.

Ensure that security-relevant events remain traceable.

Do not modify historical audit records, especially entry #33.

Do not expose sensitive clinical data in logs or audit metadata.

## Task 5 — Test coverage

Add focused backend tests for the above cases.

Use the project's existing testing conventions.

Prefer deterministic tests over timing-dependent tests. Use synchronization primitives or controlled test doubles where appropriate.

Run:

- Focused new tests.
- Existing targeted backend test suite.
- API/security smoke tests.
- Python compilation.
- SQLite migration chain.
- `alembic check`.
- `git diff --check`.

Inspect the frontend only if backend API behavior changes require corresponding updates.

## Task 6 — Final report

Provide a detailed report containing:

1. Files inspected.
2. Files changed.
3. Security and reliability issues discovered.
4. Fixes implemented.
5. New tests added.
6. Exact test results and counts.
7. SQLite migration status.
8. Git status and confirmation that no commit was created.
9. Confirmation that audit entry #33 remains untouched.
10. Known limitations and unverified integrations.

Clearly distinguish:

- Implemented.
- Locally tested.
- Tested with mocked services.
- Verified against real infrastructure.
- Not verified.

Do not claim live PostgreSQL, HAPI FHIR, or Hyperledger Fabric integration has been verified.

## Completion criteria

The milestone can be marked locally validated only when the relevant tests pass and the implementation has been reviewed.

If a requirement cannot be safely verified in the current environment, document it instead of pretending it passed.

**Start by inspecting the existing code and Git status. Work incrementally, preserve existing functionality, and do not commit.**