# Implementation status

This file records verified repository behavior separately from external
deployment claims. Use synthetic data only.

## Latest verification update (2026-11-26)

- The latest complete backend run passed 57 tests, with one PostgreSQL-only
  test skipped. The legacy API and security smoke scripts also passed against
  separate synthetic SQLite databases.
- The full SQLite migration chain through registry revision
  `2a7f9c6d4e81` passed, and `alembic check` reported no schema drift.
- The registry frontend was added after the previously successful frontend
  build. This environment has no Node.js/npm, so that updated build and browser
  acceptance remain unverified.
- Earlier in the work, both Fabric Go modules passed tests and vet; those
  commands were not rerun in this implementation pass.
- Disposable PostgreSQL audit concurrency tests passed earlier under
  `REPEATABLE READ` and `READ COMMITTED` server defaults. The registry
  migration was not tested on PostgreSQL in this pass.
- The existing project PostgreSQL database and historical audit entry #33
  were not modified. See [TESTING_REPORT.md](./TESTING_REPORT.md) for exact
  commands and evidence.

## Milestone 5 security hardening

- Added additive migration `a31e7c9d2f10` for processing, scan, encryption
  version, and key metadata on `clinical_files`.
- Added AES-256-GCM envelope storage when `DOCUMENT_ENCRYPTION_REQUIRED=true`
  and `DOCUMENT_ENCRYPTION_KEY` contains 32 bytes encoded as base64 or hex.
- Added wrong-key, missing-key, ciphertext-tampering, and unique-nonce tests.
- Added a scanner interface and ClamAV TCP adapter. When scanning is required,
  clean, malicious, unsupported, unavailable, and timeout outcomes have explicit
  statuses and no failed/unscanned record becomes downloadable.
- Files workspace now displays processing, scan, and storage-protection status.
- Existing unencrypted files remain identifiable as legacy storage and are not
  rewritten automatically. Live managed KMS, antivirus service, HAPI, Fabric,
  PostgreSQL, and browser verification remain outstanding.

## Milestone 4 clinical document exchange

- Reused the existing private `ClinicalFile` model and `/files` API rather
  than adding duplicate document metadata.
- Added a `LocalDocumentStorage` adapter with generated storage keys,
  0700 directories, 0600 files, and path/key validation.
- Added allowlisted laboratory, prescription, diagnostic, certificate, clinical,
  discharge, imaging, clinical-record, and lab-result categories.
- Added duplicate checksum rejection for active patient documents.
- Added audit events for upload rejection and denied document downloads.
- Existing provider/organization/current-consent checks remain authoritative;
  revocation, expiry, provider suspension, organization suspension, and
  affiliation loss block downloads.
- No application-level encryption or antivirus integration is implemented.
  HAPI persistence remains synchronous and FHIR retry/outbox behavior is not
  claimed as live-verified.

## Milestone 3 patient-provider care implementation

- Added `CareConnection` and `ProviderRecordRequest` models plus additive
  Alembic revision `f4c1a6d2e9b7`.
- Added patient care-connection initiation, provider accept/decline/close,
  provider record-request creation/cancellation, and patient approve/reject
  APIs under `/api/v1`.
- Patient approval creates the existing resource-scoped `Consent` record,
  including organization affiliation and expiry. Rejection creates no consent.
- All new transitions recheck current provider verification, organization
  approval, and active affiliation state. Patient/provider ownership and cross-
  tenant request access are checked on the backend.
- The Registry, Sharing & access, and Doctor workflow frontends now include
  care-discovery/connection and record-request controls using live APIs.
- Focused care-request tests passed. The updated frontend and PostgreSQL
  migration remain blocked by unavailable Node/npm and PostgreSQL tooling.

## Milestone 2 registry implementation

- Added organization/provider application and verification records,
  organization-scoped role assignments, independent provider affiliations,
  and status-history records through additive Alembic revision
  `2a7f9c6d4e81`.
- Added authenticated `/api/v1` application, directory, provider profile,
  affiliation, organization administration, platform review, and
  administrator affiliation-oversight endpoints. Admin lists and directories
  are paginated; private evidence references are not returned by public
  directory responses.
- Added the React Registry workspace for applicants, providers, organization
  administrators, platform reviewers, and patients browsing approved
  organizations/eligible providers. The workspace uses backend APIs; it does
  not use hardcoded directory data.
- Tightened provider/organization eligibility checks to use current database
  status and affiliation records. Legacy clinical workflow tests now seed
  synthetic verified providers and approved organizations rather than
  weakening those checks.
- Rejected organization applications can be resubmitted against the same
  organization profile. Organization administrators can discover verified
  providers eligible for invitation without guessing provider identifiers.
- Verified with seven registry API tests, including tenant isolation,
  private evidence separation, suspension, affiliation independence,
  administrator oversight, and rejected-application resubmission.
- The registry migration has been tested on isolated SQLite only. No
  production-ready status, official credential verification, live FHIR
  linkage, Keycloak browser authentication, or deployed PostgreSQL migration
  is claimed.

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

- Live Keycloak browser authentication, HAPI organization Consent
  `$validate`/persistence, and Fabric network commits remain unverified.
- PostgreSQL migrations and HAPI organization Consent `$validate`/persistence
  were not run against the existing project database. Never apply the new
  migration to that database without a verified backup and isolated restore
  test.
- Live Keycloak, Fabric, ZAP, k6, backup/restore, and deployment recovery tests
  remain outstanding.

## External services verified

- User-provided Compose checks previously showed PostgreSQL healthy, HAPI
  metadata reporting FHIR R4 `4.0.1`, backend health reporting database and
  HAPI readiness, and local admin login succeeding.
- The above checks establish service availability at that time, not live
  organization-consent interoperability or operational readiness.

## Environment limitations

- Docker Compose and k6 were unavailable. Node.js/npm, Go, and PostgreSQL
  were supplied through temporary installations for the checks above.
- The supplied browser page showed an already-rendered Administrator view but
  repeated Vite WebSocket `ERR_CONNECTION_REFUSED` events, so frontend hot
  reload and full browser acceptance are not verified.
- Backend dependencies were installed into a temporary Python environment;
  project dependency manifests were not changed.
- The existing PostgreSQL database was not modified or migrated during this
  pass.

## Next implementation stage

Complete the Milestone 2 verification gate by building the updated frontend
with Node.js/npm, running browser acceptance against an isolated backend, and
testing revision `2a7f9c6d4e81` on a separately provisioned disposable
PostgreSQL database. Continue only after these checks pass. Never use the
existing project PostgreSQL database for this verification.

Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged.
