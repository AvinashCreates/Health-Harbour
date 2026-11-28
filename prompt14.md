# HealthHarbor — Milestone 9.1: Critical Security and Configuration Hardening

Repository:
`/home/pamarthi-avinash/Downloads/healthcare-exchange`

Read these documents first:
- `PRODUCTION_READINESS.md`
- `DEPLOYMENT_ARCHITECTURE.md`
- `OPERATIONS_RUNBOOK.md`

## Objective

Address the highest-priority security and configuration weaknesses identified in the production-readiness assessment.

This is a focused implementation task. Do not redesign the architecture or introduce large infrastructure dependencies.

## Phase 1 — Verify the assessment

Inspect the actual code corresponding to every critical and high-priority finding.

Do not blindly trust documentation. Confirm each finding against the current implementation.

Classify each as:
- Confirmed vulnerability
- Configuration weakness
- Operational gap
- Already addressed
- Requires live infrastructure verification

## Phase 2 — Secrets and configuration

Review:
- JWT signing secrets
- Application environment configuration
- Database connection configuration
- Keycloak configuration
- FHIR credentials
- Fabric credentials
- File-storage paths
- Development versus production defaults

Requirements:
- Never expose secrets in logs or error responses.
- Production must reject insecure default secrets.
- Development mode must remain usable.
- Missing mandatory production configuration must fail clearly at startup.
- Never print actual secret values.

Do not change authentication behavior without examining existing tests.

## Phase 3 — CORS and API security

Review:
- CORS origins
- Allowed methods and headers
- Trusted host configuration
- Authentication requirements
- Rate limiting
- Error responses
- Sensitive information in logs

Apply only justified changes.

Do not use wildcard origins in production configurations.

## Phase 4 — File storage

Review:
- Upload validation
- Filename handling
- Path traversal protection
- Storage permissions
- Download authorization
- Scanner failure behavior
- File access after consent revocation

Do not weaken any existing authorization checks.

Do not claim malware protection is live when ClamAV is unavailable.

## Phase 5 — Operational readiness

Inspect existing health endpoints and identify whether they distinguish:
- Application process health
- Database readiness
- FHIR connectivity
- Blockchain gateway connectivity
- File scanning availability

Implement lightweight health/readiness improvements only where appropriate.

Do not expose sensitive infrastructure details publicly.

## Phase 6 — Validation

Run:
- Relevant security tests
- API smoke tests
- Python compilation
- `git diff --check`
- Isolated SQLite migration tests where dependencies are available
- Unsuppressed `alembic heads` and `alembic current` checks

Never use the existing PostgreSQL database for experiments.

Do not install Docker, PostgreSQL, Keycloak, HAPI or Fabric.

## Strict constraints

- Preserve user changes.
- Never run `git reset --hard` or `git clean`.
- Do not commit.
- Never modify historical audit entry #33.
- Never rewrite or re-hash historical audit records.
- Never place clinical data on the blockchain.
- Use synthetic data only.
- Do not weaken consent or organization authorization.
- Do not claim live verification without evidence.

## Final report

Report:
1. Confirmed security weaknesses.
2. Changes implemented.
3. Files modified.
4. Exact test results.
5. Remaining risks.
6. Configuration required for production.
7. Issues requiring live infrastructure.
8. Updated production-readiness verdict.

Distinguish locally tested, mocked, live verified and not verified.