# Completion roadmap

This roadmap is evidence-based and preserves the phase ordering in
`prompt.md`. No external integration is considered complete based on a mock.

| Phase | Current state | Remaining acceptance work |
|---|---|---|
| 0 — Repository inspection | In progress / documented | Finish integration and test inventory; retain the existing uncommitted changes. |
| 1 — Application stability | Partially verified | The supplied browser tab reported Vite connection refusal. Start the Vite process and re-check browser login/workspaces. Re-run service checks on the user's Compose runtime. |
| 2 — Database and migrations | Full SQLite chain verified | Back up PostgreSQL and file storage, then apply revisions `71b6c4a2d9e1` and `8c41d6a2f705` to an isolated restore first; verify PostgreSQL compatibility and safe rollback before touching deployment data. |
| 3 — Keycloak | Code and signed-token tests exist | Import/use the existing realm and verify browser PKCE login, verified patient provisioning, role mapping, refresh, logout, disabled accounts, and expired tokens. |
| 4 — HAPI R4 | Code and readiness verified previously | Against the user's live HAPI: create, `$validate`, read, versioned update, reference failure, and restart persistence for each supported resource, including organization Consent and DocumentReference. |
| 5 — Consent and authorization | Isolated SQLite tests pass | Test expired, revoked, wrong-scope, wrong-recipient, membership removal, and organization purpose cases against PostgreSQL/HAPI; verify no organization-wide implied access. |
| 6 — Fabric | Source/Go tests documented; live status unknown | Requires Go, Docker, the Fabric test network, credentials held locally, both-organization endorsement, confirmed transaction IDs, retries, duplicates, and Gateway outage recovery. |
| 7 — Clinical workflow | Local API smoke flow passes | Repeat the complete role workflow against HAPI and PostgreSQL; verify each resource and transition after retrieval and service restart. |
| 8 — File security | Isolated API tests cover access and validation | Verify Compose volume restart persistence and HAPI DocumentReference operations; perform safe synthetic traversal/size/content checks. |
| 9 — Security | Four source findings remediated and regression-tested | Review legacy seeded accounts, verify the shared limiter on PostgreSQL, then run loopback-only ZAP against a live local stack. |
| 10 — Performance | Runner exists; no current benchmark | Run k6 against a controlled loopback deployment, record full workload/configuration/latencies/error rate, and avoid extrapolating smoke tests. |
| 11 — Backup/recovery | Not yet exercised | Back up databases and file volume, verify the artifacts, restore to isolated destinations, check schema/connectivity, and document evidence. Never overwrite live volumes. |
| 12 — Frontend | Role workspaces implemented; build unavailable here | Start Vite, test each role workspace and error/empty/loading states in browser, then run `npm ci` and `npm run build`. |

## Immediate sequence

1. Keep the existing PostgreSQL data untouched. Obtain and verify a backup
   before any PostgreSQL migration attempt.
2. Restore that backup to an isolated database and test the new migration
   there; separately verify file-volume backup and restoration.
3. Start the local Vite process and validate the patient/admin organization
   membership and named-consent flow in the browser.
4. With the user's Docker/Go environment available, complete HAPI and Fabric
   real-service acceptance tests.
5. Run ZAP and k6 only against loopback services and record actual results.

## Deferred audit item

Historical audit-chain mismatch investigation deferred to a separate maintenance task. Historical records remain preserved and unchanged. New audit events and concurrency protections may still be tested without editing the historical chain.
