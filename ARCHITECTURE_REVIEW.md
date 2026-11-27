# Architecture review

## Latest verification note (2026-11-26)

The Milestone 2 registry backend and React workflows are implemented. The
latest backend suite passed 57 tests with one PostgreSQL-only test skipped,
and SQLite migration/schema checks passed through `2a7f9c6d4e81`. The new
frontend build could not be run because Node.js/npm were unavailable. The
registry migration was not tested on PostgreSQL in this pass. Earlier
disposable PostgreSQL audit concurrency checks remain recorded in
[TESTING_REPORT.md](./TESTING_REPORT.md). The existing project PostgreSQL
database was not accessed or modified.

Live Keycloak flows, HAPI resource workflows, Fabric commits, ZAP, k6,
browser acceptance, and backup/restore remain unverified. This is not a
production-readiness claim.

## Repository and runtime layout

The active Git branch at review time is `main`. Existing uncommitted changes
were present; in particular, user-edited `prompt.md` and `result.md` were
preserved and not normalized or reverted.

- `backend/` contains the FastAPI application, SQLAlchemy models, Alembic
  migrations, API routers, FHIR/ledger services, and Python test suites.
- `frontend/` contains the Vite/React application, role-specific workspaces,
  Keycloak JS adapter, and API client.
- `deployment/keycloak/` contains the Keycloak realm import.
- `deployment/postgres/init/` creates the PostgreSQL roles and separate
  application, Keycloak, and HAPI databases on first volume initialization.
- `fabric/chaincode/` and `fabric/adapter/` are separate Go modules.
- `security/` contains the loopback-restricted ZAP and k6 runners and the
  current-stack k6 scenario.
- `docker-compose.yml` runs PostgreSQL and the backend by default. Keycloak,
  HAPI, and the Fabric adapter are opt-in Compose profiles. Vite runs outside
  Compose.

## Application boundaries

1. The React application calls the API through `frontend/src/api.js`. In local
   development, the default API origin uses IPv4 loopback because Compose
   publishes the API on `127.0.0.1:8000`.
2. FastAPI routers own authentication, patient consent, FHIR workflows,
   clinical files, and audit endpoints. Dependencies enforce identity and
   role checks; resource authorization is performed in backend services and
   route handlers.
3. SQLAlchemy stores application profiles, FHIR mirrors/indexes, consent,
   workflow transitions, file metadata, memberships, idempotency records,
   audit entries, and the Fabric outbox in PostgreSQL (or SQLite for isolated
   local tests).
4. `services/fhir_server.py` handles HAPI readiness, reference checks,
   `$validate`, reads, writes, version-aware updates, and mirror recovery.
   HAPI is authoritative in HAPI mode; the database mirror supports local
   authorization and workflow indexing.
5. `services/ledger.py` delivers allowlisted provenance events from the
   transactional outbox to the Go HTTP adapter. Go chaincode verifies and
   persists permitted events; a successful outbox delivery is distinct from
   a live-ledger verification until commit is confirmed.
6. Clinical file bytes are stored outside the publicly served frontend through
   `services/document_storage.py`. The local adapter uses generated keys,
   private directory/file modes, and no exposed storage paths. When explicitly
   required, AES-256-GCM stores a framed ciphertext with a 96-bit nonce and
   key metadata. Existing plaintext records are left unchanged and explicitly
   classified as legacy storage. The database stores metadata and a digest;
   clinical bytes are not stored in Fabric.
7. `services/audit_logger.py` maintains the application hash chain. It is
   separate from the Fabric ledger and does not repair historical records.
8. The healthcare registry uses independent `HealthcareOrganization`,
   `HealthcareProvider`, application, review-history, organization-role, and
   affiliation tables. `backend/routers/registry.py` exposes the `/api/v1`
   workflows; mutable verification and affiliation status is checked from
   PostgreSQL/SQLite-backed application state, not trusted JWT claims.
9. `services/fhir_sync.py` stores stable FHIR resource synchronization events
   in a dedicated outbox, with payload hashes and bounded retry state. HAPI
   synchronization is never used as an authorization source. Live HAPI create,
   read, search, update, and reconciliation remain unverified.

## Identity and authorization

- Local authentication issues backend JWTs. Keycloak mode uses the public
  browser client and PKCE, while the API validates issuer, audience, signature,
  expiry, subject, and application role.
- Patients control resource-scoped, expiring, revocable grants. The
  organization policy requires a named physician with active
  administrator-managed membership; organization grants are treatment-only.
- Labs and technicians are tied to explicit workflows, membership, assignment,
  and state transitions. Administrator routes do not provide clinical-record
  access.
- The database remains the authorization index; live HAPI or Fabric
  availability does not replace API-side checks.
- Provider eligibility requires a currently VERIFIED profile and at least one
  active affiliation to an APPROVED organization. Each organization
  affiliation is managed independently, and organization administrators are
  scoped by a database role assignment.

## Persistence and startup

- PostgreSQL has persistent `pgdata`; clinical bytes have persistent
  `clinical_files`.
- Compose runs `alembic upgrade head` before starting the API and health-checks
  PostgreSQL before dependent services start.
- PostgreSQL auto-schema creation is disabled for the backend. SQLite local
  tests can use the development auto-create path.
- The registry migration is additive and has passed a fresh SQLite upgrade
  and `alembic check`. It has not been run on the existing project database or
  on PostgreSQL in this implementation pass.

## Verification snapshot and limitations

- An earlier implementation snapshot passed 34 focused backend unit tests,
  both isolated API/security smoke suites, and a fresh SQLite migration plus
  `alembic check`; see the latest verification note above for subsequent
  results.
- User-provided runtime evidence previously verified PostgreSQL connectivity,
  HAPI R4 metadata/readiness, and local API login. No live HAPI workflow,
  Keycloak browser flow, or Fabric ledger commit is established by those
  checks.
- The supplied browser tab reported repeated Vite WebSocket
  `ERR_CONNECTION_REFUSED` events. The frontend server was not restarted by
  this review.
- Docker Compose and k6 were unavailable in that earlier snapshot. Temporary
  Node.js/npm and Go toolchains were used for the latest build and module tests.
- The user-reported PostgreSQL audit history has a genuine break beginning at
  #33. Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged.

## Architecture concerns to track

- API authorization must remain the source of enforcement; React visibility
  and FHIR Consent records are not sufficient by themselves.
- Login throttling now uses shared database state and atomic upserts, with
  focused SQLite concurrency tests. Verify the migration on PostgreSQL and add
  network-level abuse controls before claiming full horizontal production
  readiness.
- HAPI recovery and consistency between authoritative FHIR resources and
  relational workflow mirrors need live failure/restart tests.
- Fabric adapter identity, peer endorsement, commit confirmation, duplicate
  delivery, and restart/retry behavior need a deployed local network test.
- PostgreSQL and file-volume backup/restore must be verified without
  overwriting the user's existing data.
