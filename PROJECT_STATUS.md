# HealthHarbor implementation status

This status distinguishes code implemented and locally tested from external
services that still require a real deployment. Mock tests do not establish
production interoperability.

## Latest end-to-end verification (2026-11-26)

- The latest complete backend run passed **57 tests**, with one PostgreSQL-
  only test skipped. The legacy API and security workflow scripts also passed
  on separate isolated SQLite databases.
- Fresh SQLite Alembic upgrade and `alembic check` passed through registry
  revision `2a7f9c6d4e81_healthcare_registry`.
- The PostgreSQL server default was `REPEATABLE READ`; the actual application
  engine still reported `READ COMMITTED` after a prior query, and the
  independent-process audit append regression passed. The same test also
  passed with an effective `READ COMMITTED` database default. These tests
  verified sequential linkage, recomputed hashes, appending after a synthetic
  discontinuity, and rollback after a forced insert failure.
- A prior frontend build passed before the registry page was added. The new
  registry page build could not be run in this environment because Node.js
  and npm are unavailable. Earlier Fabric module tests passed; they were not
  rerun in this implementation pass.
- Read-only requests to the running local API health endpoint and HAPI
  metadata returned HTTP 200; HAPI reported FHIR R4 `4.0.1`. Keycloak OIDC
  discovery timed out.
- No migration or write was made to the existing project PostgreSQL database.
  The known historical audit discontinuity at entry #33 remains untouched.
- This is **partial academic-demo readiness**, not complete integration or
  production readiness. Live Keycloak login, HAPI resource CRUD/workflows,
  Fabric network commits, browser acceptance, ZAP, k6 performance measurement,
  and backup/restore remain unverified. See [TESTING_REPORT.md](./TESTING_REPORT.md)
  and [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for reproduction details.

## Milestone 5 security hardening status

Milestone 5 adds opt-in AES-256-GCM document encryption, safe key validation,
key/ciphertext metadata, a ClamAV-over-TCP adapter, scan-result status fields,
and fail-closed scanner behavior. Encryption and ClamAV integration are
configuration-driven; missing keys or unavailable scanners do not silently
store or make plaintext documents available. Existing unencrypted files remain
explicitly classified as legacy records rather than being silently migrated.

Live PostgreSQL, Node/npm browser verification, live HAPI persistence, live
Fabric confirmation, and an end-to-end ClamAV service test remain unverified.

## Milestone 4 document exchange status

The existing clinical-file implementation was strengthened with an explicit
local storage adapter, allowlisted document categories, duplicate checksum
rejection, upload-rejection audit events, and denied-download audit events.
Provider downloads remain governed by current consent, provider, affiliation,
and organization state. FHIR DocumentReference metadata is still mirrored in
local/HAPI modes as previously implemented.

No new database migration is required. PostgreSQL migration verification,
Node/npm build, browser acceptance, live HAPI, live Fabric, encryption-at-rest
KMS, and antivirus scanning remain not verified or not implemented.

## Current master-prompt milestone

Milestone 3 patient discovery and provider connection workflows are
implemented in the worktree. It adds care-connection initiation and response,
provider record-access requests, patient approval/rejection, and creation of
existing resource-scoped `Consent` records. The additive SQLite migration and
focused API regressions passed. Registry and Milestone 3 frontend builds,
disposable PostgreSQL migrations, live Keycloak/HAPI/Fabric flows, and browser
acceptance remain unverified.

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
  revoked immediately. Patients may target one physician or an organization
  plus one named physician; organization grants are treatment-only and require
  active administrator-managed membership. Access history is available to the
  patient.
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
| Keycloak / OIDC | Realm export, PKCE browser client, RS256/JWKS signature validation, issuer/audience/expiry/subject checks, unambiguous role mapping, verified-email patient provisioning, and subject-based profile linking. | Signed-token tests pass, including missing audience and ambiguous-role rejection. Live discovery timed out in this verification; Keycloak import, browser sign-in, refresh, and user provisioning remain unverified. |
| HAPI FHIR R4 | Create/update/read paths use reference checks, `$validate`, conditional version updates, and authoritative HAPI reads. Compose sets the PostgreSQL Hibernate dialect directly with Spring application properties and disables contextual JDBC LOB creation. | Read-only HAPI metadata returned HTTP 200 and FHIR R4 `4.0.1`; prior user-provided evidence also confirmed HAPI 7.4.0 startup and backend readiness. Live resource create/read/update and full workflow round trips remain unverified. |
| Hyperledger Fabric | Go chaincode and HTTP Gateway adapter, explicit allowlisted append-only event types, transactional outbox with retry/backoff, keyed pseudonym references, payload hashes, and commit status only after Gateway confirmation. Deployment guidance describes a two-organization local test network with both peer organizations endorsing writes. | Python outbox tests pass. `go test ./...` and `go vet ./...` passed in both Go modules in this verification. A live Fabric network deployment and committed ledger event remain unverified. |
| PostgreSQL / migrations | Alembic schema migrations and Compose startup upgrade; API `create_all` is disabled for PostgreSQL. Compose also mounts a persistent volume for clinical file bytes. | Full upgrade and `alembic check` passed on a disposable PostgreSQL 16.11 database; audit concurrency regression passed under both server/database isolation defaults. No migration or write was made to the existing project database. Backup/restore and failure-recovery procedures remain untested. |
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

## Repeat verification (2026-11-26)

- Re-ran the 30 integration/file/audit/load-runner unit tests; all passed.
- Re-ran `test_api.py`, `test_security.py`, and a fresh SQLite migration plus
  `alembic check`; all passed.
- Started a seeded local API on an isolated loopback port. Health, patient
  login, authenticated profile, file listing, patient resource retrieval by
  ID, and ServiceRequest listing all returned expected successful responses.
  An initial `GET /fhir/Patient` returned 404 because this API exposes an
  individual patient resource at `/fhir/Patient/{patient_id}`, not a patient
  collection endpoint; the correct route returned 200. This was an invalid
  smoke-test URL, not a backend regression.
- Port 8000 did not answer the initial probe in this environment; the isolated
  API test on another loopback port succeeded. Do not stop or modify any
  unknown process occupying a port.
- At this point in the investigation, the previous browser observation
  reported entry #33 among 108 events, but the source database was not
  available here. The exact PostgreSQL finding was later reproduced by the
  user with the read-only inspector; see the PostgreSQL forensic evidence
  below. Current local SQLite results are separate; no historical rows were
  rewritten.
- `datetime.utcnow()` deprecation warnings remain. They do not fail tests but
  should be migrated to timezone-aware UTC timestamps in a separate,
  compatibility-tested change.
- Frontend build/browser automation, Go tests, Docker-based services, live
  HAPI/Keycloak/Fabric, ZAP, and k6 remain unverified because their runtimes
  were unavailable. These are environment or integration-coverage gaps, not
  failures reported by the passing backend test suites.

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
dashboard previously reported an invalid audit chain beginning at entry #33
when its API returned 108 audit entries. The UI renders the result of the
admin-only `/audit/verify` endpoint; it does not invent the broken-entry ID.
On 2026-11-26, the currently available local SQLite files were independently
verified read-only using the same hash and previous-link checks as
`services/audit_logger.py`: `healthcare.db` had 3 valid audit entries, while
`healthharbor-run.db` had 20 entries and a real chain mismatch at entry #16
(both the stored previous link and recomputed hash failed there). These are
separate SQLite files and are not the PostgreSQL audit history. Preserve all
copies; do not rewrite audit rows.

On 2026-11-26, a read-only connection attempt to the configured Compose
PostgreSQL endpoint (`127.0.0.1:5432`, database `healthcare_exchange`) did not
complete PostgreSQL protocol negotiation. The TCP port accepted a connection
but did not return the PostgreSQL SSL-negotiation response; Docker tooling was
unavailable here, so the service/container state could not be inspected and no
PostgreSQL rows were read or changed in this environment. The user subsequently
ran the forensic inspector successfully against the PostgreSQL deployment.

On 2026-11-26, the user ran the read-only inspector against the live
PostgreSQL database `healthcare_exchange`: 113 audit rows; first mismatch
entry #33 (`DATA_ACCESSED`, `2026-11-25T12:49:22.752695`). Its stored
`prev_hash` is `91c69ef747c49880e5b62a8e868eebf64bbdd084215f1341bb7d3d9f506e620a`,
while the preceding chain hash expected by verification is
`60af6590d97dbb723572bb8b78543879a33809cbf59ff443ba6c624ce456ef65`. Its
stored `curr_hash` is
`8aaf7a38a4ed93fd074340c43364c31ab2fb1277a4e7a8b4d89a1b0ffbd38464`,
while recomputation from the expected chain link is
`c32b26863db06af391f1769a8e400caa89d8067eddd8d66282edaa00b0a6d461`.
The user then reran the enhanced inspector: recomputation using #33's stored
previous hash exactly matches its stored current hash
(`current_hash_matches_stored_prev=true`). Thus #33's own event payload,
actor, type, timestamp, and hash serialization are internally consistent with
its stored commitment; the discontinuity is specifically that #33 points to a
different predecessor than #32's current hash. The likely class of cause is a
broken/forked chain link at insertion time or later alteration of `prev_hash`;
the available evidence cannot distinguish those histories. The chain is
cryptographically inconsistent from #33 onward, and this result is not
evidence of which actor or process caused it. No database records have been
altered.

## Login/connectivity investigation (2026-11-26)

- User-provided Compose status showed only `backend` and `db` running; the
  database was healthy and backend process was up. The frontend is a separate
  Vite process, not a Compose service in this setup.
- User-provided `curl` to host `127.0.0.1:8000/health` connected but timed out
  without an HTTP response. The in-container health request returned HTTP 503.
  `/health` checks both SQL connectivity and configured FHIR readiness. Since
  HAPI was not listed among running Compose services, a `FHIR_MODE=hapi`
  configuration without the `fhir` profile would explain the 503; the active
  container setting and response body still need confirmation.
- User then confirmed the active backend environment: `AUTH_PROVIDER=local`,
  `FHIR_MODE=hapi`; `/health` returns
  `{"detail":"FHIR server readiness check failed"}`. This establishes that
  HAPI readiness is one confirmed service fault. Start the `fhir` Compose
  profile and wait for HAPI R4 metadata readiness, or intentionally configure
  local FHIR mode for a local-only run.
- User later started the HAPI profile. HAPI logs report
  `Started Application in 76.819 seconds` at 2026-11-26T12:16:24Z, but host
  requests to both `127.0.0.1:8081/fhir/metadata` and
  `127.0.0.1:8000/health` still timed out for 10 seconds. Therefore "wait for
  HAPI startup" alone did not resolve the issue. Need compare backend-to-HAPI
  service connectivity from inside the backend container with host port
  forwarding, then inspect fresh backend/HAPI logs.
- User subsequently confirmed from inside the backend container: backend root
  returned HTTP 200, HAPI metadata returned HTTP 200 with a
  `CapabilityStatement`, and backend `/health` returned HTTP 200 with database
  connected and FHIR `hapi`. In contrast, host requests to both published
  ports `127.0.0.1:8000` and `127.0.0.1:8081` timed out. This isolates the
  current availability problem to host access/Compose port publication or
  host networking rather than app health, DB connectivity, or HAPI readiness.
  Follow-up read-only probes to the container IPs `172.19.0.2:8000` and
  `172.19.0.4:8080` also timed out from the host, despite Docker proxy
  listeners existing for the published localhost ports. A local-mode admin
  login executed inside the backend container returned HTTP 200 and an admin
  profile. This rules out invalid demo credentials and application login
  handling for the in-container path. The current fault is isolated to host
  routing/bridge reachability, affecting both published services. No Docker
  containers, firewall rules, or databases were changed during diagnosis.
- Host `ip route get 172.19.0.2` selected the physical Wi-Fi route
  (`via 10.76.199.230 dev wlp4s0`) rather than the Compose bridge for subnet
  `172.19.0.0/16`. This strongly indicates a routing conflict or missing route
  for the Docker bridge and explains why both direct container-IP access and
  docker-proxy-published host ports time out while in-container requests work.
  Inspect bridge interface/address and all matching routes before changing
  Compose IPAM; choose a subnet only after confirming it does not overlap VPN,
  LAN, or other Docker networks.
- Further host diagnostics confirmed bridge `br-7dc8efe54912` is UP but has
  no displayed IP address; there is no route for `172.19.0.0/16`, and route
  lookups for both bridge gateway `172.19.0.1` and backend `172.19.0.2` go via
  Wi-Fi. Other Docker networks use `172.17.0.0/16` and `172.18.0.0/16`.
  This points to a missing/unconfigured Compose bridge address/route, not an
  app or login defect. A plain `docker compose down` did not remove the
  project network (`Resource is still in use`); the subsequent `up --profile
  fhir` reused the existing HAPI container/network, so it did not actually
  recreate the bridge. Retry teardown with `docker compose --profile fhir
  down` so the HAPI profile container is included, without `-v`; verify the
  network has no attached containers and is removed before starting services
  again. Do not choose a different subnet until checking all VPN/LAN routes
  and networks for overlap.
- Browser console output showed repeated Vite WebSocket disconnects. That
  indicates the separate development server connection is being lost; keep
  `npm run dev` running and confirm it is healthy independently.
- `frontend/src/api.js` now bounds API requests to 15 seconds and surfaces
  timeout/network errors, preventing an indefinite login spinner. A frontend
  build could not be run in this environment because Node/npm are unavailable.
- A user-run direct POST to `/auth/login` timed out. The provided backend log
  excerpt contains historical HAPI schema-table errors from 2026-11-25 and a
  later startup, but not recent request-time logs, so it does not yet explain
  the current login timeout. Account/auth failure is not distinguished from a
  database/audit-write stall or frontend-to-API connectivity failure.

### Host networking follow-up

- User ran `docker compose --profile fhir down`; backend, HAPI, database, and
  the project network were removed without `-v`. The named data volumes were
  not explicitly removed.
- Recreated `db`, `backend`, and `hapi`. The new bridge
  `br-f813bc5aac5a` has gateway `172.19.0.1/16`, and the host route to
  `172.19.0.2` now correctly uses that bridge. This resolves the previously
  diagnosed missing-route condition.
- Immediate host curls returned connection reset/empty reply shortly after
  Compose reported containers started. This is not yet a successful HTTP
  check; retry after startup/readiness and inspect fresh logs if responses
  still fail. Do not remove volumes or alter firewall rules.
- After profile-aware teardown/recreation, the Docker bridge acquired
  `172.19.0.1/16` and host routes to `172.19.0.2` through that bridge. User
  then verified HAPI metadata HTTP 200, backend `/health` HTTP 200 with
  database connected and `fhir: hapi`, login HTTP 200 as admin from both
  inside the backend container and the Arch host. This confirms the previous
  host-routing issue is resolved and local admin credentials/API login work.
  Refresh Vite and test the browser login; the Vite dev server remains a
  separate process and must be running.
- Follow-up investigation of the browser's "Could not connect" message found
  `localhost` resolves to IPv6 `::1` first on this Arch host while Compose
  publishes the API only on IPv4 `127.0.0.1`. Host `localhost:8000` happened
  to work with curl's address fallback, but browser fetch may fail on the
  IPv6 attempt. The frontend default API host and `.env.example` now use
  `127.0.0.1` for the local API. IPv4 API health, HAPI R4 metadata, and the
  `http://localhost:5173` CORS preflight all returned HTTP 200 here. Frontend
  production build remains unverified because Node/npm are unavailable in
  this environment; the running Vite instance should hot-reload the source,
  or be restarted after setting `VITE_API_BASE=http://127.0.0.1:8000`.
- After the IPv4 API target change, browser-based admin sign-in was completed
  successfully with the seeded local admin account. The Administrator
  Overview loaded from the live backend and displayed 113 audit events with
  the verifier reporting a break at entry #33. This re-confirms the #33
  warning against the active PostgreSQL-backed Compose deployment; it is not
  a UI-only label. Historical audit rows remain untouched.
- Added `backend/inspect_audit_chain.py`, a read-only forensic command that
  reports the first mismatch, event type/timestamp, stored and expected
  previous hashes, and stored/recomputed current hashes without printing the
  event payload. It returned valid for the 3-row local `healthcare.db` and
  correctly diagnosed the known 20-row SQLite mismatch at #16; the audit
  concurrency regression test passed. The source PostgreSQL #33 mismatch has
  not yet been inspected for stored-vs-recomputed details or root cause.
  Compose copies backend files into its image, so rebuild the backend image
  before running this new script inside an already-existing container.

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
- Validate the database-backed login limiter migration against PostgreSQL and
  confirm shared lockout behavior across API instances; validate
  named-practitioner organization consent against live PostgreSQL/HAPI, then
  continue operational hardening.

Use synthetic data only. This prototype is not a production clinical system.

## Named-practitioner organization consent implementation

- Added administrator-managed organization/physician memberships. Membership
  removal blocks organization-based access immediately; direct physician
  consent remains separate.
- Patient consent can now target a lab organization and one named physician.
  Backend authorization enforces active membership, patient scope, expiration,
  revocation, resource type, and treatment-only purpose on protected reads,
  including clinical files.
- FHIR Consent construction now identifies the practitioner and organization
  and records the treatment purpose. The patient and administrator React
  workspaces expose the grant and membership operations.
- Added Alembic revision `71b6c4a2d9e1`. Fresh SQLite migration and schema
  comparison passed. A pre-existing synthetic consent row survived upgrade,
  downgrade, and re-upgrade; the user's PostgreSQL database was not changed.
- Verification in this pass: 34 focused backend unit tests passed, both API
  and security smoke scripts passed, and the fresh SQLite migration and
  `alembic check` passed. `npm run build` was unavailable because npm is not
  installed in the current environment.
- The supplied browser tab showed an already-rendered Administrator view but
  repeated Vite WebSocket `ERR_CONNECTION_REFUSED` events; hot reload and full
  browser acceptance are not verified.
- Live PostgreSQL migration and HAPI Consent validation/persistence have not
  been run. Apply the migration in a backed-up deployment, then verify the
  organization Consent round trip before treating this as live FHIR
  interoperability.

## Security hardening follow-up

- Removed the hardcoded demo password and credential output. Local demo seeding
  now requires an explicit strong password; production seeding creates only an
  explicitly configured initial administrator. Existing seeded accounts are
  deliberately not silently reset or removed.
- File and document-patient listings now share the same named-practitioner
  organization membership checks as file downloads.
- Replaced process-local login lockout dictionaries with HMAC-keyed shared
  database records, atomic SQLite/PostgreSQL upserts, stale-record cleanup,
  success reset, and fail-closed `503` handling. Added migration
  `8c41d6a2f705`.
- FHIR integration errors now return generic client messages and log only
  controlled operation/status metadata.
- The focused hardening/file/consent/integration/audit unit suites passed
  (46 tests), as did the isolated API and security smoke scripts. The full
  SQLite Alembic chain and `alembic check` passed; no live PostgreSQL changes
  were made.
- The new limiter is account-keyed, not IP-keyed. Live PostgreSQL,
  production-configuration, and ZAP verification remain outstanding.

Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged.
