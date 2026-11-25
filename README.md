# HealthHarbor

HealthHarbor is a consent-aware healthcare exchange prototype for patients,
physicians, and clinical laboratories. It provides scoped consent, a staged
laboratory workflow, local development mode, and optional Keycloak/OIDC,
HAPI FHIR R4, and Hyperledger Fabric integrations.

The PostgreSQL-backed Compose deployment and HAPI FHIR R4 startup/database
schema were verified on the user's Arch Linux machine on 2026-11-25. End-to-end
FHIR resource operations, live Keycloak authentication, Fabric ledger commits,
ZAP findings, and meaningful load-test results remain unverified. See
[PROJECT_STATUS.md](./PROJECT_STATUS.md) for the evidence and remaining work.

## Run locally

Requirements: Python 3.10+ and Node.js 18+.

```bash
# Terminal 1: API
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn main:app --reload

# Terminal 2: React app
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Open http://localhost:5173. API documentation is at
http://localhost:8000/docs. Local demo accounts use password `Demo@1234`:

| Role | Email |
|---|---|
| Patient | `asha.patient@example.com` |
| Patient | `vikram.patient@example.com` |
| Physician | `priya.doctor@example.com` |
| Physician | `arjun.doctor@example.com` |
| Laboratory | `lab@example.com` |
| Administrator | `admin@example.com` |

Public local registration creates patient accounts only. Staff accounts must
be provisioned by an authenticated administrator. An administrator associates
technicians with labs using `POST /auth/laboratory-memberships`.

## Core workflow

1. A patient chooses a physician, FHIR resource scopes, and a duration of
   1–30 days; consent can be revoked early.
2. The physician selects a consented patient and a laboratory, then creates a
   ServiceRequest with an `Idempotency-Key`. Retrying the same key returns the
   same request; reusing it for different input is rejected.
3. That laboratory accepts the request and assigns one of its registered
   technicians.
4. The assigned technician registers a specimen, starts processing, and
   submits preliminary observations and a report.
5. The laboratory reviewer finalizes the report.
6. The requesting physician reviews it while active DiagnosticReport consent
   remains in force.

The backend rejects invalid transitions, unauthorized labs, technicians not
assigned to the lab, and technicians not assigned to a specific request.
Patient consent checks run server-side on protected reads and writes.

## Consent-aware clinical files

The Files workspace supports private PDF, JPEG, PNG, TXT, and CSV uploads up
to 10 MiB. Patients can add records to their own file center. A physician can
upload or view a patient's files only while that patient has granted active
`Document` consent. Laboratory staff can upload workflow-linked files only
for their lab's or technician's assigned requests; file access remains
restricted to that workflow. Patients can remove files from their own record,
including files uploaded by their care team. Administrators do not receive
clinical-file access.

File bytes are stored off-chain in a private local directory (`backend/uploads`
by default) and are exposed only through authenticated API downloads.
`DocumentReference` resources contain metadata and a protected download URL;
clinical file contents are not written to the audit ledger. Compose uses a
separate persistent `clinical_files` volume. Back up this storage together
with the database and protect it with deployment-level encryption, access
controls, malware scanning, and retention policies before any real-world use.
The prototype does not provide those production storage safeguards.

## Tests

```bash
# From the project root, verify both Fabric Go modules.
(cd fabric/chaincode && go test ./... && go vet ./...)
(cd fabric/adapter && go test ./... && go vet ./...)

cd backend
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:///./test.db python test_api.py
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:///./security-test.db python test_security.py
python -m unittest test_integrations test_files test_audit_logger -v
alembic upgrade head
alembic check

cd ../frontend
npm ci
npm run build
```

The application suites cover registration, consent scope and revocation, the
staged lab workflow, access history, audit tamper detection, and security
checks. Integration tests use mocks for Keycloak token verification, HAPI
resource validation/versioning, and Fabric outbox commit behavior; they do not
replace live interoperability tests.

The current-stack k6 runner ramps through 10, 30, and 50 virtual users and
can include an authenticated, role-appropriate read endpoint. It saves a
JSON summary under `security/reports`; see
[`RESEARCH_EVALUATION.md`](./RESEARCH_EVALUATION.md) for controlled test
commands and reporting requirements. Both shell runners are restricted to
loopback targets. `backend/loadtest.py` provides a Python-only GET smoke load
at concurrency 1, 10, and 50 and now also validates that the target is a
loopback origin. Neither runner writes clinical data. Do not treat old
prototype benchmark numbers as current results.

## PostgreSQL Compose deployment

```bash
cp .env.example .env
# Replace every placeholder credential/key before running.
docker compose up --build
docker compose exec backend python seed.py
```

The backend container runs `alembic upgrade head` before starting FastAPI.
User-provided deployment output confirmed PostgreSQL healthy and the backend
connected; see [PROJECT_STATUS.md](./PROJECT_STATUS.md). This confirms the
reported local setup, not production readiness or backup/recovery behavior.
Database creation scripts only run when the PostgreSQL data volume is first
initialized. SQLite remains the default for local development. Uploaded file
bytes persist in the separate `clinical_files` volume; include it in backups.
`DB_PASSWORD` is embedded in the Compose SQLAlchemy URL, so use a URL-safe
hexadecimal value (for example, generate one with `openssl rand -hex 32`).

## Optional external integrations

### Keycloak / OpenID Connect

[`deployment/keycloak/healthharbor-realm.json`](./deployment/keycloak/healthharbor-realm.json)
configures a public browser client with Authorization Code + PKCE, verified
email, realm roles, and the API audience.

1. In root `.env`, set `AUTH_PROVIDER=keycloak` and replace the Keycloak admin
   password. Set `KEYCLOAK_ISSUER` to the issuer in the token and
   `KEYCLOAK_JWKS_URL` to the endpoint reachable from the API container.
2. In `frontend/.env`, set `VITE_AUTH_PROVIDER=keycloak` and confirm the
   Keycloak URL, `healthharbor` realm, and client ID.
3. Run `docker compose --profile identity up --build`, then run the frontend.
   The realm is imported on first startup of a fresh database.
4. Patient self-registration is completed by Keycloak and provisioned locally
   after a token with verified email and the patient realm role is received.
   Create staff in Keycloak with the matching role, then provision the local
   profile by subject in the admin UI. Profiles are never linked by email
   alone.

The realm has been renamed from `wirachain` to `healthharbor`. Existing
Keycloak deployments still using the old realm need an operator-managed realm
migration or a fresh realm import; changing the application name does not
rename an already provisioned Keycloak realm.
The browser client allows `localhost` and `127.0.0.1` on Vite's 5173/4173
ports. If the realm already exists, importing this JSON will not update it;
add the matching redirect URIs, web origins, and post-logout redirect URIs to
the existing client in Keycloak.

To create the initial application administrator, first create and verify an
administrator user in Keycloak, then run this operator-controlled one-time
command from the API environment:

```bash
AUTH_PROVIDER=keycloak python provision_keycloak_admin.py \
  --subject '<keycloak-user-id>' --email 'admin@example.com' --name 'System Admin'
```

### HAPI FHIR R4

The HAPI container explicitly overrides Spring Boot's Hibernate dialect using
`SPRING_APPLICATION_JSON`. This is necessary because the HAPI-specific
`HIBERNATE_DIALECT` environment variable was present in the container but did
not prevent the observed H2-style `blob`/`clob` DDL from reaching PostgreSQL.
The configuration also disables contextual JDBC LOB creation, which
PostgreSQL's JDBC driver does not implement. Set `FHIR_MODE=hapi` and run
`docker compose --profile fhir up --build`.
The API validates resources with `$validate`, checks references, uses
conditional version updates, and treats HAPI as authoritative for reads.
`/health` checks for an R4 `CapabilityStatement`. For a host-run API process,
use `FHIR_SERVER_URL=http://localhost:8081/fhir`; the Compose-internal URL is
`http://hapi:8080/fhir`. After changing the HAPI database configuration,
recreate only the HAPI container with
`docker compose --profile fhir up -d --force-recreate hapi`; do not remove the
PostgreSQL volume. Confirm HAPI startup logs no longer contain `blob` or
`clob` schema errors and the expected tables exist, then
verify `/fhir/metadata` reports `CapabilityStatement` / `4.0.1`, the expected
database tables exist, and backend `/health` reports `fhir: hapi`. These
startup checks passed on the user's machine on 2026-11-25. FHIR resource
create/read/update operations still need to pass before end-to-end
interoperability is considered tested.

### Hyperledger Fabric

Chaincode, a commit-confirming Gateway adapter, and setup instructions are in
[`fabric/README.md`](./fabric/README.md). Deploy a Fabric network before
setting `FABRIC_ENABLED=true`. Copy the operator identity certificate, private
key, and peer TLS CA certificate to the ignored `fabric-identity/` directory
(readable by container UID 10001). Configure one shared random Gateway token
and a separate random `FABRIC_PSEUDONYM_KEY` of at least 32 bytes, then run
`docker compose --profile fabric up --build`. The Fabric test-network named
`net` must already be running. The transactional outbox stores keyed
pseudonyms and hashes, not clinical or identifying data. Events are marked
committed only after the Gateway confirms a transaction ID. No live ledger
commit is claimed unless a network confirms it.

### OWASP ZAP and k6

Against a running local service, use the passive ZAP baseline and the k6
current-stack health test:

```bash
TARGET_URL=http://localhost:8000 sh security/run-zap-baseline.sh
TARGET_URL=http://localhost:8000 VUS=10 DURATION=1m sh security/run-k6.sh
```

Both runners use Docker. ZAP output is written to the ignored
`security/reports/` directory. The supplied k6 test reports API readiness and,
if `AUTH_TOKEN` is supplied, authenticated profile responses. These are
reproducible test configurations only; no scan or load result has been
produced.

## Security and scalability notes

- In production, set `JWT_SECRET` to a unique secret of at least 32 characters;
  startup rejects missing or documented development placeholder values.
- `CORS_ORIGINS` is an explicit comma-separated allowlist.
- API responses include no-store and baseline browser security headers.
- Passwords are bcrypt-hashed in local mode. Synthetic data only; do not use
  this prototype to store real patient data.
- The local login rate limiter is process-local and is not shared across API
  workers. Use a shared limiter before horizontal production scaling.
- The supplied ZAP and k6 runners refuse non-loopback targets and are intended
  for controlled local evaluation only. A ZAP baseline is not a full
  penetration test; no current scan or meaningful load result is available.
- Organization-level authorization beyond lab-to-technician membership and
  formal production hardening remain future work.
