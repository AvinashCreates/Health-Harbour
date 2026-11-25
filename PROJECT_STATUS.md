# HealthHarbor implementation status

This status distinguishes code implemented and locally tested from external
services that still require a real deployment. Mock tests do not establish
production interoperability.

## Application features

### Backend

- FastAPI role-gated authentication, bcrypt local passwords, expiring JWTs,
  login rate limiting, CORS allowlisting, and baseline security headers.
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
| Keycloak / OIDC | Realm export, PKCE browser client, RS256/JWKS signature validation, issuer/audience/expiry checks, role mapping, verified-email patient provisioning, and subject-based profile linking. | Unit tests use signed test tokens. Live Keycloak import, sign-in, and user provisioning remain unverified. |
| HAPI FHIR R4 | Create/update/read paths use reference checks, `$validate`, conditional version updates, and authoritative HAPI reads. Compose sets the PostgreSQL Hibernate dialect directly with Spring application properties and disables contextual JDBC LOB creation. | Verified on the user's machine (2026-11-25): HAPI 7.4.0 completed startup, the `bt2_job_instance`, `trm_concept`, and `hfj_search` tables exist in PostgreSQL, metadata reports FHIR R4 `4.0.1`, and API health reports `fhir: hapi`. Live resource create/read/update and full workflow round trips remain unverified. |
| Hyperledger Fabric | Go chaincode and HTTP Gateway adapter, allowlisted append-only events, transactional outbox with retry/backoff, keyed pseudonym references, payload hashes, and commit status only after Gateway confirmation. | User ran `go test ./...` successfully in both Go modules on 2026-11-25. A live Fabric network deployment and committed ledger event remain unverified. |
| PostgreSQL / migrations | Alembic schema migrations and Compose startup upgrade; API `create_all` is disabled for PostgreSQL. Compose also mounts a persistent volume for clinical file bytes. | User-provided Compose output (2026-11-25) showed PostgreSQL healthy, backend running, and API health confirming database connectivity. Backup/restore and failure-recovery procedures remain untested. |
| OWASP ZAP | Passive baseline scan runner against a configured target. | Runner added; scan not run. |
| k6 load testing | Current-stack ramping test with optional authenticated reads and JSON summary export. | Runner syntax checked; k6 is unavailable here and no live load results were produced. |

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
