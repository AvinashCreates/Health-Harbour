# HealthHarbor: Current Status and Future Plan

This document records the project status evidenced as of 2026-11-25 and lays
out a staged plan to close the gaps against [abstract.md](./abstract.md).
Statuses distinguish implemented code from behavior verified against running
services. Do not treat this research prototype as a production clinical system.
Use synthetic identities and clinical data only.

## Current project status

### Implemented application capabilities

- React workspaces for patients, physicians, laboratory supervisors and
  technicians, and administrators.
- FastAPI authentication and role checks, scoped patient consent, consent
  expiry and revocation, access history, and a staged laboratory workflow.
- FHIR resource builders and API paths for patient, practitioner, service
  request, specimen, observation, diagnostic report, consent, and file metadata.
- Private off-chain file storage with consent/workflow-scoped access controls.
- Local hash-chained audit records and a Fabric outbox/adapter implementation.
- Optional Keycloak/OIDC, HAPI FHIR R4, and Hyperledger Fabric integrations.
- Automated backend tests, mocked integration tests, frontend build, and
  reproducible ZAP/k6 evaluation runners.

These features are present in code; the live-service evidence below is more
limited than the implementation list.

### Verified evidence

| Area | Evidence currently available | Status |
|---|---|---|
| Local API and security behavior | API and security test scripts passed against isolated SQLite databases. | Verified locally |
| Backend integration/file/audit tests | 16 unit tests passed; external OIDC, HAPI, and Fabric behaviors use mocks. | Verified locally; not live integration evidence |
| Frontend | Production build passed. | Verified locally |
| Database migrations | Fresh SQLite Alembic upgrade and `alembic check` passed. | Verified locally |
| PostgreSQL deployment | User-provided Compose output showed PostgreSQL healthy, backend running, and API health reporting database connected. | Verified on user's Arch Linux deployment |
| HAPI FHIR R4 | User-provided output showed HAPI 7.4.0 startup completed, PostgreSQL tables `bt2_job_instance`, `trm_concept`, and `hfj_search` present, metadata `CapabilityStatement` / FHIR `4.0.1`, and API health reporting `fhir: hapi`. | Startup and schema verified; resource operations not yet verified |
| Fabric source tests | User ran `go test ./...` successfully in both chaincode and adapter modules. | Unit tests verified; live ledger not verified |
| Performance runner | A three-request-per-phase smoke check validated the Python runner only. | Not a benchmark |

The user's deployment results are recorded in [result.md](./result.md). These
are user-provided terminal results, not tests run from this VS Code
environment.

### Known open issues and evidence gaps

- No application-level HAPI resource create/read/update or full clinical
  workflow has yet been shown against the running HAPI server.
- Keycloak browser login, logout, token refresh, patient registration, and
  staff provisioning have not been verified against a live realm.
- No live Fabric network commit has been demonstrated.
- OWASP ZAP has not been run on the current deployment.
- There are no current-stack, meaningful load/performance measurements.
- The admin dashboard previously reported a broken local hash chain beginning
  at audit entry #33. Preserve the warning and investigate without rewriting
  historical records.
- PostgreSQL backup/restore, service recovery, and deployment hardening have
  not been evaluated. Earlier Compose logs showed a temporary DNS resolution
  failure for `db`, though later health checks showed connectivity restored.

## Comparison with the abstract

| Abstract objective | Current position | Remaining work to substantiate the objective |
|---|---|---|
| Interoperable exchange between patients, physicians, and laboratories | Role-based UI and staged clinical workflow are implemented; API workflow tests passed locally. | Run the same workflows against PostgreSQL and HAPI, verify real FHIR references and persisted resources, and capture successful results. |
| Standard FHIR resources for requests, specimens, observations, reports, and consent | Resource builders and HAPI integration paths exist; HAPI R4 service/schema startup is verified. | Test create, read, update, and validation for the workflow resources against HAPI R4; verify references and response versions. |
| Fine-grained consent for a specific physician and selected resource scopes, up to 30 days, with expiry and revocation | Consent checks, 1–30 day duration, expiry, revocation, and local automated tests exist. | Demonstrate expiry and revocation in a deployed PostgreSQL/HAPI workflow, including denied access after each boundary. |
| Role-based least-privilege access | Backend authorization and ownership/workflow checks exist; automated role/security tests passed locally. | Execute a role-by-role authorization matrix on the deployed stack and retain expected allow/deny evidence. |
| Off-chain clinical data and permissioned ledger provenance | Private file storage, Fabric adapter/chaincode, and outbox code exist; Go unit tests passed. | Start a Fabric test network, submit a synthetic event, independently verify its committed transaction, and demonstrate that clinical data/identifiers are not written to the ledger. |
| Secure authentication | Local JWT flow is tested; Keycloak/OIDC configuration and verification code exist. | Complete live PKCE sign-in, refresh, logout, registration, and staff provisioning; verify invalid issuer/audience/signature/role tokens are rejected. |
| Functional and controlled penetration testing | Functional/security suites and a passive ZAP runner exist. | Run and review ZAP only against the controlled local deployment; document scope, findings, false positives, and remediation. A baseline scan is not a full penetration test. |
| Scalability and performance under increasing load | k6 ramping and Python read-load tools exist; only a tiny runner smoke check has been performed. | Run controlled, repeatable workloads and report environment, concurrency, duration, warm-up, p50/p95/p99 latency, throughput, errors, and resource use. |
| Evaluate unauthorized access, consent behavior, interoperability, auditability, latency, throughput, and ledger overhead | Tests and runners cover parts of the evaluation; no consolidated current-stack results exist. | Create a reproducible results set covering each metric and a matched ledger-off/ledger-on comparison. |

## Prioritized implementation and verification plan

### Phase 1 — Secure authentication

The local JWT and OIDC validation paths have received additional negative-test
coverage. Complete this phase by verifying the configured identity provider
against a live Keycloak realm:

1. Import or update the `healthharbor` realm and ensure localhost and
   `127.0.0.1` redirect/origin settings match the browser URL in use.
2. Test Authorization Code + PKCE, sign-out, token refresh/expiry, verified
   patient registration, and administrator-provisioned staff.
3. Verify invalid signature, issuer, audience, expiry, subject, and ambiguous
   role claims are rejected by the API.
4. Confirm profile linking uses the stable identity subject, not email alone.

**Exit criteria:** successful live browser flows and a recorded negative-token
test matrix using synthetic users. Until then, Keycloak remains implemented
but not live-verified.

### Phase 2 — Verify consent enforcement and FHIR interoperability

1. Exercise default-deny behavior for each role and protected resource/action.
2. Verify named physician, patient binding, resource scope, 1–30 day duration,
   automatic expiry, early revocation, access history, and denied access after
   each boundary.
3. Against HAPI R4, create, read, and update representative resources:
   `Patient`, `Practitioner`, `ServiceRequest`, `Specimen`, `Observation`,
   `DiagnosticReport`, and `Consent`.
4. Exercise `$validate`, conditional version updates, and resource references
   used by the application workflow.
5. Run the synthetic consent-to-laboratory workflow through report review and
   confirm expired/revoked access is denied.
6. Save concise command/API results and failures; do not publish PHI, tokens,
   or secrets.

**Exit criteria:** representative HAPI create/read/update/validation
operations pass, references resolve, and an authorized synthetic workflow
succeeds while out-of-scope, expired, and revoked access is denied.

### Phase 3 — Verify Fabric provenance end to end

1. Start a local Fabric test network and deploy the project chaincode.
2. Configure the adapter with the test identity, peer TLS certificate, and
   independently generated service/pseudonym keys.
3. Submit a synthetic consent or workflow event through the application
   outbox.
4. Confirm the adapter returns a committed transaction ID and independently
   query the ledger for the event.
5. Inspect the event to confirm it contains only the intended pseudonymous
   references and hashes, never clinical payloads or direct identifiers.
6. Test retry/idempotency and failure recovery while the Gateway is
   unavailable.

**Exit criteria:** a live event is independently visible on the test ledger,
retries do not create unintended duplicate events, and no PHI/PII is recorded.

### Phase 4 — Measure scalability and ledger overhead

1. Record software versions, hardware, Docker resource limits, database,
   enabled integrations, test data scale, workload, duration, and warm-up.
2. Use synthetic identities/data and increase load in controlled stages.
3. Measure p50/p95/p99 response time, throughput, error rate, and CPU/memory;
   include authenticated role-appropriate reads and relevant workflow writes.
4. Repeat comparable runs with Fabric delivery disabled and enabled, changing
   no other workload/configuration, and report submission latency separately
   from commit confirmation.
5. Keep runner smoke checks distinct from performance results. Do not reuse
   historical prototype figures as measurements for this revision.

**Exit criteria:** results are repeatable, have stated test conditions, and
include both successful and failed-request behavior without exposing tokens or
clinical data.

### Phase 5 — Run a controlled OWASP ZAP assessment

1. Run the ZAP baseline only against the controlled local deployment.
2. Triage each alert, distinguish confirmed issues from false positives, and
   record accepted risks and scoped remediations.
3. Rerun relevant tests and the baseline after fixes.
4. Investigate the existing broken audit-chain warning from entry #33 without
   changing historical records; document the root cause and resolution status.

**Exit criteria:** repeatable tests pass, unauthorized cases are denied, audit
integrity behavior is documented, and ZAP findings are reviewed rather than
reported as raw untriaged alerts. A baseline scan is not a full penetration
test.

### Phase 6 — Operational readiness and documentation

1. Verify PostgreSQL backup and restore, file-volume backup, startup ordering,
   and recovery after service interruption without deleting persistent data.
2. Verify the database-backed login rate limiter against PostgreSQL, including
   fail-closed behavior and cleanup under sustained load, before horizontal
   API scaling.
3. Review organization-level authorization, secrets management, encryption,
   logging/retention, file malware scanning, monitoring, and deployment
   access controls.
4. Update [PROJECT_STATUS.md](./PROJECT_STATUS.md) and
   [RESEARCH_EVALUATION.md](./RESEARCH_EVALUATION.md) with dated evidence,
   environment details, limitations, and outstanding work.

**Exit criteria:** operational procedures are tested and documented. Passing
this phase still does not make the prototype a certified or production-ready
clinical system.

## Recommended immediate next action

Continue **Phase 1** with live Keycloak PKCE, refresh, logout, and provisioning
verification. Local auth/OIDC negative tests pass, but the current workspace
does not have Docker or a responding local API, so live identity and HAPI
checks must be repeated when those services are available.

## Evidence and reporting rules

- Mark work “implemented” when code exists, and “verified” only when the
  corresponding test or live service result has been observed.
- Record the date, revision, commands/scenario, environment, outcomes, and
  unresolved failures for every evaluation.
- Do not describe a running container, healthy endpoint, mocked test, or
  runner smoke check as proof of end-to-end interoperability, penetration
  resistance, or scalability.
- Never include secrets, bearer tokens, private keys, or real patient data in
  this document or committed reports.
