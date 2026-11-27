# Security assessment

## Scope and method

Read-only source review of the current HealthHarbor repository, including
authentication, authorization/consent, file handling, rate limiting, error
responses, frontend output, and deployment configuration. The review did not
connect to external services, mutate a database, run ZAP, or validate live
deployment configuration. Reported issues are source-level findings, not
proof of exploitation in a deployed environment.

## Findings

### HIGH — Demo credentials and credential disclosure — remediated in source

- **Evidence:** The former hardcoded demo-password default and
  password-printing output have been removed from `backend/seed.py`.
- **Remediation:** Local demo seeding now requires an explicit password with a
  16-character minimum, a 72-byte bcrypt-compatible maximum, and uppercase,
  lowercase, numeric, and special characters. The password is never printed.
  `APP_ENV=production` creates only an explicitly configured initial
  administrator and rejects missing or weak credentials; production bootstrap
  credentials are intended only for the one-time seed command.
- **Residual risk:** Existing demo accounts are not automatically deleted or
  rotated, because doing so could modify an operator's database without
  consent. Administrators must rotate or disable legacy seeded accounts before
  production. Keycloak-managed accounts are provisioned in Keycloak, not by
  this local seeder.
- **Status:** Fixed for future seed runs; production operators must inspect
  existing accounts.

### MEDIUM — Organization-membership checks omitted from file listings — fixed

- **Evidence:** Both physician endpoints now use
  `services.consent_access.consented_patient_ids`, the same shared predicate
  used by direct file authorization.
- **Remediation:** Added regression coverage for membership removal,
  membership added after consent, direct consent, and file-list/patient-picker
  behavior.
- **Status:** Fixed in source; focused tests pass.

### MEDIUM — Login rate limiting was process-local — remediated in source

- **Evidence:** `backend/rate_limit.py` now stores HMAC-hashed account keys and
  lockout state in the database with atomic PostgreSQL/SQLite upserts.
- **Remediation:** Added migration `8c41d6a2f705`, bounded stale-record
  retention, success reset, and fail-closed handling (`503`) if the shared
  store is unavailable. Focused tests cover concurrent failures, shared
  sessions, expiry, reset, and store failure.
- **Residual risk:** The limiter is account-keyed, not source-IP-keyed; it
  does not replace network-level abuse controls. All API instances must use
  the same database and stable `JWT_SECRET` for shared hashed keys.
- **Status:** Fixed in source; the migration has not been applied to live
  PostgreSQL.

### MEDIUM — Detailed HAPI errors returned to clients — fixed

- **Evidence:** The global handler no longer returns exception text. It
  returns stable status-specific messages and logs only controlled operation,
  HTTP method, and status metadata; it does not log upstream diagnostics,
  URLs, tokens, or clinical content.
- **Remediation:** Added an API regression test that injects an internal HAPI
  URL and diagnostic string and verifies neither appears in the response.
- **Status:** Fixed in source; live HAPI behavior remains unverified.

## Live-configuration risks

- `JWT_SECRET` has a development fallback in the application configuration;
  Compose requires the environment variable, but uniqueness and production
  strength must be verified by the operator.
- `APP_ENV=production` must be explicitly set for production checks to apply.
- CORS behavior depends on the deployed `CORS_ORIGINS` value; the code default
  is loopback-only.
- The database-backed limiter does not use source addresses; deploy
  network-level rate controls if IP-based throttling is required.
- Seed scripts intentionally leave pre-existing demo users and passwords
  unchanged. Rotate or disable legacy demo users before production.
- File uploads have size/type checks and private storage, but no malware
  scanning or production object-storage policy was verified.
- No live ZAP scan was run: Docker and a live local scan target were
  unavailable.

## Controls reviewed without a confirmed finding

- Local and Keycloak token validation enforce signature/issuer/audience/time
  and subject checks through their respective code paths.
- SQLAlchemy parameterization was used in inspected database queries; no
  confirmed injection sink was identified.
- React sources reviewed did not use `dangerouslySetInnerHTML` or another
  direct HTML injection sink.
- Bearer-token authentication does not use ambient browser cookies, so no
  cookie-based CSRF path was confirmed in the reviewed flows.
- Individual file downloads, workflow transitions, and direct consent checks
  enforce backend authorization. Physician file and patient listings now use
  the same shared consent predicate, with membership-removal and
  post-grant-membership regression tests.

## Verification and next actions

Focused regressions for these four findings pass, along with the existing file
authorization suite. Live PostgreSQL migration, production deployment review,
and a ZAP scan remain outstanding; source tests do not establish live
configuration safety. See [TESTING_REPORT.md](./TESTING_REPORT.md) for what
was and was not executed.

## Verification update (2026-11-26)

The 50-test isolated backend suite, API workflow checks, and adversarial API
checks passed. The PostgreSQL migration chain and audit concurrency regression
also passed against a disposable PostgreSQL 16.11 cluster, including a server
default of `REPEATABLE READ`; no migration or write was made to the existing
project database. Read-only API health and HAPI metadata requests succeeded.
Keycloak discovery timed out, and no ZAP scan or live production configuration
review was performed. These results do not change the live-deployment risks
above or establish production readiness.

## Milestone 8.1 clinical integration findings (2026-11-27)

- The synthetic end-to-end clinical journey passed through consent, laboratory
  order/report/observation, physician review, prescription, patient history,
  audit, and FHIR outbox stages.
- Cross-patient and unauthorized prescription/review attempts are denied by
  role, patient ownership, provider eligibility, and consent checks.
- Report amendments are restricted to final/reviewed laboratory reports and
  preserve previous conclusion, actor, reason, and FHIR synchronization state.
- Live external infrastructure verification remains unavailable: PostgreSQL,
  HAPI, Fabric, and ClamAV outcomes are not established by SQLite or mocks.

## Milestone 10 clinical workflow findings (2026-11-27)

- Prescription creation requires verified provider eligibility and patient
  MedicationRequest consent. Other providers cannot transition or modify a
  prescription they do not own.
- Clinical review creation requires verified provider eligibility and patient
  DiagnosticReport consent, and report/order references must belong to the
  patient.
- DiagnosticReport amendments are restricted to the responsible laboratory
  organization and only finalized or physician-reviewed states.
- Prescription and review APIs remain covered by the existing authentication,
  role, ownership, and consent checks. Live clinical medication and laboratory
  integrations remain unverified.

## Milestone 7.2 validation findings (2026-11-27)

- Cross-hospital consent is rechecked immediately before document metadata,
  retrieval, and import decisions. Revocation between initial request handling
  and the final recheck is denied by the final database query.
- FHIR outbox event processing now uses stable resource type/ID uniqueness,
  row claiming, bounded attempt counts, and permanent-failure rules. Unchanged
  permanent failures are not silently requeued.
- A controlled crash after a mocked remote operation leaves the event FAILED;
  a restart/retry processes it successfully against the stable resource identity.
- SQLite tests demonstrate local transaction/recovery behavior only. Real
  PostgreSQL row-lock timing, HAPI idempotency, and worker multiprocess races
  remain unverified.

## Milestone 8 validation findings (2026-11-27)

- Confirmed and fixed: cross-hospital document APIs now explicitly verify
  consent grantee and organization, approved source organization, and consent
  expiry/revocation/scope before metadata, download, or import.
- Confirmed and fixed: cross-hospital document download is authenticated and
  available only to the requesting provider. Direct HAPI/Binary access is not
  implemented as an authorization bypass.
- Confirmed and fixed: FHIR synchronization runs through an application worker
  and consent approval/revocation no longer performs a synchronous HAPI write.
  Permanent 400/401/403/404/409/422 failures are retained as permanent states.
- Remaining: live revocation race behavior, PostgreSQL row locking, HAPI
  remote confirmation, ClamAV service testing, and Fabric transaction
  confirmation could not be demonstrated with unavailable infrastructure.

## Milestone 7 cross-hospital controls (2026-11-27)

- Cross-hospital requests require a currently verified provider with an active
  affiliation to the requesting organization. Requesting and source
  organizations must be distinct and approved.
- Patient approval creates the existing scoped Consent record; rejection,
  expiry, and revocation block document access. Resource scope is rechecked
  before source-document listing and import.
- Source documents are queried by patient, source organization, deletion
  state, and clean processing state. Import records preserve source document,
  source and receiving organizations, checksum, importing provider, consent,
  and integrity status without copying bytes or changing source ownership.
- Audit events and Fabric allowlist entries cover exchange request, consent
  grant/rejection/revoke, and document import. Clinical contents and secrets
  are not included.
- Live tenant, PostgreSQL, HAPI, Fabric, and browser verification remains
  incomplete; cross-hospital tests currently provide isolated SQLite evidence
  only.

## Milestone 6 FHIR interoperability security (2026-11-27)

- FHIR synchronization is a durable application-state mirror, not an authorization
  source. Stable resource IDs use application IDs and documented identifier
  systems; retry payloads are deduplicated by resource type and ID.
- Admin-only endpoints expose sync status, worker processing, and reconciliation.
  Reconciliation reports discrepancies but does not silently overwrite HAPI or
  application state.
- PractitionerRole references point to the provider and organization domain IDs;
  application verification and affiliation checks remain authoritative.
- Direct HAPI access is not exposed by this application. HAPI resource visibility
  does not bypass consent, ownership, suspension, affiliation, or document
  download checks.
- Live HAPI validation, search, create/read/update, direct Binary access, and
  cross-tenant retrieval remain NOT VERIFIED.

## Milestone 5 security hardening (2026-11-27)

- Clinical documents can be encrypted at rest with AES-256-GCM. Storage uses
  a unique 96-bit nonce, authenticated associated storage-key data, a key
  identifier, and explicit encryption metadata.
- Missing, malformed, mismatched, or invalid ciphertext keys fail closed. The
  application does not emit key material or silently persist plaintext when
  encryption is required.
- Existing unencrypted documents are preserved and labeled as legacy storage;
  no startup re-encryption or rewrite occurs.
- A scanner interface supports clean, malicious, unsupported, unavailable, and
  timeout outcomes. ClamAV TCP is an opt-in adapter. Required scanning never
  silently bypasses unavailable/failed scanners; unscanned records remain
  blocked from download.
- Live ClamAV, managed KMS, HAPI, Fabric, PostgreSQL, and browser verification
  remain explicitly unverified. Local configuration keys are development
  mechanisms only, not production key management.

## Milestone 4 clinical document controls (2026-11-27)

- Clinical files remain private to backend-controlled local storage. A storage
  adapter validates generated storage keys and writes files with private modes.
  API responses expose document IDs and metadata, never internal storage paths.
- Uploads are limited to allowlisted extensions/MIME signatures and 10 MiB;
  filenames and categories are validated and duplicate active checksums are
  rejected.
- Every download is reauthorized against current ownership, consent scope,
  provider verification, affiliation, organization approval, expiry, and
  revocation state. Denied attempts generate audit events without content.
- Upload rejections and denied downloads are audited. Clinical contents,
  passwords, tokens, and storage paths are not included in audit payloads.
- Application-level encryption-at-rest and antivirus scanning are still absent;
  HTTPS is not treated as storage encryption. Live HAPI Binary/DocumentReference
  persistence and Fabric delivery remain unverified.

## Milestone 3 care workflow controls (2026-11-27)

- Care connections and record requests are owned by patient/provider and
  organization-affiliated IDs. Every response, decision, and cancellation
  rechecks ownership and current provider/organization/affiliation state.
- Providers cannot use a stale JWT role or affiliation to initiate workflows:
  `require_verified_provider` and active-affiliation checks run against the
  database for every request.
- Patient approval creates the existing `Consent` model rather than a second
  authorization mechanism. It is resource-scoped, treatment-purpose, bounded
  to 1–30 days, and subject to existing expiry/revoke checks.
- Rejection and provider cancellation create no consent. Suspended providers
  and suspended organizations are denied at initiation and approval.
- Focused tests cover patient/provider/organization ownership, cross-provider
  and cross-patient denial, duplicate transitions, and approval/rejection.

## Milestone 2 registry controls (2026-11-26)

- Added database-backed organization approval, provider verification,
  organization-scoped admin assignments, and independent affiliation
  lifecycles. Existing `doctor` or `lab` roles alone do not satisfy the new
  eligibility checks.
- New and legacy clinical authorization checks read current profile,
  organization, and affiliation state from the database, so suspension or
  termination takes effect without waiting for a JWT refresh.
- Cross-organization affiliation management is constrained by
  `require_organization_admin`; the provider-candidate endpoint is scoped to
  an approved organization that the caller administers. Platform affiliation
  oversight is admin-only and paginated.
- Directory outputs include only approved organizations and verified
  providers with eligible active affiliations. Verification evidence
  references are excluded from public directory responses.
- Added negative tests for non-admin decisions, cross-tenant access,
  unverified activation, evidence privacy, and organization/provider
  suspension. Rejected organization applications now reuse their existing
  organization profile on resubmission; duplicate registration checks remain
  enforced.
- Provider approval history persists the allowed `VERIFIED` decision value,
  and provider suspension changes the actual provider status. Both defects
  were caught and corrected by the new registry regression tests.

### Remaining registry trust limitations

- Provider credentials and organization registration are reviewed manually.
  Evidence references are opaque identifiers only; the application does not
  store or independently retrieve evidence and does not integrate with an
  official registry. Do not treat submission or approval in this prototype as
  official credential verification.
- The new registry migration has passed SQLite checks only in this worktree.
  Disposable PostgreSQL migration verification and frontend/browser
  acceptance remain outstanding; no live deployment was tested.
- No migration or write was made to the existing project PostgreSQL database,
  and historical audit entry #33 was not changed.
