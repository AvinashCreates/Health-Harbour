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
