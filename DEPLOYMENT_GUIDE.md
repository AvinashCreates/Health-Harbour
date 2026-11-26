# Deployment and recovery guide

This guide describes the existing local Compose topology. It is not a
production-hardening certification. Use synthetic data only.

## Configuration and startup

1. Copy root `.env.example` to `.env`; replace every example secret before
   use. Keep `.env`, Fabric identity keys, and backups private and out of Git.
   `DB_PASSWORD` must be URL-safe hexadecimal because Compose embeds it in the
   SQLAlchemy URL.
2. Start PostgreSQL and the backend:

   ```sh
   docker compose up -d --build db backend
   docker compose ps
   docker compose logs --tail=100 db backend
   ```

3. For HAPI mode, set `FHIR_MODE=hapi` and start the profile:

   ```sh
   docker compose --profile fhir up -d hapi backend
   curl -fsS http://127.0.0.1:8081/fhir/metadata
   curl -i --max-time 10 http://127.0.0.1:8000/health
   ```

   HAPI readiness may take time on first startup. Require a CapabilityStatement
   reporting FHIR R4 `4.0.1` and a healthy backend before testing HAPI-backed
   operations.

4. Start Vite separately from Compose:

   ```sh
   cd frontend
   cp .env.example .env
   npm ci
   npm run dev -- --host 127.0.0.1
   ```

   Open `http://localhost:5173`. The local Vite API URL should be
   `http://127.0.0.1:8000`; confirm `VITE_API_BASE` if the browser reports an
   API connectivity error.

## Optional integration profiles

- **Keycloak:** Configure `AUTH_PROVIDER=keycloak`, `KEYCLOAK_ISSUER`,
  `KEYCLOAK_JWKS_URL`, and `KEYCLOAK_AUDIENCE` in root `.env`; configure the
  matching public client in `frontend/.env` using `VITE_AUTH_PROVIDER` and the
  realm URL. Then start `docker compose --profile identity up -d keycloak
  backend`. The realm import is mounted read-only from
  `deployment/keycloak/healthharbor-realm.json`. Live PKCE login, refresh, and
  logout still need verification.
- **Fabric:** The existing adapter profile requires a separately deployed
  Fabric test network, the external Docker network named by
  `FABRIC_DOCKER_NETWORK`, and local certificate/private-key/TLS files named
  by `FABRIC_CERT_PATH`, `FABRIC_KEY_PATH`, and `FABRIC_TLS_CERT_PATH`.
  Configure `FABRIC_GATEWAY_TOKEN`, MSP, peer, channel, and chaincode settings
  in root `.env` before using `docker compose --profile fabric up -d
  fabric-gateway backend`. Use the deployment and endorsement instructions in
  [fabric/README.md](./fabric/README.md); do not treat adapter health as proof
  of a committed ledger transaction.

## Migration safety

Compose runs `alembic upgrade head` during backend startup. Before starting a
new backend image against existing PostgreSQL data:

1. Back up `healthcare_exchange` and the clinical files volume.
2. Verify the database backup is readable with `pg_restore --list`.
3. Restore it to a new, isolated database and test the migration there.
4. Only after a verified backup and explicit operator approval should the
   migration run against the existing deployment.

Do not delete Docker volumes or use `docker compose down -v`.

## PostgreSQL backup to host files

Run from the Compose project root. Create a private backup directory first and
restrict its permissions. These commands do not change the live database:

```sh
mkdir -p backups
chmod 700 backups
umask 077
stamp=$(date +%Y%m%d-%H%M%S)
docker compose exec -T db pg_dump -U postgres -d healthcare_exchange --format=custom > "backups/healthcare_exchange-$stamp.dump"
docker compose exec -T db pg_restore --list < "backups/healthcare_exchange-$stamp.dump" > "backups/healthcare_exchange-$stamp.list"
sha256sum "backups/healthcare_exchange-$stamp.dump" > "backups/healthcare_exchange-$stamp.sha256"
```

The Compose PostgreSQL cluster also contains separate `keycloak` and `hapi_fhir`
databases. Back them up with separate `pg_dump` commands if their data must be
preserved. Database dumps and checksums contain sensitive operational data;
encrypt them at rest and restrict access. Preserve global roles/permissions
according to the deployment's secret-handling policy.

## Clinical file volume backup

The backend mount point is `/var/lib/healthharbor/files`. Archive it to a
private host path; this reads bytes from the running container but does not
modify the source:

```sh
docker compose exec -T backend tar -C /var/lib/healthharbor -czf - files > "backups/clinical-files-$stamp.tar.gz"
gzip -t "backups/clinical-files-$stamp.tar.gz"
sha256sum "backups/clinical-files-$stamp.tar.gz" > "backups/clinical-files-$stamp.sha256"
```

Use an application maintenance window or filesystem-consistent snapshot when
you need a point-in-time pair of database and file backups. The commands above
run sequentially and do not guarantee a transactionally consistent snapshot
while uploads are occurring.

## Isolated restore drill

Never restore a test over `healthcare_exchange` or an existing volume. Use a
new database name on a disposable PostgreSQL cluster or a dedicated isolated
test cluster. On the same Compose PostgreSQL service, create a new database
name that does not already exist:

```sh
docker compose exec -T db createdb -U postgres -O healthapp healthcare_exchange_restore_test
docker compose exec -T db pg_restore -U postgres --exit-on-error --dbname=healthcare_exchange_restore_test < backups/healthcare_exchange-YYYYMMDD-HHMMSS.dump
docker compose exec -T db psql -U postgres -d healthcare_exchange_restore_test -c '\dt'
```

Verify the expected tables, `alembic_version`, and synthetic test records.
Check connectivity to the isolated database using a temporary client/config
that targets `healthcare_exchange_restore_test`; do not change the production
backend URL. Do not remove the test database until the restore result and
retention requirements have been reviewed.

Restore file archives only into a new isolated directory. Inspect the archive
before extraction, then validate expected file count and hashes against
database metadata. Never extract an untrusted archive as root or over the live
file volume.

## Current verification status

The documented backup and restore commands have not been executed in this
environment. PostgreSQL backup integrity, database restore, file restore, and
application connectivity after restore remain unverified. The Compose
PostgreSQL database and named volumes were not modified by the current
implementation pass.
