# HealthHarbor — Deployment Architecture

## Source of truth

HealthHarbor has one application database that remains authoritative for authentication mapping, provider verification, organization approval, affiliations, consent, request state, document ownership, and clinical workflow state.

HAPI FHIR is an interoperability mirror, not an authorization engine. Fabric is a tamper-evident metadata/transaction outbox, not authorization or clinical storage.

## Local development

### Minimum services

- React/Vite frontend
- FastAPI backend
- SQLite database
- Local private file directory
- Optional local/mock FHIR mode
- Optional local/mock scanner
- Optional local/mock Fabric outbox

### Configuration

- `APP_ENV=development`
- `DATABASE_URL=sqlite:///...` or a disposable SQLite file
- `AUTH_PROVIDER=local` (development) or explicit Keycloak issuer/JWKS/audience (production)
- `FHIR_MODE=local`
- `FABRIC_ENABLED=false`
- `FILE_STORAGE_PATH` pointing outside publicly served frontend directories
- `DOCUMENT_ENCRYPTION_REQUIRED=false|true` (production requires `true`)
- `DOCUMENT_ENCRYPTION_KEY` only when encryption is required
- `DOCUMENT_SCAN_REQUIRED=false|true` (production requires `true` with ClamAV)
- `DOCUMENT_SCANNER=unavailable|clamav`

Use synthetic accounts and test data only.

## Demonstration environment

Recommended isolated services:

- PostgreSQL in a disposable project/Compose network
- FastAPI backend
- React frontend served by Vite or a static web server
- HAPI FHIR R4 if live interoperability is part of the demonstration
- Keycloak if OIDC behavior is demonstrated
- Optional ClamAV
- Optional Fabric test network
- Separate persistent volumes for PostgreSQL and clinical files

Demonstration data must be synthetic. External services should use isolated credentials and a separately named database.

Never point migration or reset commands at the developer's existing PostgreSQL database.

## Production architecture

```text
Browser / Mobile
  |
  v
TLS Reverse Proxy / WAF
  |
  +--> Static Frontend CDN or Web Tier
  |
  +--> API Load Balancer
          |
          +--> FastAPI API replicas
          |       +--> PostgreSQL primary/replicas
          |       +--> Private encrypted object/file storage
          |       +--> KMS/HSM
          |       +--> Malware scanner service
          |       +--> HAPI FHIR R4
          |       +--> FHIR sync worker replicas
          |       +--> Fabric gateway worker replicas
          |
          +--> Keycloak / IdP

PostgreSQL, file storage, HAPI, scanner, KMS, and ledger components
must use private networks and least-privilege identities.
```

### Required components

1. **Reverse proxy/WAF:** TLS termination, request limits, headers, and IP controls.
2. **Frontend:** static build served separately from API and file storage.
3. **API replicas:** stateless FastAPI instances using the same database, key provider, and service configuration.
4. **PostgreSQL:** primary and tested backup/restore; application user separate from migration/administrative user.
5. **Object storage:** private encrypted clinical storage or volume with encryption, backup, retention and malware scanning.
6. **Key management:** managed envelope-encryption keys, not environment plaintext for the default production mode.
7. **Scanner service:** isolated ClamAV or equivalent with clean/malicious/unavailable states.
8. **HAPI FHIR:** private network, authenticated clients, R4 validation, reference checks and reconciliation.
9. **Fabric:** permissioned network, gateway identities, transaction confirmation and pseudonymous event payloads.
10. **Workers:** independent FHIR and Fabric workers with bounded retries and dead-letter/failed-state handling.
11. **Observability:** structured logs, metrics, traces, health/readiness endpoints, backup monitoring and alerting.

## Health and readiness

- `/health/live` confirms only that the application process is alive.
- `/health/ready` verifies database readiness and reports configuration/readiness
  state for HAPI, encryption, scanner, and Fabric components.
- Readiness responses contain component booleans only; they do not print URLs,
  credentials, key material or database connection strings.
- Load balancers should use liveness/readiness separately and should not expose
  readiness JSON to public users.

Production startup additionally rejects insecure database, CORS, trusted-host,
key, scanner, authentication, HAPI and Fabric configuration combinations.

## Network isolation

- Public exposure limited to frontend and API reverse proxy.
- PostgreSQL, HAPI, scanner, KMS, Fabric peers/gateway, and worker services are private.
- Clinical file storage is not served by static frontend paths or permanent share links.
- API and worker identities use short-lived credentials or externally managed secrets.
- Admin FHIR endpoints must not be public.

## Database migration deployment

1. Take a verified backup.
2. Run migrations with a dedicated migration identity.
3. Start a new application image only after migration success.
4. Verify health/readiness and smoke authorization.
5. Keep rollback SQL and old-image compatibility documented.
6. Never run destructive downgrade or reset operations in production without an incident plan.

## Service configuration

Required deployment settings include:

- `APP_ENV=production`
- `JWT_SECRET` unique, >=32 characters
- PostgreSQL application and migration identities
- `CORS_ORIGINS` restricted to deployed frontend origins
- `DOCUMENT_ENCRYPTION_REQUIRED=true`
- Managed `DOCUMENT_ENCRYPTION_KEY` delivery or a future KMS-backed provider
- `DOCUMENT_SCAN_REQUIRED=true`
- real scanner adapter/configuration
- HAPI URL and bearer/token configuration only if HAPI is deployed
- Fabric configuration and pseudonym key only if Fabric is deployed
- no development seed credentials in the long-running API process

## Readiness boundary

This architecture is a proposed deployment topology. No Docker Compose network, PostgreSQL migration, HAPI instance, Fabric network, or browser deployment was verified in this assessment.
