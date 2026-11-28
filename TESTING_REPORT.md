# Testing report

## Milestone 8.2 frontend integration audit (2026-11-28)

- Frontend API contract review completed for Doctor, Patient/Sharing, and
  Laboratory clinical workflows.
- Corrected stale patient-side clinical-state handling: refreshed data is cleared
  first and only fulfilled API results repopulate the view.
- Corrected Doctor prescription-state duplication prevention and added explicit
  refresh/fail states for mutation actions.
- Added actual approved cross-hospital source-document listing, download, and
  import actions to the Doctor dashboard using existing backend APIs.
- Replaced laboratory report amendment browser prompts with an inline validated
  form; report amendment still uses the existing backend authorization and lifecycle.
- Static frontend diagnostics found no errors in modified React/API files.
- Node/npm and browser automation remained unavailable; no production build or
  browser workflow was claimed.


## Milestone 8.1 end-to-end clinical-workflow verification (2026-11-27)

- Complete synthetic clinical journey passed: patient, consent, doctor lab
  order, laboratory acceptance/assignment/specimen, observations, report,
  physician review, prescription, patient history, audit entries, and FHIR
  outbox entries.
- Added report-amendment coverage and prescription/report security scenarios.
- Complete relevant backend suite: **81 tests passed, 1 PostgreSQL-only audit
  concurrency test skipped**.
- `test_api.py` and `test_security.py` passed on separate disposable SQLite
  databases.
- Alembic upgrade through `e8d1a4c7b2f5_clinical_prescriptions_reviews` passed;
  `alembic check` reported no drift.
- Python compilation and `git diff --check` passed.
- Frontend static diagnostics found no errors in modified React files.
- Node/npm, browser automation, PostgreSQL, live HAPI, live Fabric, and live
  ClamAV remain unavailable and unverified.

## Milestone 8.1 frontend clinical-workflow verification (2026-11-27)

- Frontend static diagnostics: no errors found in modified Doctor, Sharing,
  Laboratory, and API client source files.
- Backend relevant suite: **81 tests passed, 1 PostgreSQL-only audit concurrency
  test skipped**.
- API smoke test passed; security smoke test passed.
- Complete SQLite migration chain and `alembic check` passed.
- The patient Sharing workspace now loads laboratory orders, reports,
  prescriptions, and clinical reviews through authenticated APIs.
- The doctor workspace now uses report selectors and disabled duplicate-submit
  states for prescription and clinical-review mutations.
- The laboratory workspace now uses an inline report-amendment form instead of
  browser prompt dialogs.
- Node/npm, browser automation, live PostgreSQL, HAPI, Fabric, and live HAPI
  remain unavailable or unverified.

## Latest Milestone 10 clinical-workflow verification (2026-11-27)

- Added two focused clinical workflow tests covering prescription lifecycle,
  cross-patient denial, consent-gated review, and resource-link validation.
- Focused clinical/integration/audit suite: **23 tests passed, 1 PostgreSQL-only
  audit test skipped**.
- Complete relevant backend suite: **79 tests passed, 1 PostgreSQL-only audit
  test skipped**.
- `test_api.py` and `test_security.py` passed on separate disposable SQLite
  databases.
- Alembic upgrade through `e8d1a4c7b2f5_clinical_prescriptions_reviews` passed
  and `alembic check` reported no drift.
- Python compilation and `git diff --check` passed.
- Frontend static diagnostics reported no errors for modified React files.
- Node/npm and browser automation remain unavailable, and live PostgreSQL,
  HAPI, Fabric, and ClamAV integrations remain unverified.


## Milestone 7.2 local concurrency and recovery validation (2026-11-27)

- Focused cross-hospital and FHIR recovery tests passed: **7 tests**.
- Complete relevant backend suite passed: **77 tests**, with one PostgreSQL-only
  audit concurrency test skipped.
- `test_api.py` and `test_security.py` passed on fresh isolated SQLite databases.
- Complete SQLite Alembic upgrade and `alembic check` passed with no schema drift.
- Python compilation and `git diff --check` passed.
- Fixed worker duplicate-processing protection and permanent-failed requeue behavior.
- Added final cross-hospital consent recheck before document retrieval/import.
- PostgreSQL, Docker, Node/npm, HAPI, Fabric, ClamAV, browser automation, and
  live infrastructure remained unavailable and are NOT VERIFIED.


## Latest Milestone 7 verification (2026-11-27)

- Two cross-hospital exchange tests passed. Coverage includes patient approval,
  Document-scope retrieval, provenance-preserving import metadata, consent
  revocation, organization impersonation denial, and cross-patient/tenant denial.
- The complete targeted backend suite passed **73 tests**, with one PostgreSQL-
  only audit concurrency test skipped.
- `test_api.py` and `test_security.py` passed separately on isolated SQLite.
- Migration `d4e8b2a1c9f7` passed through a fresh SQLite upgrade and `alembic
  check` reported no drift.
- Node/npm, disposable PostgreSQL, live HAPI, live Fabric, and browser
  acceptance remain NOT VERIFIED.


## Latest Milestone 8 validation (2026-11-27)

- Complete migration chain passed on isolated SQLite through
  `d4e8b2a1c9f7_cross_hospital_exchange`; `alembic check` reported no drift.
- Focused cross-hospital and FHIR tests passed: 7 tests. Coverage includes
  consent-gated source-document download, import provenance, revocation denial,
  wrong-provider denial, and FHIR permanent-failure handling.
- Complete targeted backend suite passed: **73 tests, 1 PostgreSQL-only audit
  concurrency test skipped**.
- `test_api.py` and `test_security.py` passed separately on fresh SQLite.
- Python compilation and `git diff --check` passed.
- PostgreSQL, Docker/Compose, Node/npm, ClamAV, HAPI, Fabric, and browser
  automation were unavailable. Live database migration, frontend build, HAPI
  operations, Fabric confirmation, and browser acceptance remain NOT RUN.

## Latest Milestone 6 verification (2026-11-27)

- Focused FHIR sync tests: **5 passed**. Coverage includes stable queue keys,
  local mirror synchronization, repeated updates, identity and PractitionerRole
  mapping, permanent HAPI errors, and reconciliation status.
- Complete targeted backend suite: **71 passed, 1 PostgreSQL-only test skipped**.
- `test_api.py` and `test_security.py` passed as separate smoke scripts.
- Fresh SQLite migration through `c7f3a9d1e4b2_fhir_sync_outbox` passed and
  `alembic check` reported no drift.
- Live HAPI persistence/retrieval, disposable PostgreSQL migration, Node/npm
  build, browser acceptance, and live Fabric confirmation remain NOT VERIFIED.


## Latest Milestone 5 verification (2026-11-27)

- AES-GCM encryption tests: 5 passed. Coverage includes round trips, unique
  ciphertexts, missing/wrong keys, tampering detection, legacy plaintext
  handling, and scanner availability fail-closed behavior.
- Combined backend security/regression suite: **66 tests passed, 1
  PostgreSQL-only test skipped**.
- `test_api.py` and `test_security.py` passed as separate smoke scripts.
- Milestone 5 migration `a31e7c9d2f10` passed on fresh SQLite and `alembic
  check` reported no schema drift. SQLite required batch-alter mode and was
  corrected after the first migration attempt.
- PostgreSQL, Node/npm, browser acceptance, live HAPI, live Fabric, and ClamAV
  end-to-end delivery remain NOT TESTED or NOT VERIFIED.

## Latest Milestone 4 verification (2026-11-27)

- The focused `test_files` suite passed **12 tests**, including duplicate
  detection, category rejection, denied-download auditing, consent revocation,
  expiry, organization membership, bounded listings, FHIR DocumentReference
  metadata, and lab/technician isolation.
- The targeted regression suite passed **60 tests**, with one PostgreSQL-only
  audit concurrency test skipped.
- `test_api.py` and `test_security.py` passed separately on fresh isolated
  SQLite databases.
- Alembic upgrade through `f4c1a6d2e9b7` and `alembic check` passed on a fresh
  SQLite database. No migration or write was made to the existing PostgreSQL
  database.
- PostgreSQL tooling and Docker were unavailable, so disposable PostgreSQL
  migration verification remains NOT TESTED. Node/npm and a browser harness
  were unavailable, so the updated frontend build and browser acceptance remain
  NOT VERIFIED.


## Latest Milestone 3 verification (2026-11-27)

- `test_care_requests.py`: 4 Milestone 3 tests passed. Coverage includes
  patient initiation, provider response, cross-provider/patient denial,
  affiliation restrictions, approval-created consent, rejection without
  consent, and suspended-provider blocking.
- All unittest-style backend modules ran together on a fresh SQLite database:
  **58 tests passed, 1 PostgreSQL-only test skipped**.
- `test_api.py` passed as a separate API smoke script on a fresh SQLite
  database.
- `test_security.py` passed as a separate adversarial smoke script on a fresh
  SQLite database.
- Alembic upgrade through `f4c1a6d2e9b7` passed on isolated SQLite and
  `alembic check` reported no schema drift.
- Frontend production build, browser acceptance, and disposable PostgreSQL
  migration testing were blocked because Node/npm and PostgreSQL/Docker tools
  were unavailable in this shell. No live service was contacted.

## Latest Milestone 2 verification (2026-11-26)

This update supersedes earlier test-count summaries for the current worktree.

- `python -m unittest discover -v` passed **57 tests**, with one PostgreSQL-
  only test skipped. It ran with `AUTH_PROVIDER=local`, `FHIR_MODE=local`,
  `FABRIC_ENABLED=false`, and a fresh migrated SQLite database at
  `/tmp/hh-milestone2-full-final.db`.
- `test_api.py` and `test_security.py` each passed as separate smoke runs
  against their own migrated disposable SQLite databases.
- The seven registry API tests passed, including authorization denials,
  organization resubmission, provider-candidate scoping, evidence privacy,
  suspension, and multi-organization affiliation behavior.
- `alembic upgrade head` and `alembic check` passed on a fresh isolated
  SQLite database through `2a7f9c6d4e81_healthcare_registry`.
- The existing project PostgreSQL database was not connected to or modified.
  The registry migration was not run on PostgreSQL in this pass.
- `npm run build` was attempted but could not start because this environment
  has neither Node.js nor npm installed. Earlier build evidence predates the
  new Registry workspace and does not validate it. No frontend browser
  acceptance was performed.
- Earlier disposable PostgreSQL audit concurrency tests still provide
  evidence for the READ COMMITTED audit fix; they were not rerun here.

## Verification environment and safety

- Backend tests ran under Python 3.13.15 in a temporary virtual environment.
- Frontend dependencies were installed from the existing lockfile with
  temporary Node.js 22.20.0/npm; no package manifest or lockfile changes were
  made. Vite 6.4.6 produced a successful production build.
- Go 1.23.12 was installed under a temporary path. PostgreSQL 16.11 was
  source-built and run as a disposable loopback-only cluster.
- The existing project PostgreSQL database was not accessed for migrations or
  writes. PostgreSQL tests used only databases named `audit_test_*`; SQLite
  tests used separate temporary files and synthetic accounts.
- Initial Go/PostgreSQL compilation attempts exhausted the constrained `/tmp`
  filesystem. Re-running with temporary build directories on the home
  filesystem succeeded. No repository source changes were needed for this.

## Backend test results

From `backend/`, the focused suite ran:

```sh
DATABASE_URL=sqlite:////tmp/hh-prompt-final-unit-suite.db \
DB_AUTO_CREATE=1 \
python -m unittest test_security_hardening test_files \
  test_organization_consent test_integrations test_audit_logger \
  test_loadtest -v
```

**Result: 50 tests passed, 1 PostgreSQL-only test skipped.** The skip was
intentional because this command used SQLite; the PostgreSQL test was then run
explicitly against disposable databases. Coverage includes seed safeguards,
shared login rate limiting, consent and membership authorization, protected
files, generic FHIR errors, token validation, the hash chain, and load-runner
target validation.

The isolated API workflow passed:

```sh
DATABASE_URL=sqlite:////tmp/hh-prompt-final-api.db DB_AUTO_CREATE=1 \
AUTH_PROVIDER=local FHIR_MODE=local FABRIC_ENABLED=false \
python test_api.py
```

It covered registration, consent, ServiceRequest idempotency, laboratory and
technician transitions, reports, revocation, and audit tamper detection.

The isolated security workflow passed:

```sh
DATABASE_URL=sqlite:////tmp/hh-prompt-final-security.db DB_AUTO_CREATE=1 \
AUTH_PROVIDER=local FHIR_MODE=local FABRIC_ENABLED=false \
python test_security.py
```

It covered missing, malformed, expired, and tampered tokens; role-denied
operations; unsafe input; security headers; and account lockout.

## Migration and PostgreSQL audit concurrency

The full Alembic chain and schema comparison passed on a fresh SQLite database:

```sh
DATABASE_URL=sqlite:////tmp/hh-prompt-final-migration.db DB_AUTO_CREATE=0 \
alembic upgrade head
DATABASE_URL=sqlite:////tmp/hh-prompt-final-migration.db DB_AUTO_CREATE=0 \
alembic check
```

On the disposable PostgreSQL 16.11 cluster, `alembic upgrade head` ran through
`8c41d6a2f705` and `alembic check` reported **No new upgrade operations
detected**:

```sh
DATABASE_URL=postgresql://postgres@127.0.0.1:55439/audit_test_prompt \
alembic upgrade head
DATABASE_URL=postgresql://postgres@127.0.0.1:55439/audit_test_prompt \
alembic check
```

The server's `default_transaction_isolation` was `repeatable read`.
The guarded test passed through the application engine/session configuration:

```sh
AUDIT_TEST_POSTGRES=1 \
AUDIT_TEST_SERVER_DEFAULT='repeatable read' \
DATABASE_URL=postgresql://postgres@127.0.0.1:55439/audit_test_concurrency \
python -m unittest \
  test_audit_logger.AuditLoggerConcurrencyTests.test_postgresql_repeatable_read_server_default_serializes_appends \
  -v
```

The same test passed on a separate disposable database with its effective
default set to `read committed`, using
`AUDIT_TEST_SERVER_DEFAULT='read committed'` and
`DATABASE_URL=postgresql://postgres@127.0.0.1:55439/audit_test_readcommitted`.
Both runs used independent writer processes and sessions. They verified that
the application transaction uses `READ COMMITTED` after an earlier query,
advisory-lock serialization, sequential predecessor links, recomputed hashes,
appending after a synthetic discontinuity without changing it, and rollback
with no partial insert after a forced failure.

This verifies the implementation on isolated synthetic PostgreSQL data only;
it does not validate or repair the existing project database. Its known
historical discontinuity at entry #33 remains untouched.

## Frontend and Fabric module results

```sh
cd frontend
npm ci
npm run build
```

`npm ci` completed from the lockfile with zero reported vulnerabilities.
`npm run build` passed: Vite 6.4.6 transformed 42 modules and emitted the
production bundle.

From the project root, both Fabric modules passed tests and vet:

```sh
(cd fabric/chaincode && go test ./... && go vet ./...)
(cd fabric/adapter && go test ./... && go vet ./...)
```

These are module tests only; they do not prove a live Fabric deployment or a
committed ledger transaction.

## Read-only service probes and unverified behavior

- Backend `GET /health`: HTTP 200, status healthy, database connected, FHIR
  mode `hapi`.
- HAPI `GET /fhir/metadata`: HTTP 200, `CapabilityStatement`, FHIR R4 `4.0.1`.
- Keycloak OIDC discovery timed out.
- No HAPI clinical resource writes, live Keycloak browser flow, Fabric
  transaction, browser acceptance run, ZAP scan, k6 workload, backup, or
  restore was performed.
- Docker Compose tooling was unavailable, so no containers or project volumes
  were started, stopped, or changed.
- Test logs included Python 3.13 `datetime.utcnow()` deprecation warnings;
  they did not fail the test runs.
- `git diff --check` passed. No changes were committed.
