# Implementation status

This file records verified repository behavior separately from external
deployment claims. Use synthetic data only.

## Implemented

- FastAPI authentication with local JWT and Keycloak/OIDC validation paths,
  role-gated routes, consent expiry/revocation, and database-backed,
  cross-instance login rate limiting.
- Patient-controlled resource-scoped consent for an individual physician or a
  healthcare organization plus one named physician. Organization membership
  is administrator-managed; removal invalidates organization grants
  immediately. Organization grants are restricted to `TREATMENT` purpose and
  selected FHIR resource types.
- FHIR Consent generation includes the named practitioner, organization,
  resource scopes, validity period, and treatment-purpose coding.
- Laboratory workflow, protected clinical files, hash-chained audit log, and
  transactional Fabric outbox.
- React role workspaces, including patient organization-consent controls and
  administrator organization-membership management.
- Production-safe seed flow: explicit strong local demo password, no
  credential output, and a production-only one-time administrator bootstrap
  that does not create synthetic clinical accounts or workflow data.
- FHIR integration errors return generic client messages while server logs
  retain only safe operation and status metadata.

## Partially implemented

- HAPI FHIR R4 create/read/update, `$validate`, reference checking, and
  optimistic version updates are implemented in code. Prior user-provided
  checks verified HAPI R4 metadata, backend readiness, and API login. This
  change's organization Consent has not yet been persisted or validated against
  the live HAPI server.
- Organization membership and consent migrations are implemented and have
  passed a fresh SQLite upgrade and `alembic check`. The new migration has not
  yet been applied to the user's PostgreSQL Compose database. The shared login
  limiter migration `8c41d6a2f705` also requires live PostgreSQL verification.
  An existing consent row was preserved across SQLite upgrade, downgrade, and
  re-upgrade.
- Keycloak/OIDC token verification is implemented and tested with signed
  synthetic tokens; browser sign-in, refresh, logout, and live provisioning
  remain deployment verification tasks.
- Fabric adapter/outbox logic and allowlists are implemented. A live Fabric
  network submission and ledger commit remain unverified.

## Missing features and known defects

- No live HAPI workflow round-trip has been run for this change.
- Organization consent currently supports the named-practitioner model with a
  treatment-only purpose. It does not expose a broader purpose-selection
  policy or direct organization-wide member access.
- PostgreSQL backup/restore, migration recovery, and operational recovery
  tests remain outstanding. The new shared rate limiter has passed isolated
  SQLite session/concurrency tests but has not been exercised on live
  PostgreSQL.
- Four findings from the static review have been addressed in source; see
  `SECURITY_ASSESSMENT.md` for residual deployment actions. ZAP has not run.
- The PostgreSQL audit history previously reported by the user contains a
  genuine hash-chain discontinuity beginning at entry #33. Historical rows
  were not changed. Its cause and actor cannot be determined from the
  available evidence.

## Tests and verification

### Passed in this implementation pass

- `python -m unittest test_organization_consent test_integrations test_files test_audit_logger`
  — 34 tests passed.
- `test_security_hardening.py`, `test_files.py`, `test_organization_consent`,
  `test_integrations`, and `test_audit_logger` — 46 tests passed together,
  covering seed safeguards, database-backed limiter concurrency and failure
  handling, FHIR response redaction, consent-aware file listings, and
  regressions across adjacent backend features.
- `test_api.py` — all functional smoke checks passed against an isolated
  SQLite database.
- `test_security.py` — all adversarial smoke checks passed against a separate
  isolated SQLite database.
- Fresh SQLite Alembic upgrade to head and `alembic check` passed.
- The full migration chain, including `8c41d6a2f705`, passed on a fresh
  isolated SQLite database; `alembic check` reported no schema drift.
- SQLite migration compatibility passed for a pre-existing consent row,
  default values, downgrade, and re-upgrade.
- Workspace diagnostics found no errors in the modified Python files.

### Not run or not verified

- `npm run build` could not run because npm is unavailable in the current
  environment.
- PostgreSQL migrations and HAPI organization Consent `$validate`/persistence
  were not run against live services. Never apply the new migration to the
  user's database without a verified backup and isolated restore test.
- Live Keycloak, Fabric, ZAP, k6, backup/restore, and deployment recovery tests
  remain outstanding.

## External services verified

- User-provided Compose checks previously showed PostgreSQL healthy, HAPI
  metadata reporting FHIR R4 `4.0.1`, backend health reporting database and
  HAPI readiness, and local admin login succeeding.
- The above checks establish service availability at that time, not live
  organization-consent interoperability or operational readiness.

## Environment limitations

- Docker, Node.js/npm, Go, and k6 are unavailable in the current verification
  environment.
- The supplied browser page showed an already-rendered Administrator view but
  repeated Vite WebSocket `ERR_CONNECTION_REFUSED` events, so frontend hot
  reload and full browser acceptance are not verified.
- Backend dependencies were installed into a temporary Python environment;
  project dependency manifests were not changed.
- The existing PostgreSQL database was not modified or migrated during this
  pass.

## Next implementation stage

Apply the new migration to a backed-up disposable or deployment database, then
validate organization Consent create/read/revoke against the configured HAPI
FHIR R4 service. Continue with complete live FHIR workflow verification before
claiming interoperability.

Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged.
