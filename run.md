# HealthHarbor: Run and Explore the Project

This guide covers a complete local run on **Arch Linux** and **Windows 10/11**,
then explains how to explore the application features and start the optional
infrastructure integrations.

> **Recommended first run:** start the API with SQLite and local authentication,
> then start the React frontend. This is the quickest way to explore the
> consent and laboratory workflows without Docker or external services.
>
> PostgreSQL Compose and HAPI FHIR R4 startup/schema were verified on the
> user's Arch Linux deployment on 2026-11-25. End-to-end HAPI resource
> operations, Keycloak flows, and Fabric network commits still need live
> verification. Do not use real patient information; use synthetic/demo data
> only.

## 1. What you need

### For the local application

- Python **3.10 or later**
- Node.js **18 or later** and npm
- A terminal
- Optional: Git, if you are cloning the repository

### For PostgreSQL and optional infrastructure

- Docker Engine + Docker Compose on Arch Linux, or Docker Desktop with the
  WSL2 backend on Windows
- Additional service requirements described in [Optional integrations](#7-optional-integrations)

## 2. Get the project

If you already have the project folder, open a terminal there. Otherwise clone
the repository using its actual URL:

```text
git clone <repository-url>
cd healthcare-exchange
```

Commands below assume the project root contains `backend/`, `frontend/`, and
`docker-compose.yml`.

## 3. Arch Linux: install dependencies

Update the system and install Python, Node.js, npm, and basic build tools:

```bash
sudo pacman -Syu
sudo pacman -S --needed git base-devel python python-pip nodejs npm
```

Check the installed versions:

```bash
python --version
node --version
npm --version
```

The local application does not require Docker. To use Compose later, install
and start Docker:

```bash
sudo pacman -S --needed docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in for the Docker group change to take effect, then verify:

```bash
docker --version
docker compose version
```

## 4. Windows: install dependencies

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/windows/).
   In the installer, enable **Add Python to PATH**.
2. Install **Node.js LTS** from [nodejs.org](https://nodejs.org/). npm is
   included.
3. Optional for cloning: install [Git for Windows](https://git-scm.com/download/win).
4. Optional for PostgreSQL and service profiles: install
   [Docker Desktop](https://www.docker.com/products/docker-desktop/) and enable
   its **WSL2 backend**. Start Docker Desktop before using `docker compose`.
5. Open **PowerShell** and check:

```powershell
py --version
node --version
npm --version
docker --version
docker compose version
```

The final two commands are only needed for Docker-based features. If the
project is stored under WSL2, use the Arch/Linux instructions from a WSL
terminal instead of mixing Windows and Linux Python environments.

## 5. Start the local application (Arch Linux or Windows)

### 5.1 Configure the backend

From the project root, copy the backend example environment file.

**Arch Linux:**

```bash
cp backend/.env.example backend/.env
```

**Windows PowerShell:**

```powershell
Copy-Item backend/.env.example backend/.env
```

For the first run, leave the SQLite database and local-auth settings as
provided. The local defaults are:

- SQLite file: `backend/healthcare.db`
- Authentication: locally issued JWT
- FHIR storage: local application database
- Fabric: disabled
- File bytes: private `backend/uploads/` directory

The local `.env` should use `DATABASE_URL=sqlite:///./healthcare.db`,
`AUTH_PROVIDER=local`, and `FHIR_MODE=local`. Keep `APP_ENV=development` for
local exploration. If `backend/healthcare.db` already exists from an older
run, use a fresh filename such as `sqlite:///./healthharbor-demo.db` in
`backend/.env` before migrating. Never delete an existing database unless you
intend to erase its data. Never use development secrets in a public
deployment.

### 5.2 Create a Python environment and install backend packages

Open a terminal in the project root.

**Arch Linux:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows PowerShell:**

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks environment activation, either use
`.\.venv\Scripts\python.exe` for the commands below, or allow scripts for the
current PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 5.3 Create the schema and sample data

Keep the terminal in `backend/` with the virtual environment active:

```bash
alembic upgrade head
python seed.py
```

PowerShell uses the same commands:

```powershell
alembic upgrade head
python seed.py
```

The seed script creates sample patient, physician, laboratory, and admin
accounts, plus a consent and sample request/report workflow. It prints the
accounts it created. All seeded passwords are `Demo@1234`.

| Role | Email |
|---|---|
| Patient | `asha.patient@example.com` |
| Patient | `vikram.patient@example.com` |
| Physician | `priya.doctor@example.com` |
| Physician | `arjun.doctor@example.com` |
| Laboratory | `lab@example.com` |
| Administrator | `admin@example.com` |

The seed does **not** create a technician account. Create one from the
administrator dashboard before trying technician-only workflow steps.

### 5.4 Start the API

Still in `backend/`, start FastAPI:

```bash
uvicorn main:app --reload
```

PowerShell:

```powershell
python -m uvicorn main:app --reload
```

Leave this terminal running. Verify:

- API health: <http://localhost:8000/health>
- Interactive API documentation: <http://localhost:8000/docs>

The local health response should report the database as connected and FHIR
mode as `local`.

### 5.5 Start the frontend

Open a **second** terminal at the project root and copy the frontend
configuration.

**Arch Linux:**

```bash
cp frontend/.env.example frontend/.env
cd frontend
npm ci
npm run dev
```

**Windows PowerShell:**

```powershell
Copy-Item frontend/.env.example frontend/.env
Set-Location frontend
npm ci
npm run dev
```

Leave this terminal running and open <http://localhost:5173/>.

The default frontend environment points to the local API at
`http://localhost:8000` and uses local authentication.

## 6. Explore the application features

Sign in and out using the account switch by signing out, then signing in with
another seeded account. The frontend shows the workspace permitted for each
role.

### Patient: grant, review, and revoke consent

1. Sign in as `asha.patient@example.com` with password `Demo@1234`.
2. Review the FHIR patient record and existing consent, which was seeded for
   Dr. Priya.
3. In **Choose what to share**, select a physician, select allowed resource
   types, set a duration from 1 to 30 days, and grant access.
4. Review the active/past consent list and the record access history.
5. Revoke a consent and confirm the physician loses access immediately.
6. Review diagnostic reports associated with the patient.

The backend enforces the maximum consent duration and checks consent on
protected requests; the frontend is not the authorization boundary.

### Patient and care-team files

1. As a patient, open **Files** and upload a PDF, JPEG, PNG, TXT, or CSV file
   (maximum 10 MiB). Files are private by default and do not grant access on
   their own.
2. In **Sharing & access**, grant the intended physician `Document` scope.
   The physician's file center will only offer patients with active
   `Document` permission.
3. Sign in as that physician and open **Files** to view or upload records for
   the consented patient. Revoking the permission blocks future file listing
   and downloads immediately.
4. Laboratory staff and assigned technicians can upload only against their
   assigned service requests. Workflow-linked files are visible to the
   patient and authorized members of that laboratory workflow.
5. The patient can delete files in their own record, including files uploaded
   by a physician. Administrators cannot view or download clinical file
   contents.

File data is stored outside the database in `backend/uploads/` for local
development. Keep this directory private and include it in backups. In
Compose, file bytes are stored in the separate persistent `clinical_files`
volume. This prototype does not encrypt files at rest or scan uploads for
malware; use synthetic files only.

### Physician: create a laboratory request and review a report

1. Sign in as `priya.doctor@example.com` with password `Demo@1234`.
2. Review the list of patients who granted access.
3. Create a lab test request for a patient with active consent and choose the
   laboratory.
4. Review the request's workflow status.
5. When the report is finalized, choose **Record clinical review**.
6. Try `arjun.doctor@example.com` with the seeded patient who has not granted
   that physician access to see the consent boundary.

Request creation uses an idempotency key. A repeat with the same key returns
the original request; reusing the key for different input is rejected.

### Administrator: provision staff, connect a technician, inspect audit

1. Sign in as `admin@example.com` with password `Demo@1234`.
2. In **Create a staff account**, create a lab technician. Set a name, unique
   email, temporary password of at least 12 characters, and role
   **Laboratory technician**.
3. In **Assign a technician**, enter the technician email and
   `lab@example.com`, then add them to the lab team.
4. Use **Verify chain integrity** to check the local hash-chained audit
   history.
5. Review the audit events.

The local hash chain is tamper-evident audit logging; it is **not** a
permissioned blockchain.

### Laboratory: accept and assign requests, finalize reports

1. Sign in as `lab@example.com` with password `Demo@1234`.
2. For a new request, choose **Accept request**.
3. Enter the technician email created by the administrator and choose
   **Assign work**.
4. After the technician submits results, review and finalize the report.

The lab cannot assign a technician who is not a member of its team.

### Technician: register specimen, process, and submit results

1. Sign out of the lab account.
2. Sign in using the technician email and password created by the admin.
3. Open assigned work and advance the request:
   - Register specimen.
   - Start processing.
   - Enter the measured result, unit, and clinical conclusion.
   - Submit results for laboratory review.
4. Sign back in as the laboratory account and finalize the report.
5. Sign back in as the requesting physician to record the clinical review.

The backend enforces the workflow order, technician membership and assignment,
and reviewer permissions.

### API and automated regression checks

Open <http://localhost:8000/docs> to inspect and call the API endpoints. Use
synthetic records only; access controls still apply to direct API calls.

To run the local functional, security, and integration tests, stop the
development API if it conflicts with tests, then run from the project root:

**Arch Linux:**

```bash
cd backend
source .venv/bin/activate
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:///./test.db python test_api.py
DB_AUTO_CREATE=1 DATABASE_URL=sqlite:///./security-test.db python test_security.py
python -m unittest test_integrations.py
```

**Windows PowerShell:**

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
$env:DB_AUTO_CREATE = "1"
$env:DATABASE_URL = "sqlite:///./test.db"
python test_api.py
$env:DATABASE_URL = "sqlite:///./security-test.db"
python test_security.py
$env:DATABASE_URL = "sqlite:///./integration-test.db"
python -m unittest test_integrations.py
Remove-Item Env:DATABASE_URL
Remove-Item Env:DB_AUTO_CREATE
```

These are automated tests and may create separate test database files under
`backend/`. They do not test against live Keycloak, HAPI, PostgreSQL, or Fabric
services.

## 7. Optional integrations

### 7.1 Run PostgreSQL with Docker Compose

This path replaces the local SQLite backend database with PostgreSQL.

1. Install and start Docker (Arch Linux) or Docker Desktop (Windows).
2. From the project root, copy `.env.example` to `.env`.
3. Replace all placeholder passwords and secrets. `DB_PASSWORD` is embedded
   in the PostgreSQL URL; use a URL-safe hexadecimal value. A random hex
   value can be generated with Python:

   **Arch Linux:**

   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```

   **Windows PowerShell:**

   ```powershell
   py -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Start the base services:

   ```text
   docker compose up --build
   ```

   Compose starts PostgreSQL and the backend. The backend runs Alembic
   migrations before serving requests.
5. In another terminal, seed sample accounts:

   ```text
   docker compose exec backend python seed.py
   ```

6. Start the frontend using the frontend steps above. It still runs locally
   and calls `http://localhost:8000`.

Use `docker compose logs -f backend db` to inspect startup and readiness.
Stop services with `docker compose down`; this keeps the PostgreSQL volume.
`docker compose down -v` deletes the database volume and its data—only use it
when you intentionally want to erase the local Compose database.

### 7.2 Keycloak / OpenID Connect

Keycloak is an optional Docker profile. It uses the
`healthharbor` realm export in `deployment/keycloak/healthharbor-realm.json`.

1. Ensure Docker is running and root `.env` exists.
2. In root `.env`, set `AUTH_PROVIDER=keycloak`, a strong
   `KEYCLOAK_ADMIN_PASSWORD`, and the realm issuer/JWKS URLs for
   `healthharbor`. Keep the Compose defaults unless you changed hostnames or
   ports.
3. In `frontend/.env`, set:

   ```dotenv
   VITE_AUTH_PROVIDER=keycloak
   VITE_KEYCLOAK_URL=http://localhost:8080
   VITE_KEYCLOAK_REALM=healthharbor
   VITE_KEYCLOAK_CLIENT_ID=healthcare-exchange-web
   ```

4. Start the database, backend, and Keycloak profile:

   ```text
   docker compose --profile identity up --build
   ```

5. Start/restart the frontend development server so it reloads its `.env`.
   Open <http://localhost:5173/> and sign in or register through Keycloak.

Patient registration requires a verified email and the `PATIENT` realm role.
For staff, create the Keycloak user and assign its matching realm role first,
then link it to an application profile through the administrator dashboard
using that user's immutable Keycloak ID (`sub`). Do not link identities by
email alone.

To create the initial application administrator, create a verified Keycloak
administrator user first, then run the operator command in the backend
container (replace the sample values):

```text
docker compose exec backend python provision_keycloak_admin.py --subject "<KEYCLOAK_USER_ID>" --email "admin@example.com" --name "System Admin"
```

The realm import is not a migration of an existing old `wirachain` realm.
Existing installations need an operator-managed migration or a fresh Keycloak
realm/database. Do not erase a populated database just to rename the realm.

### 7.3 HAPI FHIR R4

HAPI runs as the `fhir` Compose profile and stores resources in its own
PostgreSQL database. The Compose service sets HAPI's
Hibernate dialect directly with `SPRING_APPLICATION_JSON` to
`ca.uhn.fhir.jpa.model.dialect.HapiFhirPostgresDialect`, and disables
contextual JDBC LOB creation. This avoids relying only on `HIBERNATE_DIALECT`,
which was present in the container but did not prevent H2-style `blob` and
`clob` DDL errors in the observed startup.

1. In root `.env`, set `FHIR_MODE=hapi` and
   `FHIR_SERVER_URL=http://hapi:8080/fhir`.
2. Start the base services and HAPI:

   ```text
   docker compose --profile fhir up --build -d
   ```

3. If HAPI was already started with the incorrect dialect, recreate only HAPI
   so it receives the corrected Spring configuration. Keep the existing
   PostgreSQL volume:

   ```text
   docker compose --profile fhir up -d --force-recreate hapi
   ```

4. Wait for HAPI startup, then confirm its logs have no `blob`/`clob` schema
   errors and verify the required tables exist. Check `/fhir/metadata` reports
   FHIR `4.0.1`, and API `/health` reports `fhir: hapi`.
5. Test actual FHIR resource create/read operations before treating
   interoperability as verified. Seed sample data only after confirming the
   HAPI configuration and application workflow work.

For a host-run backend connecting to Compose HAPI, set
`FHIR_SERVER_URL=http://localhost:8081/fhir` in `backend/.env`. HAPI mode
makes the HAPI service authoritative for FHIR reads; missing resources are not
silently replaced by local JSON.

### 7.4 Hyperledger Fabric

Fabric requires a running Fabric test network and its credentials; enabling
the Compose profile alone does not create a Fabric network.

1. Install Go **1.23+** and Docker.

   **Arch Linux:**

   ```bash
   sudo pacman -S --needed go
   go version
   ```

   **Windows PowerShell (with winget):**

   ```powershell
   winget install --id GoLang.Go -e
   ```

   Reopen PowerShell after installation, then check `go version`. Alternatively
   install Go for Windows from [go.dev/dl](https://go.dev/dl/).

2. Follow [fabric/README.md](./fabric/README.md) to start the Fabric
   `test-network` and deploy the `clinical-provenance` chaincode to
   `mychannel`.
3. Confirm the Docker network configured by the test network exists. The
   Compose default is external network `net`; set `FABRIC_DOCKER_NETWORK` to
   the network's real name if it differs.
4. Place the client identity certificate, private key, and peer TLS CA where
   root `.env` points to them. The defaults are:
   - `./fabric-identity/cert.pem`
   - `./fabric-identity/key.pem`
   - `./fabric-identity/peer-ca.crt`
5. Set `FABRIC_ENABLED=true`, a shared random
   `FABRIC_GATEWAY_TOKEN` (at least 32 bytes), and a separate random
   `FABRIC_PSEUDONYM_KEY` (at least 32 bytes). Check the MSP ID, peer endpoint,
   TLS server name, channel, and chaincode values against your network.
6. Start Compose with the Fabric profile:

   ```text
   docker compose --profile fabric up --build
   ```

   Include `--profile fhir` or `--profile identity` as well if those
   integrations are also configured and desired.
7. Generate normal application events (for example, grant consent or create a
   lab request), then sign in as an application administrator and inspect
   `GET /audit/ledger` in <http://localhost:8000/docs> and the Fabric network.
   The outbox marks an event committed only after the Gateway confirms a
   transaction ID.

Run unit checks for the Go modules from the project root:

```text
cd fabric/chaincode
go test ./...
go vet ./...
cd ../adapter
go test ./...
go vet ./...
```

Do not submit patient names, clinical values, or other PHI to the ledger.
Only hashes and pseudonymous references should be recorded. An actual
permissioned ledger commit and independent verification require the live
network.

### 7.5 OWASP ZAP and k6

Both supplied runners use Docker and target the running local API. Use
synthetic/test data and scan only systems you own or are authorized to test.

**Arch Linux / WSL2 shell:**

```bash
TARGET_URL=http://localhost:8000 sh security/run-zap-baseline.sh
TARGET_URL=http://localhost:8000 VUS=10 DURATION=1m sh security/run-k6.sh
```

**Windows PowerShell:** run the scripts from a WSL2 shell where Docker is
available. ZAP writes reports under `security/reports/`. The k6 test checks
health and can include authenticated profile requests if `AUTH_TOKEN` is
provided.

These commands execute scans/tests; they do not guarantee a clean security
result or a performance target. Review the generated output.

## 8. Troubleshooting

### Port already in use

Ports `5173`, `8000`, `8080`, `8081`, and `5432` may be in use. Stop the
conflicting service or change the relevant service port and matching frontend
API/Keycloak URL configuration.

### Frontend loads but API calls fail

- Confirm the backend is running and `/health` responds.
- Confirm `frontend/.env` has `VITE_API_BASE=http://localhost:8000`.
- Restart Vite after editing `frontend/.env`.
- Check the backend CORS origin list includes the frontend's exact origin.

### Demo accounts fail to sign in

- Run `python seed.py` from the `backend/` directory using the intended
  database configuration.
- Confirm you are using `Demo@1234`.
- In Keycloak mode, demo password seeding is intentionally disabled; sign in
  with configured Keycloak users instead.

### Migrations or database connection fail

- For local mode, run commands from `backend/` and confirm
  `DATABASE_URL=sqlite:///./healthcare.db`.
- For Compose, check `docker compose logs db backend`, root `.env` values, and
  database readiness.
- The Compose database initialization scripts create databases/users only
  when the PostgreSQL data directory is first initialized.

### HAPI health check fails

HAPI can take about 90 seconds to initialize on first startup. Confirm the
container logs show `Started Application`, then check
`FHIR_SERVER_URL=http://hapi:8080/fhir` inside Compose. The HAPI service must
use `ca.uhn.fhir.jpa.model.dialect.HapiFhirPostgresDialect` through the
Spring application properties configured in `docker-compose.yml`; PostgreSQL
does not accept the H2-style `blob`/`clob` DDL observed with the default
dialect. From a host-run API, use `http://localhost:8081/fhir`. Verify the
tables exist and metadata reports R4 before running application resource
operations.

### Fabric adapter cannot connect

Confirm the external Fabric network exists, the adapter is attached to it,
peer DNS/port and TLS server name match the Fabric network, and all mounted
credential paths are readable by the adapter container.

## 9. Stop the local development services

- Stop the API and frontend by pressing **Ctrl+C** in their terminals.
- Stop Compose services with `docker compose down`.
- Keep or remove persistent test data intentionally; do not remove a database
  volume unless you want to delete that data.
