# HealthHarbor — Operations Runbook

## Scope

This runbook covers safe local demonstration and planned production operations. It does not claim that PostgreSQL, HAPI, Fabric, ClamAV, Keycloak, or browser deployment has been live-tested.

## Pre-operational checks

1. Verify `APP_ENV=production` only on production processes.
2. Verify `JWT_SECRET` is unique and at least 32 characters; never print or log it.
   Production startup rejects SQLite, wildcard or loopback CORS origins,
   missing trusted hosts, disabled encryption, invalid encryption keys,
   disabled scanning, unavailable scanner adapters, missing ClamAV hosts,
   missing Keycloak settings when OIDC is enabled, missing HAPI URLs when HAPI
   is enabled, and invalid Fabric configuration.
3. Verify the database migration identity can run `alembic upgrade head`.
4. Verify `DATABASE_URL` points to the intended database; use read-only inspection first.
5. Verify encrypted document storage is enabled when required and the decryption key is available.
6. Verify the scanner is configured and healthy if `DOCUMENT_SCAN_REQUIRED=true`.
7. Verify HAPI/Fabric configuration values are internal secrets, not browser-visible values.
8. Verify audit entry #33 is present and unchanged; do not repair or rehash historical records.

## Startup

### Local isolated demonstration

Use SQLite and local auth. Configure a strong demo password only through `DEMO_SEED_PASSWORD`; never print it.

```sh
cd backend
export DATABASE_URL=sqlite:////tmp/healthharbor-validation.db
export DB_AUTO_CREATE=1
export AUTH_PROVIDER=local
export FHIR_MODE=local
export FABRIC_ENABLED=false
export DOCUMENT_ENCRYPTION_REQUIRED=false
alembic upgrade head
python test_api.py
python test_security.py
```

### PostgreSQL deployment

Before applying migrations:

1. Take and verify a backup.
2. Restore it into a disposable database if restoring is part of validation.
3. Run `alembic upgrade head` against the intended database only.
4. Run `alembic check`.
5. Verify application health and login before enabling traffic.

Never point migration commands at the existing personal/project database without explicit operator approval.

## Health and readiness

- `GET /health/live` verifies process liveness.
- `GET /health/ready` verifies database and configured component readiness.
- `GET /health` remains available as the compatibility health endpoint and verifies database/FHIR status.
- `/audit/verify` verifies the application audit chain. A mismatch at historical entry #33 is a known baseline and must not trigger deletion or rehashing.
- `/api/v1/admin/fhir/sync/status` exposes FHIR outbox counts for administrators.
- `/audit/ledger` exposes Fabric outbox status and transaction IDs to administrators.

## FHIR worker recovery

The application worker polls `FHIRSyncOutbox` every five seconds in its lifespan:

- `PENDING`/`FAILED` due events are processed.
- Permanent 400/401/403/404/409/422 failures remain permanent.
- Bounded retries use exponential backoff.
- Worker restart does not delete pending rows.
- Record state changes in the outbox before retrying; do not edit payload or status manually unless resolving an incident.

If HAPI is unavailable:

1. Keep application authorization independent.
2. Preserve pending events.
3. Alert on failed/permanent-failed counts.
4. Restore HAPI and process pending events.
5. Reconcile missing, differing, or unexpected remote resources.

Never mark a resource synchronized based on outbox status alone.

## Fabric worker recovery

The Fabric worker polls `LedgerOutbox` every two seconds when enabled:

- Each event has pseudonymous actor/subject/resource references and a payload hash.
- A transaction ID is written only after gateway confirmation.
- Retry at most through the configured attempt limit.
- A ledger failure never grants document or consent access.

If Fabric is unavailable:

1. Preserve pending events.
2. Continue application authorization and clinical operations.
3. Alert on delivery failures.
4. Restore gateway connectivity and process pending events.
5. Reconcile transaction IDs with the Fabric ledger before declaring success.

## Document recovery

### Upload failure

- Roll back database state if storage/FHIR operations fail.
- Remove newly written storage bytes if database or remote state fails.
- Keep rejected/quarantined/failed-scan documents unavailable.

### Missing or inaccessible file

1. Verify consent and authorization first.
2. Verify metadata row and file processing status.
3. Check private storage volume/path and encryption metadata.
4. For encrypted files, verify key ID and key availability without exposing key material.
5. If ciphertext is tampered or unreadable, deny retrieval and preserve audit evidence.

### Backup

Back up PostgreSQL and clinical file storage as coordinated restore units. Encryption key material requires a separate secure backup and key-restoration procedure.

No live backup/restore test has been performed in this assessment.

## Audit incident handling

1. Stop the affected application instance if a new audit mismatch appears.
2. Export the mismatch and surrounding rows; do not print clinical payload details.
3. Preserve entry #33 as-is.
4. Verify whether the mismatch begins at a known historical entry or a new entry.
5. Never delete, rewrite, rehash or regenerate audit rows to make verification pass.
6. Open an incident with actor, timestamp, database snapshot, application version and affected API route.

## Database incident response

1. Detect and isolate the database failure.
2. Preserve the volume and logs.
3. Restore to a fresh test database first.
4. Validate migration state and record counts.
5. Promote only after application health, audit verification and smoke tests pass.

No live PostgreSQL restore test is verified.

## Secret rotation

- Rotate `JWT_SECRET`: schedule a bounded session invalidation window.
- Rotate database credentials: update application secrets and restart workers first, then revoke old credentials.
- Rotate document encryption keys: use key-version metadata and a tested re-encryption procedure; do not overwrite legacy ciphertext without verification.
- Rotate HAPI bearer/Fabric gateway tokens/pseudonym keys independently.
- Never commit secrets or paste secret values into tickets, logs or reports.

## Unsupported integrations

- Live HAPI CRUD/search/update and remote reconciliation are unverified.
- Live HAPI direct-Binary access is unverified.
- Live Fabric transaction confirmation is unverified.
- Live ClamAV scanning is unverified.
- Live PostgreSQL backup/restore is unverified.
- Live Keycloak browser OIDC flow is unverified.
- Frontend production build/browser acceptance is unverified.

## Escalation

Escalate immediately for:

- Unauthorized clinical data access
- Encryption key exposure or decryption failure
- New audit-chain mismatch
- Consent record incorrect or stale
- Suspected PHI exposure in logs
- Database restore mismatch
- Worker duplication or stuck permanent-failed events
- HAPI or Fabric payload containing unexpected identifiers or clinical content
