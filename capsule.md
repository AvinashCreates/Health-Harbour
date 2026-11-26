# HealthHarbor Project Capsule

**Purpose:** Carry forward the project context when changing Copilot accounts or
starting a new assistant session in this workspace. Read this file first, then
inspect the specific code being changed. This capsule is a navigation and status
guide, not a substitute for checking current source, test output, deployment
configuration, or user instructions.

**Workspace:** `/home/pamarthi-avinash/Downloads/healthcare-exchange`  
**Status snapshot:** 2026-11-26  
**Project type:** Research prototype; not a production clinical system. Use
synthetic identities, files, and clinical data only.

## Continuation instructions for an assistant

1. Treat `abstract.md` as the concise research objective and `prompt.md` as the
   detailed implementation requirements.
2. Read this capsule before asking the user to explain the repository. Then
   inspect relevant source files and verify whether the capsule is still
   current before making changes.
3. Keep **functionality, authorization correctness, and safe data handling
   ahead of visual polish**. The requested visual direction is simple, readable,
   white/black with cement-gray backgrounds; avoid complex interactions.
4. Distinguish implemented code, automated test evidence, mocked integration
   evidence, user-provided live-service evidence, and unverified plans. Do not
   turn one type of evidence into another.
5. Never claim a live Fabric commit, live HAPI resource workflow, live Keycloak
   flow, penetration test, backup/restore test, or current throughput result
   without fresh evidence.
6. Preserve historical audit evidence. A previously observed local audit-chain
   integrity break starts at entry #33; do not rewrite or “repair” history to
   hide it.
7. Preserve existing user changes. The workspace was reported as not having
   Git repository metadata in the earlier environment; check before using Git.
8. After backend source edits, a Compose backend image built from `backend/`
   must be rebuilt because Compose does not bind-mount backend source.

## Product intent

HealthHarbor is a consent-aware exchange prototype for patients, physicians,
laboratories, laboratory technicians/supervisors, and administrators. Its
intended flow is:

1. Patient grants a selected physician access to selected FHIR resource scopes
   for 1–30 days, and may revoke the grant early.
2. An authorized physician creates a laboratory `ServiceRequest`.
3. The assigned laboratory accepts it and assigns one of its technicians.
4. The assigned technician registers a specimen, processes it, and submits
   observations/results.
5. A laboratory reviewer finalizes the report.
6. The requesting physician reviews it while required consent remains active.

Clinical file bytes are intended to remain off-chain. FHIR R4 models healthcare
resources; PostgreSQL stores application records and a local FHIR mirror; HAPI
FHIR is an optional external FHIR server. Fabric is an optional provenance
integration, not the database for clinical records.

## Current repository map

### Top level

- `abstract.md` — project abstract and high-level aims.
- `prompt.md` — detailed project requirements and expected behavior.
- `README.md` — setup, feature summary, integrations, and test commands.
- `PROJECT_STATUS.md` — implementation and verification evidence.
- `RESEARCH_EVALUATION.md` — abstract-to-code mapping and evaluation procedure.
- `future_plan.md` — phased gap-closing plan against `abstract.md`.
- `result.md` — user-provided deployment/test output; distinguish historic
  failures from later successful checks.
- `run.md` — deployment and integration runbook.
- `data.md` — data notes.
- `docker-compose.yml`, `.env.example` — local Compose services and settings.
- `deployment/postgres/init/` — initial PostgreSQL databases/users.
- `deployment/keycloak/` — realm/client import configuration.
- `security/` — ZAP baseline and k6 runners; scan/load results are not implied
  by the presence of the scripts.
- `fabric/` — Go chaincode, Gateway adapter, module tests, and deployment docs.

Generated/local material may be present, including `frontend/node_modules`,
`frontend/dist`, Python cache files, SQLite databases, and compiled Go
executables under `fabric/`. These are not source-of-truth implementation or
verification records. Do not copy database files or generated credentials into
documentation or commits.

### Backend: `backend/`

- `main.py` — FastAPI app, security headers, CORS allowlist, FHIR error mapping,
  health route, and optional ledger-outbox worker.
- `database.py`, `models.py`, `schemas.py`, `deps.py` — SQLAlchemy,
  persistence models, request/response types, and authentication/role
  dependencies.
- `routers/auth.py` — local auth, Keycloak profile provisioning, admin account
  provisioning, and lab-technician membership.
- `routers/consent.py` — consent grant, revoke, active-list, and patient access
  history routes.
- `routers/fhir.py` — patient/physician/lab resources and ServiceRequest /
  Specimen / DiagnosticReport workflow endpoints.
- `routers/files.py` — authenticated upload/list/view/download/delete,
  file authorization, and DocumentReference creation.
- `routers/audit.py` — local audit log and integrity verification endpoints.
- `services/fhir_builder.py` — FHIR R4-shaped resource builders.
- `services/fhir_server.py` — local/HAPI mode, HAPI readiness, validation,
  persistence, retrieval, references, authoritative reads, and recovery of
  missing remote resources from the local mirror.
- `services/audit_logger.py` — local PostgreSQL/SQLite hash-chain audit log;
  documentation explicitly says this alone is not Hyperledger Fabric.
- `services/ledger.py` — allowlisted event pseudonymization, payload hashing,
  transactional outbox enqueue, Gateway submit/retry, and confirmed transaction
  tracking.
- `services/oidc.py`, `auth_utils.py`, `rate_limit.py` — Keycloak token
  verification, local JWT/password helpers, and current login throttling.
- `migrations/` — Alembic migration history.
- `seed.py` — local demo users and synthetic workflow data; seeding invokes
  FHIR persistence helpers.
- `test_api.py`, `test_security.py`, `test_files.py`, `test_integrations.py`,
  `test_audit_logger.py` — local, file, security, integration, and audit tests.
- `loadtest.py` — GET smoke load runner; not a file upload benchmark.

### Frontend: `frontend/`

- React 18 + Vite. Main shell and role-aware navigation are in `src/App.jsx`;
  styles are layered in `src/index.css`.
- `src/api.js` — API base URL and fetch wrappers.
- `src/keycloak.js` — optional Keycloak JS adapter.
- `src/pages/Login.jsx` — local login/registration or Keycloak login and
  introduction panel.
- `src/pages/Overview.jsx` — role-specific metrics, activity, and next-step
  actions.
- `PatientDashboard.jsx`, `DoctorDashboard.jsx`, `LabDashboard.jsx`,
  `AdminDashboard.jsx` — role workflows and admin surfaces.
- `Files.jsx` — upload, preview, download, delete, and role-aware upload
  selectors.
- `SharingAccess.jsx` — patient consent grants, revocation, and access history.
- `components/` — loading skeleton and transfer status.
- Current styling direction: white/black with cement-gray background, simple
  typography and transitions. Recent UI changes replaced the logo letter H
  with `+` and removed the sign-in flow diagram of patient/consent/doctor/lab.

### Fabric: `fabric/`

- `chaincode/` — Go chaincode for append-only provenance events and tests.
- `adapter/` — Go HTTP adapter using Fabric Gateway, validation, and tests.
- `README.md` describes deploying to an existing Fabric test network. The
  Compose `fabric-gateway` profile connects to an **external** Fabric Docker
  network; Compose itself does not create Fabric peers/orderers/channel or
  deploy chaincode.

## Behavior and security notes

### Consent and file access

- Consent duration is bounded to 1–30 days.
- API access checks use server-side active state: not revoked and `expires_at`
  later than the current time. No scheduled cleanup is needed for enforcement;
  old expired rows may remain stored.
- Early revocation sets `revoked_at`; protected access checks should deny that
  grant immediately. The revoke handler also updates the FHIR Consent state.
- Doctor file access requires active `Document` consent. Lab access is tied to
  a laboratory workflow and assignment. Patients access their own files.
- File bytes are off-chain in a private local path or Compose volume. The
  application has an allowlist for PDF/JPEG/PNG/TXT/CSV and a 10 MiB limit.
- `GET /files` batches patient/uploader metadata and workflow lookups rather
  than issuing per-file queries. Lab file listing remains restricted to files
  linked to workflows assigned to that lab or technician; the 250-file result
  cap is unchanged.
- These controls are implemented and covered by local tests, but still need
  live deployment verification for consent boundaries and file downloads.

### Authorization/authentication

- Local mode uses bcrypt-backed passwords and expiring JWTs; the API rejects
  local tokens without a non-empty subject or expiration. Public local
  registration is patient-only. Staff accounts are admin-provisioned.
- Optional Keycloak uses Authorization Code + PKCE in the browser and API-side
  RS256/JWKS, issuer, audience, expiry, subject, and role validation. Tokens
  with missing audiences or multiple mapped application roles are rejected.
  Live Keycloak flows have not been evidenced.
- Production startup requires an explicitly configured JWT secret of at least
  32 characters and rejects the documented development placeholder values.
- Backend authorization checks role, consent scope, ownership, lab identity,
  technician membership, and assignment to a specific workflow.
- CORS allowlist and baseline response headers are configured.
- Login throttling now uses HMAC-keyed shared database state and atomic
  PostgreSQL/SQLite upserts. Verify the migration and cross-instance behavior
  on PostgreSQL before production scaling; source-IP throttling is not
  included.
- The prototype lacks production-grade operational guarantees such as
  external secrets management, encryption/key lifecycle policy, malware
  scanning, immutable backup/recovery proof, and a completed security review.

### Audit and Fabric

- Local hash-chained audit records can detect edits/reordering in the local
  chain; this is not distributed consensus and not a permissioned blockchain.
- `services/ledger.py` queues selected events in an outbox only if
  `FABRIC_ENABLED=true`; a worker submits to the Gateway and marks an event
  committed only after receiving a transaction ID.
- Fabric payloads use keyed pseudonymous references and hashes, not clinical
  record contents. Pseudonyms remain linkable data and require protection.
- Go unit tests passed per user output on 2026-11-25. This is not a live network
  commit.
- The local chain was previously reported invalid from audit entry #33. Preserve
  that evidence and investigate; do not modify historical audit data just to
  make verification green.

### HAPI FHIR

- `FHIR_MODE=local` is the Compose example default; set `FHIR_MODE=hapi` to
  use HAPI at `FHIR_SERVER_URL` (Compose default `http://hapi:8080/fhir`).
- HAPI 7.4.0 R4/PostgreSQL startup was user-verified on 2026-11-25:
  metadata reported FHIR `4.0.1`, expected HAPI tables existed, and API health
  reported `fhir: hapi`.
- Startup/metadata does **not** prove successful application-level FHIR
  create/read/update or a full workflow against HAPI.
- Recent code adds recovery for a resource missing from HAPI when its local
  mirror exists. For a missing ServiceRequest, recovery attempts to restore
  referenced resources recursively first, clears HAPI-managed version metadata,
  and then persists the request. Missing mirror dependencies or cyclic
  references fail explicitly.
- After such backend edits, rebuild/recreate the Compose backend before testing:
  `docker compose --profile fhir up -d --build backend`.

## Evidence snapshot and limitations

Evidence known when this capsule was written:

- In the latest full verification attempt (2026-11-26), all **30 tests** in
  `test_integrations`, `test_files`, `test_audit_logger`, and `test_loadtest`
  passed. The separate `test_api.py` workflow smoke checks and
  `test_security.py` adversarial checks also passed against isolated SQLite
  databases. A fresh SQLite Alembic upgrade and `alembic check` passed.
- The running browser UI was navigated through the Administrator Overview and
  Admin tools using read-only actions. The audit verification action confirmed
  the existing chain is broken starting at entry #33; preserve the data and
  investigate rather than rewriting it. This did not verify every role's UI
  or a production frontend build.
- Docker/Compose, Go, Node/npm, and k6 were unavailable for this attempt.
  Therefore this is not a full live-stack run: frontend production build,
  Fabric Go tests, live HAPI/Keycloak/Fabric workflows, ZAP, and performance
  testing remain unverified. Python emitted `datetime.utcnow()` deprecation
  warnings, but the tested commands passed.
- On 2026-11-26, the backend integration suite passed **16 tests** after local
  and OIDC token validation hardening. The `test_security.py` adversarial API
  checks and `test_api.py` workflow smoke checks also passed against separate
  isolated SQLite databases with local auth explicitly enabled. New tests
  cover required local JWT expiry/subject, production secret configuration,
  missing OIDC audience, and ambiguous Keycloak role claims. This is automated
  local evidence; live Keycloak sign-in and refresh remain unverified.
- Consent expiry regression coverage now also verifies that an expired grant
  blocks physician Patient reads and ServiceRequest creation and hides expired
  ServiceRequests from physician listings. The combined integration and file
  suites passed **25 tests** after this addition. Docker is unavailable in this
  environment, and API/HAPI health probes did not respond, so live HAPI-backed
  consent enforcement remains unverified.
- `fabric/README.md` now documents mapping the local Fabric sample network's
  two peer organizations to provider/laboratory roles and requiring both
  organizations to endorse chaincode writes. This is deployment guidance only:
  no Fabric network or live ledger commit was run here.
- The OWASP ZAP and k6 shell runners now refuse non-loopback targets. Their
  shell syntax and refusal behavior were checked, but Docker is unavailable,
  so neither a ZAP scan nor load test ran. This safeguard does not constitute a
  penetration test or scalability result.
- The backend, Fabric adapter, and chaincode now use an explicit allowlist for
  ledger event types; the Go adapter and chaincode tests reject an unapproved
  event name. Python integration/file tests passed (**26 tests**) including
  confirmation that the backend does not enqueue unapproved event types and
  that the stored outbox projection has only the expected fields. Go tests
  could not be run because Go/gofmt are unavailable here; live Fabric behavior
  remains unverified.
- `backend/loadtest.py` now rejects non-loopback or ambiguous target URLs.
  Three unit tests passed for loopback acceptance and remote/malformed target
  rejection. A CLI check also confirmed a remote target is refused before a
  network request. This protects runner scope; no performance run was made.
- User-provided Arch Linux output showed Docker 29.9.2, Compose 5.6.1, and Go
  1.27.3. Backend/PostgreSQL health, HAPI startup/schema/metadata, and both
  Fabric Go module test commands were reported successful.
- Earlier in this assistant session, the backend integration suite passed
  **12 tests**, including a mocked HAPI recovery test that calls
  `GET /fhir/ServiceRequest` and confirms missing request dependencies are
  restored from the mirror.
- The file access suite covers expiry/revocation, patient/physician/lab/
  technician access, and file lifecycle behavior. A query-count regression
  test verifies that listing 20 patient files takes at most four SELECTs;
  lab and technician list scopes are also asserted. All **8 file tests passed**
  after these changes. This is local SQLite/query-count evidence, not a
  throughput benchmark or live PostgreSQL/HAPI deployment test.
- The local backend workflow smoke script passed all checks with an isolated
  SQLite database (consent/role gates, request lifecycle, report flow, audit
  behavior). This is local-mode evidence, not live HAPI evidence.
- Browser inspection verified the recent monochrome UI changes. No frontend
  production build result was run for every most recent CSS/markup edit.
- A prior unauthenticated probe to `GET /fhir/ServiceRequest` returned 401,
  proving the route was registered in that running backend; it did not test a
  valid user token or the live HAPI recovery path.
- Earlier status documentation recorded 16 integration/file/audit tests and
  a successful frontend build from an earlier checkpoint. Treat those as
  historical until rerun against the present checkout.
- There is no verified current “40 files/second” result. Prior performance
  figures from older revisions must not be presented as current throughput.
  The current Python load runner is GET-only; use a purpose-built synthetic
  file upload/download benchmark to evaluate file throughput.
- OWASP ZAP and k6 scripts exist, but ZAP has not been run on the current
  deployment, and there is no meaningful current-stack load result.
- Penetration testing has not been performed. Automated tests and a passive
  ZAP baseline are not a full penetration test.
- Backup/restore, live Keycloak, live Fabric commits, end-to-end HAPI workflows,
  organization-scale access review, and production readiness remain open.

See `PROJECT_STATUS.md`, `RESEARCH_EVALUATION.md`, `future_plan.md`, and
`result.md` for the fuller evidence, comparison to the abstract, and staged
work plan.

## Local operation quick reference

### PostgreSQL + API + frontend (Compose)

1. Copy `.env.example` to `.env` and replace every placeholder secret. Never
   commit `.env` or use development secrets outside a local environment.
2. Start the base services:

   ```sh
   docker compose up -d --build
   ```

3. Optional integrations:

   ```sh
   docker compose --profile fhir up -d --build hapi backend
   docker compose --profile identity up -d --build keycloak
   docker compose --profile fabric up -d --build fabric-gateway
   ```

   HAPI, Keycloak, and Fabric profile services require their configuration and
   dependencies. Fabric additionally requires an externally running network.
4. Verify with `docker compose ps`, `curl http://127.0.0.1:8000/health`, and,
   when HAPI is enabled, `curl http://127.0.0.1:8081/fhir/metadata`.
   Compose “Started” is not equivalent to service readiness.
5. Backend source is copied into its image; rebuild after editing backend code.
   The frontend dev server may run separately under Vite.

### Local development

- Backend: install `backend/requirements.txt`, run Alembic, optionally seed
  synthetic data, then `uvicorn main:app --reload` from `backend/`.
- Frontend: `npm ci` then `npm run dev` from `frontend/`.
- Default API URL derives from the current host at port 8000, or
  `VITE_API_BASE` can override it. Browser URL/CORS origins must match
  `localhost` vs `127.0.0.1`.
- Local seed runs require a strong explicit `DEMO_SEED_PASSWORD`; production
  bootstrap creates only an explicitly configured administrator. Existing
  demo accounts are not automatically rotated or removed.

### Tests (recheck before reporting)

From `backend/` with requirements installed:

```sh
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:////tmp/healthharbor-api-test.db python test_api.py
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:////tmp/healthharbor-security-test.db python test_security.py
python -m unittest test_integrations test_files test_audit_logger -v
```

From project root:

```sh
(cd fabric/chaincode && go test ./...)
(cd fabric/adapter && go test ./...)
```

Frontend:

```sh
cd frontend && npm ci && npm run build
```

Use fresh isolated test databases. Do not run destructive migrations, wipe
volumes, alter stored audit history, or use real health data.

## Recommended next work, in order

1. **Verify live ServiceRequest recovery:** rebuild backend; authenticate as a
   synthetic lab user; test the list route with a local-mirror request absent
   from HAPI and confirm it is restored; test the explicit failure when a
   dependency is missing. Confirm no duplicate or overwrite behavior against
   the actual running HAPI version.
2. **Prove consent expiry/revocation:** with synthetic users/files, demonstrate
   permitted access before expiry and denied access after expiry and immediate
   revocation. Include a protected file download and record expected status
   codes without exposing tokens or file contents.
3. **Prove HAPI interoperability:** create/read/update/validate representative
   R4 resources and complete the workflow against HAPI; capture actual outcomes.
4. **Prove Fabric operation:** deploy a test network and chaincode, submit a
   synthetic event, verify the transaction independently, and inspect outbox
   retry/failure semantics.
5. **Investigate audit integrity entry #33** from preserved source data and
   document cause; do not rewrite prior rows.
6. **Run an authorized security assessment:** start with a controlled ZAP
   baseline, review findings, then assess IDOR/role boundaries, consent scope,
   upload/download, OIDC configuration, rate limiting, and error leakage with
   synthetic records. Do not scan systems without explicit authorization.
7. **Measure performance correctly:** define target hardware, file sizes,
   concurrent users, upload/download paths, and ledger-on/off comparison.
   Report p50/p95/p99 latency, throughput, errors, resource use, and test
   configuration. Do not claim 40 files/second until reproduced.
8. **Operational readiness:** shared rate limiting, encrypted object storage,
   malware scanning, secret rotation, backup/restore drills, monitoring,
   retention/deletion policy, and documented incident response.

## Key architectural decisions to preserve

- Server-side authorization is authoritative; frontend visibility is not an
  access-control boundary.
- Consent is checked at access time so expiry/revocation takes effect without
  trusting the browser or a delayed cleanup process.
- Clinical files stay off-chain. Ledger events must exclude PHI and raw
  identifiers; pseudonymous references still need protection.
- HAPI is an external FHIR authority in HAPI mode, with a local mirror for
  application ownership/workflow queries and recovery.
- The outbox decouples database commits from asynchronous Fabric delivery.
  Do not report `COMMITTED` until Gateway confirmation is received.
- Keep error states explicit; do not turn upstream FHIR failures into a
  success-shaped empty queue or silent fallback.
- Keep changes surgical, update directly relevant documentation, and validate
  against the actual behavior requested.
