# HealthHarbor implementation status

This status distinguishes code implemented and locally tested from external
services that still require a real deployment. Mock tests do not establish
production interoperability.

## Application features

### Backend

- FastAPI role-gated authentication, bcrypt local passwords, expiring JWTs,
  login rate limiting, CORS allowlisting, and baseline security headers.
- Local tokens require expiration and a non-empty subject. Production startup
  requires a configured, non-placeholder `JWT_SECRET` of at least 32
  characters. OIDC validation requires RS256 signature, issuer, audience,
  expiry, and subject; ambiguous application-role claims are denied.
- Patient-only public registration in local mode; admin-provisioned staff.
- Consent is resource-scoped, lasts 1–30 days, expires server-side, and can be
  revoked immediately. Access history is available to the patient.
- Explicit lab workflow:
  `REQUESTED → ACCEPTED → ASSIGNED → SPECIMEN_REGISTERED → PROCESSING →
  RESULTS_SUBMITTED → FINALIZED → PHYSICIAN_REVIEWED`.
- Server checks lab ownership, technician membership and assignment, physician
  ownership, resource scope, and transition order.
- Idempotency keys protect ServiceRequest creation from duplicate retries.
- Local audit entries are hash-chained and tampering can be detected.
- Clinical files are stored off-chain and downloaded through authenticated
  endpoints. Patients can manage their own files; physicians need active
  `Document` consent; laboratory users are limited to assigned workflows.
  Uploads are limited to PDF, JPEG, PNG, TXT, and CSV files up to 10 MiB.

### Frontend

- Role workspaces for patient, physician, laboratory/supervisor, technician,
  and administrator.
- Separate Overview, Files, Sharing & access, workflow, and Admin tools
  sections avoid placing every action on one screen. File recipient selectors
  use active consent and assigned workflows instead of free-form internal IDs.
- Patient consent management and access history; physician request/review
  workflow; lab/technician staged processing; administrator provisioning and
  audit tooling.
- Responsive cream/white design, simple typography, and reduced-motion-aware
  transitions.
- Local mode uses `sessionStorage`. Keycloak mode uses the Keycloak JS adapter
  with Authorization Code + PKCE, access-token refresh, and sign-out.

## Infrastructure integrations

| Requirement | Implementation | Verification status |
|---|---|---|
| Keycloak / OIDC | Realm export, PKCE browser client, RS256/JWKS signature validation, issuer/audience/expiry/subject checks, unambiguous role mapping, verified-email patient provisioning, and subject-based profile linking. | Signed-token tests pass, including missing audience and ambiguous-role rejection. Live Keycloak import, sign-in, refresh, and user provisioning remain unverified. |
| HAPI FHIR R4 | Create/update/read paths use reference checks, `$validate`, conditional version updates, and authoritative HAPI reads. Compose sets the PostgreSQL Hibernate dialect directly with Spring application properties and disables contextual JDBC LOB creation. | Verified on the user's machine (2026-11-25): HAPI 7.4.0 completed startup, the `bt2_job_instance`, `trm_concept`, and `hfj_search` tables exist in PostgreSQL, metadata reports FHIR R4 `4.0.1`, and API health reports `fhir: hapi`. Live resource create/read/update and full workflow round trips remain unverified. |
| Hyperledger Fabric | Go chaincode and HTTP Gateway adapter, explicit allowlisted append-only event types, transactional outbox with retry/backoff, keyed pseudonym references, payload hashes, and commit status only after Gateway confirmation. Deployment guidance describes a two-organization local test network with both peer organizations endorsing writes. | Python outbox tests pass, including rejection of unapproved event types and checks on the outbound field projection. Go tests could not run in this environment because Go is unavailable. User ran `go test ./...` successfully in both modules on 2026-11-25. A live Fabric network deployment and committed ledger event remain unverified. |
| PostgreSQL / migrations | Alembic schema migrations and Compose startup upgrade; API `create_all` is disabled for PostgreSQL. Compose also mounts a persistent volume for clinical file bytes. | User-provided Compose output (2026-11-25) showed PostgreSQL healthy, backend running, and API health confirming database connectivity. Backup/restore and failure-recovery procedures remain untested. |
| OWASP ZAP | Passive baseline scan runner restricted to loopback targets. | Runner syntax and non-loopback refusal checked; Docker and a live local API were unavailable, so no scan was run. |
| k6 load testing | Current-stack ramping test with optional authenticated reads and JSON summary export, restricted to loopback targets. | Runner syntax and non-loopback refusal checked; Docker/k6 and a live API were unavailable, so no load results were produced. |

## Verification record (2026-11-25)

- `backend/test_api.py` passed using an isolated SQLite database.
- `backend/test_security.py` passed using a separate isolated SQLite database.
- `python -m unittest test_integrations test_files test_audit_logger -v`
  passed all 16 tests; external-service behavior in integration tests is
  mocked.
- `security/current-stack.js` passed Node syntax validation; both security
  runner shell scripts passed `sh -n`.
- Fresh SQLite Alembic upgrade and `alembic check` passed.
- The Python load-test runner completed a smoke test against an isolated API
  using 3 requests per phase and a synthetic authenticated account. This only
  validates the runner, not performance or scalability.
- Frontend production build passed.
- Python requirements were installed only in a temporary environment for
  these tests; no project dependency manifests were changed.

## Authentication hardening evidence (2026-11-26)

- Added required `exp` and non-empty `sub` checks for local JWTs and required
  production `JWT_SECRET` configuration, rejecting known documented
  development values.
- Keycloak token verification explicitly rejects missing/invalid audiences and
  empty subjects. Role mapping now denies tokens carrying multiple recognized
  application roles rather than selecting a privileged role.
- `python -m unittest test_integrations` passed all 16 tests, including the
  new local-token, production-secret, missing-audience, and ambiguous-role
  cases.
- `test_security.py` and `test_api.py` both passed with separate isolated
  SQLite databases and explicit local-auth settings. These are local
  automated checks; live Keycloak login and refresh are still unverified.
- Consent expiry tests also verify expired physician grants deny Patient
  resource reads and ServiceRequest creation and hide expired requests from
  physician listings. The combined integration and file suites passed 25
  tests. Docker was unavailable and local API/HAPI probes did not respond, so
  live HAPI-backed consent behavior remains unverified.
- Fabric deployment guidance now specifies a provider/laboratory two-peer
  endorsement policy. This is documentation, not evidence of a deployed
  network or committed transaction.
- Fabric adapter and chaincode now reject event names outside their closed
  allowlist; tests were added in both Go modules, but could not be run here
  because Go/gofmt are unavailable. The Python backend integration suite
  passed 26 tests, including outbox allowlist and payload-shape checks.
- `backend/loadtest.py` rejects remote and ambiguous target URLs; all three
  focused loopback validation tests passed. No workload was executed, so this
  is runner-safety evidence rather than a scalability result. A CLI check
  confirmed a remote target is refused before connecting.
- ZAP and k6 runners now reject non-loopback targets. Shell syntax and
  non-loopback refusal checks passed. Docker, Go, and k6 are unavailable in
  this environment; the API/HAPI probes timed out, so Fabric tests, live
  deployment, ZAP scanning, and performance measurement remain outstanding.

## Full project verification attempt (2026-11-26)

- `python -m unittest test_integrations test_files test_audit_logger
  test_loadtest` passed all 30 tests using the temporary Python environment.
- `test_api.py` passed its end-to-end local-mode workflow checks, and
  `test_security.py` passed its adversarial API checks, each using a separate
  isolated SQLite database.
- A fresh SQLite Alembic upgrade and `alembic check` passed.
- The running browser UI opened Administrator Overview and Admin tools. The
  read-only audit verification confirmed the existing chain is broken starting
  at entry #33; preserve the historical records and investigate the cause.
- Docker/Compose, Go, Node/npm, and k6 were unavailable. Consequently this was
  not a complete live-stack test: frontend production build, Fabric Go tests,
  live HAPI/Keycloak/Fabric workflows, ZAP scanning, and performance testing
  remain unverified. Python emitted `datetime.utcnow()` deprecation warnings;
  they did not fail the checks.

Additional user-run checks on Arch Linux:

- Docker Compose showed PostgreSQL healthy and the backend running; API
  `/health` returned database connected.
- Both Fabric Go modules passed `go test ./...`.
- HAPI 7.4.0 initialized against PostgreSQL after the Spring-level PostgreSQL
  dialect/LOB configuration was applied. The three previously missing tables
  were present, `/fhir/metadata` reported `CapabilityStatement` / `4.0.1`, and
  API `/health` returned HTTP 200 with `fhir: hapi`.

These are user-provided command results, not tests run from this VS Code
environment. Live Keycloak flows, end-to-end FHIR resource operations, actual
Fabric network commits, ZAP, and meaningful load tests remain outstanding.
Earlier logs showed a temporary Compose DNS failure resolving `db`; the later
user-provided health checks showed database connectivity restored. The admin
dashboard has also reported an invalid local audit chain beginning at entry
#33; preserve that warning and investigate historical data without rewriting
it.

Older performance figures in prior revisions are not current measurements
and must not be cited as results for this version.

## Remaining production-readiness work

- Verify PostgreSQL backups/restores and recovery behavior; Compose database
  connectivity and HAPI schema startup have been demonstrated, but operational
  resilience is not yet evaluated.
- Exercise the imported Keycloak realm through a real browser login, logout,
  refresh, registration, and staff role provisioning.
- Run synthetic FHIR resource create/read/update and workflow round trips
  through the application against HAPI, including `$validate` and reference
  checks.
- Build the adapter image, deploy the Fabric network, submit test events, and
  verify committed transaction IDs on-ledger.
- Execute and review the OWASP ZAP baseline and current-stack load tests.
- Replace process-local login rate limiting with a shared store before
  horizontal API scaling; complete broader organization-level authorization
  and operational hardening.

Use synthetic data only. This prototype is not a production clinical system.
