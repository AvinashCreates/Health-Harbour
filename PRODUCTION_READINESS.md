# HealthHarbor — Production Readiness Assessment

**Assessment date:** 2026-11-28  
**Scope:** source review and locally executable evidence in the current repository  
**Verdict:** **NOT PRODUCTION READY — locally demonstrated prototype with multiple deployment-critical gaps**

## Milestone 9.1 hardening update — 2026-11-28

- Production startup now rejects SQLite database URLs.
- Production startup rejects wildcard or loopback CORS origins.
- Production startup requires explicit trusted hosts.
- Production startup requires encryption enabled and a valid 32-byte key.
- Production startup requires a ClamAV scanner host and scan-required mode.
- Keycloak issuer/JWKS/audience, HAPI URL, and Fabric configuration are fail-fast validated according to enabled modes.
- Added `/health/live` and `/health/ready` endpoints. Readiness reports database, FHIR, scanner, encryption, and Fabric component state without secrets.
- Development mode remains usable with SQLite, local auth, loopback CORS, and optional integrations.

## Executive summary

HealthHarbor has substantial application functionality: local authentication, registry workflows, consent-aware record exchange, encrypted document storage, FHIR synchronization state, a Fabric outbox, audit chaining, and clinical workflows. Backend behavior has been exercised extensively on isolated SQLite databases and through unit/API/security suites.

The project is not ready for production or real patient data. The most important blockers are live PostgreSQL/backup validation, external HAPI/Fabric/ClamAV verification, managed key management, frontend build/browser verification, database recovery procedures, monitoring, and formal deployment security review.

## Evidence-backed implementation status

| Area | Evidence | Status |
|---|---|---|
| Backend API and authorization | FastAPI routes, role dependencies, consent and affiliation checks, isolated SQLite suites | Locally tested |
| Database migrations | Alembic chain through `e8d1a4c7b2f5_clinical_prescriptions_reviews`; fresh SQLite upgrade and `alembic check` passed | Locally tested |
| PostgreSQL | SQLAlchemy READ COMMITTED configuration and disposable PostgreSQL audit tests reported previously | PostgreSQL live verification not available in this assessment |
| Audit chain | Hash-chained audit, tamper verification, existing entry #33 preserved | Locally tested; live database untouched |
| Login rate limiting | PostgreSQL/SQLite atomic upsert implementation and migration | Locally tested; live PostgreSQL not verified |
| Document storage | Private local adapter, 0700 directory, 0600 files, generated keys | Locally tested |
| Encryption at rest | Opt-in AES-256-GCM, 96-bit nonce, key metadata and tamper tests | Locally tested; not a KMS |
| Malware scanning | ClamAV TCP adapter and fail-closed scanner lifecycle | Adapter implemented; live ClamAV not verified |
| FHIR interoperability | Resource builders, stable identifiers, FHIR outbox, local mirror, validation service | Mock/local tested; live HAPI not verified |
| Hyperledger Fabric | Allowlisted event outbox, pseudonymous payload, transaction ID confirmation logic | Mock/unit tested; live ledger not verified |
| Frontend | React clinical, registry, consent, file and exchange workflows | Static source/diagnostic review; Node/npm build unavailable |

## Critical gaps

### 1. Encryption key management

`DOCUMENT_ENCRYPTION_REQUIRED=true` requires a 32-byte base64 or hexadecimal `DOCUMENT_ENCRYPTION_KEY`. The default is false. Existing plaintext files are not automatically migrated or re-encrypted.

**Required before production:** managed KMS/HSM-backed envelope encryption, key rotation, key-version metadata, secure key backup, decryption access control, and an explicit migration/re-encryption procedure.

### 2. Malware scanning

Scanning is opt-in and unavailable by default. The ClamAV adapter is not a verified live service. If scanning is required, uploads must remain unavailable until a clean result is recorded.

**Required before production:** deployed scanner, health monitoring, antivirus signature updates, bounded queues, quarantine retention, retry policy, and periodic scans.

### 3. PostgreSQL operations

The Compose configuration includes PostgreSQL and persistent volumes, but no restore test, backup procedure, migration rollback rehearsal, or RLS strategy is verified.

**Required:** tested pg_dump/base-backup recovery, restore to a fresh database, migration downgrade/upgrade rehearsal, backup encryption, retention, and restore-time recovery objectives.

### 4. External integrations

HAPI, Keycloak, Fabric, and ClamAV are documented and partially implemented but are not live-verification results. Direct FHIR endpoints must remain secondary to backend authorization.

**Required:** isolated live HAPI CRUD/search/version tests, real browser Keycloak flow, Fabric transaction confirmation and duplicate delivery tests, and live ClamAV scanning.

### 5. Worker reliability

Two in-process workers exist for FHIR and Fabric when enabled. There is retry/backoff state, but no dedicated worker deployment, distributed lock/lease model, dead-letter operation, queue depth monitoring, or multi-instance leader strategy is verified.

**Required:** separate worker service/process, durable startup scheduling, metrics, alerting, duplicate protection, and restart/crash drills.

### 6. Audit and historical integrity

Audit entry #33 is known to be historically inconsistent. It remains untouched. A global audit verification may report failure beginning at that historical entry, so monitoring must distinguish the known baseline without modifying the row.

**Required:** an append-only integrity policy, external archival/export, monitoring that excludes no unknown records, and documented incident handling for a new mismatch.

### 7. Secrets and configuration

JWT production startup rejects known weak secrets. Database, FHIR bearer token, Fabric token, pseudonym key, encryption key, scanner settings, and CORS origin are environment driven.

**Required:** a secrets manager, secret rotation, startup validation, separation of build/runtime secrets, and deployment-specific `.env` access control.

### 8. Frontend deployment

Node/npm were unavailable in the latest validation environment. Static editor diagnostics passed, but no production build or browser acceptance test proves routing, payload serialization, or UX behavior in a deployed browser.

**Required:** CI build, browser smoke tests, accessibility checks, and artifact signing/promotion.

## Security priorities

1. Deploy PostgreSQL and exercise backup/restore before clinical use.
2. Enable and protect managed encryption keys; define legacy-file migration.
3. Deploy ClamAV or another approved scanner and fail closed.
4. Live-test Keycloak issuer/audience/subject/role mapping.
5. Live-test HAPI references, validation, duplicate processing, and recovery.
6. Live-test Fabric transaction confirmation and duplicate delivery.
7. Add monitoring, audit export, alerting, and incident response.
8. Verify frontend build and browser flows.
9. Conduct a third-party privacy/security review.

## Current readiness verdict

| Category | Verdict |
|---|---|
| Local API/security functionality | Strong prototype evidence |
| SQLite migrations | Passed |
| PostgreSQL migrations | Not verified |
| Live HAPI | Not verified |
| Live Fabric | Not verified |
| Live ClamAV | Not verified |
| Key management | Prototype only |
| Frontend build/browser | Not verified |
| Production deployment | Not ready |
