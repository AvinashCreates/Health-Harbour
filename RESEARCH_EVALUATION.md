# Research evaluation status

This report maps the implementation to [abstract.md](./abstract.md) and
separates local functional evidence from tests that require live services.
Do not treat code/configuration, mocked tests, or historical measurements as
evidence that a current external integration was exercised.

## Abstract-to-implementation mapping

| Abstract objective | Implementation evidence | Current evidence / remaining work |
|---|---|---|
| Interoperable exchange among patients, physicians, and laboratories | Separate role workspaces and consent-scoped FHIR-backed workflows | API/workflow tests passed with SQLite. User verified PostgreSQL-backed app health and HAPI startup; repeat workflows using real HAPI resources |
| Standard FHIR resources for patient, request, specimen, observation, and report | FastAPI FHIR routes and resource builders; HAPI FHIR R4 persistence, validation, and retrieval integration | User verified HAPI 7.4.0 R4 startup, PostgreSQL schema tables, and metadata (`4.0.1`); live resource create/read/update, `$validate`, and references are not yet evidenced |
| Patient-selected doctor, resource scope, expiry up to 30 days, and early revocation | Consent API enforces 1–30 days and checks current authorization on protected requests | API and security tests passed with SQLite; repeat against PostgreSQL/HAPI deployment |
| Role-based access for patient, doctor, lab, technician, and administrator | Backend dependencies plus ownership, consent, laboratory membership, and workflow assignment checks | API, security, and workflow tests passed locally; run the same checks against the deployed stack |
| Off-chain clinical data and selected ledger provenance | Private file storage and a Fabric outbox carrying pseudonymous references and hashes | Fabric code and chaincode exist; a real commit has not been verified. Local hash-chained audit is not Fabric |
| Secure authentication | Local JWT mode and optional Keycloak/OIDC PKCE/JWKS integration | Local flow is available; live Keycloak login, refresh, provisioning, and logout require verification |
| Functional and controlled security evaluation | API acceptance/security suites, ZAP runner | Automated tests are not a penetration test; ZAP has not been run on the current deployment |
| Scalability/performance evaluation under rising workloads | k6 ramping runner and a Python load-test script | No current-stack results are recorded. Run against a stated hardware/database/service configuration |
| Evaluate response time, throughput, unauthorized access, FHIR interoperability, auditability, and ledger overhead | Existing tests and configurable evaluation runners | Consolidated current-revision measurements remain outstanding; compare ledger off/on only on the same setup |

## Current verification record

The repository includes:

- `backend/test_api.py` for consent, workflow, access history, idempotency,
  and audit behavior.
- `backend/test_security.py` for token validation, role separation,
  provisioning, injection-style inputs, and login rate limiting.
- `backend/test_files.py` for file authorization and lifecycle.
- `backend/test_integrations.py` for mocked OIDC, HAPI, and Fabric-outbox
  behavior.
- `fabric/chaincode` and `fabric/adapter` Go tests.
- `security/run-zap-baseline.sh` and `security/run-k6.sh`.

For this checkout, the API and security scripts passed with separate
temporary SQLite databases, and the integration, file, and audit unittest
modules passed (16 tests total). Backend requirements were installed only in a
temporary environment. A three-request-per-phase Python load-runner smoke
check also passed on an isolated local API; it is only a runner check, not a
usable performance result. User-provided Arch Linux output from 2026-11-25
also confirms the PostgreSQL Compose database was healthy, backend `/health`
reported database connectivity, both Fabric Go modules passed `go test ./...`,
and HAPI 7.4.0 completed startup with the expected PostgreSQL tables and R4
metadata. This does not yet verify FHIR resource CRUD or workflow
interoperability. Earlier Compose output showed a temporary DNS failure for
`db`; the later successful health output confirms connectivity was restored
at the time of that check.

Historical benchmark numbers from prior prototype revisions have deliberately
been removed from this report. They do not measure the current integrated
stack and must not be cited as current results.

## Reproducible local checks

From the project root, after installing backend requirements into an isolated
environment and activating it:

```bash
cd backend
DATABASE_URL=sqlite:////tmp/healthharbor-api-test.db DB_AUTO_CREATE=1 python test_api.py
DATABASE_URL=sqlite:////tmp/healthharbor-security-test.db DB_AUTO_CREATE=1 python test_security.py
python -m unittest test_integrations test_files test_audit_logger -v
```

Run Go tests separately:

```bash
cd fabric/chaincode && go test ./... && go vet ./...
cd ../adapter && go test ./... && go vet ./...
```

Build the frontend:

```bash
cd frontend && npm ci && npm run build
```

## Live integration checks

1. PostgreSQL and backend Compose readiness has been demonstrated on the
   user's deployment. For each evaluation run, reconfirm `docker compose ps`
   and `/health`, then record environment and database settings.
2. HAPI startup, PostgreSQL schema, R4 metadata, and API health have been
   demonstrated on the user's deployment. Next exercise create/read/update
   for workflow resources and verify references and R4 `$validate` responses.
3. With Keycloak mode enabled, test browser authorization-code + PKCE login,
   logout, token refresh/expiry, patient provisioning, and administrator
   staff provisioning. Confirm the API rejects invalid issuer, audience,
   signature, and role claims.
4. Deploy the Fabric test network and chaincode, enable the Gateway, and
   submit a synthetic consent or workflow event. Verify the event on-ledger
   independently and confirm the application only marks it committed after
   the Gateway returns a committed transaction ID.
5. Keep all test identities and clinical content synthetic. No PHI belongs
   in load tests, application logs, or ledger events.

## Controlled security and load evaluation

Run OWASP ZAP only against the locally controlled deployment:

```bash
TARGET_URL=http://127.0.0.1:8000 OUTPUT_DIR=./security/reports ./security/run-zap-baseline.sh
```

The k6 runner ramps through 10, 30, and 50 virtual users. Set `AUTH_TOKEN` to
a short-lived token for a synthetic test account; `AUTH_PATH` can select an
authorized read endpoint for the account's role. The runner writes its
machine-readable summary into `security/reports` by default:

```bash
TARGET_URL=http://127.0.0.1:8000 \
AUTH_TOKEN='<short-lived-synthetic-account-token>' \
AUTH_PATH=/consent/active \
RAMP_DURATION=1m \
./security/run-k6.sh
```

For a Python-only smoke load (100 GET requests at concurrency 1, 10, and 50),
run from the backend directory with a suitable synthetic token:

```bash
LOAD_TEST_URL=http://127.0.0.1:8000 \
LOAD_TEST_TOKEN='<short-lived-synthetic-account-token>' \
LOAD_TEST_READ_PATH=/consent/active \
python loadtest.py
```

This script measures only read requests and `/health`; it does not create test
records. The k6 runner provides the staged virtual-user ramp.

Choose an `AUTH_PATH` permitted to the token's role. For example,
`/consent/active` is patient-only; a `403` indicates a test configuration or
authorization mismatch, not successful workload behavior. Do not put tokens
in committed files or reports.

For each run, record the commit/revision, enabled services, hardware/CPU and
memory limits, database, number of users, run duration, warm-up, and whether
Fabric is enabled. Report p50/p95/p99 latency, throughput, error rate, and
resource utilization. For Fabric overhead, perform matched runs with the
same configuration and synthetic workload, changing only ledger delivery;
measure submission separately from commit confirmation. Do not invent
results if a service or metric was unavailable.
