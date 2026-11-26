# Testing report

## Environment

- Python 3.13.15 in the current environment.
- Backend dependencies installed into a temporary virtual environment; no
  dependency manifest changes.
- Docker, Node.js/npm, Go, and k6 unavailable in the current environment.
- Python/API tests used isolated SQLite databases and synthetic accounts.
- No PostgreSQL or Docker volume was modified.

## Passed in the current implementation pass

| Check | Result | Scope and limitation |
|---|---|---|
| `python -m unittest test_organization_consent test_integrations test_files test_audit_logger` | 34 tests passed | Isolated/unit tests; external service behavior is mocked where relevant. |
| `test_security.py` | Passed | Isolated API checks for tokens, roles, privilege attempts, SQL-injection-style input, and login throttling. |
| `test_security_hardening.py`, `test_files.py`, `test_organization_consent`, `test_integrations`, `test_audit_logger` | 46 tests passed | Isolated SQLite; covers explicit seeding credentials, production seed behavior, shared/concurrent rate limiting and fail-closed storage, generic FHIR API errors, membership-aware file listings, and adjacent backend regressions. |
| `test_api.py` | Passed | Isolated local-mode API workflow, including consent, lab transitions, and audit tamper detection. |
| Full Alembic chain through `8c41d6a2f705` | Passed | Fresh temporary SQLite database; no changes to PostgreSQL. |
| `alembic check` | Passed | No schema drift after the full migration chain on SQLite. |
| Existing consent migration compatibility | Passed | Synthetic consent survived SQLite upgrade, downgrade, and re-upgrade; organization defaults were populated. |
| Workspace diagnostics for modified Python and React files | No errors reported | Editor/compiler diagnostics only; not a frontend production build. |
| `git diff --check` on feature files | Passed | Whitespace validation for the implementation edits. |

## Not run / not verified

- `npm run build`: npm is not installed here.
- Browser acceptance/hot reload: the supplied shared page showed rendered
  Administrator content but repeated Vite WebSocket `ERR_CONNECTION_REFUSED`;
  frontend server was not started or restarted by this test run.
- PostgreSQL migration: intentionally not applied to the user's database;
  verified backup and isolated PostgreSQL restore are prerequisites.
- HAPI Consent/DocumentReference/workflow live CRUD and `$validate`: not run.
- Keycloak browser PKCE login, refresh, logout, and live role provisioning:
  not run in this pass.
- Fabric Go tests, network deployment, commit transaction verification, and
  retry/outage tests: Go and Docker unavailable.
- OWASP ZAP: not run; Docker and a live local target were unavailable.
- The four source-review findings have been remediated in source; see
  [SECURITY_ASSESSMENT.md](./SECURITY_ASSESSMENT.md) for residual deployment
  actions and limitations. No live ZAP results are claimed.
- k6 workload and performance metrics: not run; k6 and a live target were
  unavailable. No throughput/latency figures are claimed.
- PostgreSQL backup/restore and clinical-file volume restore: not run.

## Historical audit evidence

The user's PostgreSQL inspector previously reported 113 rows and a genuine
chain-link discontinuity starting at audit entry #33. The implementation and
tests did not edit historical audit rows. Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged.

## Reproduction

See [run.md](./run.md) for isolated API, security, migration, and backend test
commands. See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for the non-destructive
backup and isolated restore procedure.
