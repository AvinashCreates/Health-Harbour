# HealthHarbor local integration guide

Use synthetic accounts and records only. This guide describes a local
demonstration, not production deployment or certification.

## Safety first

The Compose backend runs Alembic migrations during startup. Do not start it
against the existing project PostgreSQL database to follow this guide. Use a
new checkout/configuration with a disposable database, or use the isolated
SQLite workflow below. Never run `docker compose down -v` and never remove
existing volumes. The known historical audit discontinuity at entry #33 must
remain untouched.

Do not use real patient information. Keep `.env`, credentials, Fabric keys,
and database backups out of Git.

## Simplest isolated demonstration: SQLite and local authentication

Requirements: Python 3.10+ and Node.js 18+ with npm. From the repository root,
prepare the backend in one terminal:

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:////tmp/healthharbor-demo.db
export DB_AUTO_CREATE=1
export AUTH_PROVIDER=local
export FHIR_MODE=local
export FABRIC_ENABLED=false
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Create a strong demo password without echoing it, then seed only this empty,
disposable database:

```sh
read -rsp "Synthetic demo password: " DEMO_SEED_PASSWORD
printf '\n'
export DEMO_SEED_PASSWORD
python seed.py
unset DEMO_SEED_PASSWORD
uvicorn main:app --reload
```

The seed script requires an explicit strong password and does not print it.
Seeded users share that password:

| Role | Account |
|---|---|
| Patient | `asha.patient@example.com` |
| Patient | `vikram.patient@example.com` |
| Physician | `priya.doctor@example.com` |
| Physician | `arjun.doctor@example.com` |
| Laboratory | `lab@example.com` |
| Administrator | `admin@example.com` |

Open a second terminal and start the frontend:

```sh
cd frontend
test -e .env || cp .env.example .env
npm ci
npm run dev
```

Open <http://localhost:5173/>. Verify the API at
<http://127.0.0.1:8000/health> and API documentation at
<http://127.0.0.1:8000/docs>. The isolated local-mode health response should
report FHIR mode `local`.

## Synthetic feature walkthrough

1. **Registry and care initiation:** As an authenticated representative, submit an
   organization application in **Care network**. As an administrator, review
   and approve it. A provider submits their professional details and opaque
   evidence-reference IDs; an administrator manually reviews and verifies
   the provider. As the approved organization administrator, invite the
   verified provider. The provider accepts, then the organization
   administrator activates the affiliation. This establishes prototype
   registry state only; it does not contact an official organization or
   professional registry.
2. **Patient directory and connection:** Browse approved organizations and
   providers in **Care network**. Initiate a care connection with a verified
   provider and its active organization. The provider accepts or declines in
   the Care workflow. The connection is separate from record authorization.
3. **Provider record request:** As a verified provider, request only selected
   resource categories from a patient for treatment, with a 1–30 day duration.
   As the patient, approve or reject the request in Sharing & access. Approval
   creates the existing scoped consent record; rejection creates no consent.
4. **Patient consent:** Sign in as `asha.patient@example.com`, choose a
   physician, select resource scopes and a 1–30 day duration, then grant
   access. Confirm the physician can access only the allowed resources.
   Revoke consent and confirm the same access is denied.
5. **Clinical files:** As the patient, upload a supported synthetic PDF, image,
   text, or CSV file (maximum 10 MiB). Grant the physician `Document` scope,
   verify access as that physician, then revoke and verify denial. File
   visibility is enforced by the API, not only the UI.
6. **Laboratory workflow:** As a consented physician, create a ServiceRequest
   for a laboratory. As a lab reviewer, accept it and assign an affiliated
   technician. As the assigned technician, register the specimen, begin
   processing, and submit synthetic results. As the reviewer, finalize the
   report; as the requesting physician, review it.
7. **Administrator tools:** Use the administrator account for account,
   membership, and audit administration. Administrator role does not grant
   access to patient clinical resources.
8. **Audit integrity:** The API's local hash-chain verification detects
   tampering. It is distinct from Fabric and does not validate or repair
   historical records in another database.

## Optional live integrations

These require separate isolated services and are not necessary for the SQLite
demonstration:

- **HAPI FHIR R4:** Use a fresh, disposable PostgreSQL/Compose environment,
  configure `FHIR_MODE=hapi`, and start the `fhir` profile only after checking
  that Compose resolves to the intended new project and volumes. Wait for
  `GET /fhir/metadata` to return a FHIR R4 `CapabilityStatement` and API
  `/health` to pass. Current verification checked metadata/readiness only;
  end-to-end clinical resource CRUD and workflow round trips remain
  unverified.
- **Keycloak:** Configure the backend issuer, JWKS URL, and audience together
  with the frontend public client and PKCE settings. Verify discovery, browser
  login, refresh, logout, and role provisioning in that isolated realm. Live
  discovery timed out in the latest verification.
- **Hyperledger Fabric:** Follow [fabric/README.md](./fabric/README.md) to
  configure an isolated test network, certificates, channel, chaincode, and
  dual-organization endorsement. Run the adapter and verify a committed
  transaction ID; unit tests or adapter health alone do not prove a ledger
  commit.

For any existing PostgreSQL deployment, back up and restore into a separately
named test database before migration testing. Never point a migration command
at the project's current database without explicit operator approval.

## Verification commands

From `backend/`, the unit and smoke suites are documented in
[TESTING_REPORT.md](./TESTING_REPORT.md). The guarded audit concurrency test
must use a disposable PostgreSQL server on loopback port `55439` and a database
named `audit_test_*`; its exact environment guard is:

```sh
AUDIT_TEST_POSTGRES=1 \
AUDIT_TEST_SERVER_DEFAULT='repeatable read' \
DATABASE_URL=postgresql://postgres@127.0.0.1:55439/audit_test_concurrency \
python -m unittest \
  test_audit_logger.AuditLoggerConcurrencyTests.test_postgresql_repeatable_read_server_default_serializes_appends \
  -v
```

Run the Fabric Go module tests with `go test ./... && go vet ./...` from each
of `fabric/chaincode` and `fabric/adapter`. Run `npm ci && npm run build` from
`frontend/`. None of these commands should be aimed at a production service or
database.

## Readiness boundary

The current Milestone 4 file suite and backend/API tests passed on isolated
SQLite. Milestone 4 added private storage adapters, category validation,
duplicate detection, and denied-access/upload-rejection audits. The current
SQLite migration chain passed.
Earlier frontend build, Go module, disposable PostgreSQL migration, and
two-process audit append results are recorded in [TESTING_REPORT.md](./TESTING_REPORT.md).
The new Registry workspace could not be built here because Node.js/npm were
unavailable, and its migration has not been tested on PostgreSQL. The complete
live stack is **partially ready**: live Keycloak browser authentication, HAPI
resource operations, a Fabric ledger commit, browser acceptance, ZAP, k6
performance measurements, and backup/restore have not been verified.
Production readiness is not established.
