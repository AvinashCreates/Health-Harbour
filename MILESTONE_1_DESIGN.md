# HealthHarbor — Milestone 1 Domain and Architecture Design

**Status: proposed for product-owner review.** This document fulfills the
current master prompt's Milestone 1 starting instruction. It is design only:
no application code, schema, migration, API route, or frontend workflow was
added for this proposal. Do not start Milestones 2–9 until this design and its
open policy decisions have been reviewed.

## 1. Current architecture assessment

HealthHarbor is a centralized FastAPI service with SQLAlchemy domain and
authorization data in PostgreSQL, optional HAPI FHIR R4 integration, Keycloak /
OIDC authentication, a React/Vite client, and an asynchronous Fabric
transactional outbox/Gateway path. PostgreSQL application policy remains the
authorization source of truth; neither a FHIR Consent nor frontend visibility
is sufficient to authorize a request.

Existing reusable capabilities:

- `User` provides an account, Keycloak subject, single role, and optional FHIR
  resource pointer. Public registration is patient-only; staff and
  organization-like accounts are administrator provisioned.
- `OrganizationMembership` links a doctor `User` and lab `User`, but records
  only active/inactive and creation time. It is not a verified, independently
  governed employment relationship.
- `Consent` stores patient, physician grantee, optional organization,
  resource-type JSON, purpose, validity and revocation. Shared consent
  predicates enforce expiry, revocation and active membership.
- `FHIRResource` stores generic R4 JSON and local owner/creator indexes.
  `LaboratoryWorkflow`, `WorkflowTransition` and `IdempotencyRecord` support
  the existing laboratory lifecycle.
- `ClinicalFile` is the current document metadata record: patient, uploader,
  optional workflow, category, storage key, media type, size, SHA-256,
  timestamps and soft-delete. Bytes currently use a configured local path.
  Encryption, storage abstraction, immutable versions, source-organization
  attribution and scan/quarantine states are not modeled.
- Existing routers cover authentication/provisioning, consent, files,
  laboratory/FHIR workflows, audit and ledger status. Provider and laboratory
  directories are role-based lists, not verified searchable registries.
- React has patient, doctor, laboratory/technician and platform-admin areas.
  Organization onboarding/admin, provider verification, patient-provider
  relationships, referrals, and document access requests are absent.

Key constraints:

1. Do not continue treating a `User` row as an organization or proof of
   professional eligibility.
2. Keep patient consent separate from a patient-provider relationship.
3. Keep FHIR JSON as an interoperability representation, not the source of
   approval, membership or authorization decisions.
4. Preserve laboratory workflows, the existing audit format, PostgreSQL
   `READ COMMITTED` application-engine setting and advisory lock.
5. Entry #33 in the existing project audit history is historical and strictly
   out of scope.
6. Current test evidence includes isolated backend, frontend build, Go module,
   SQLite and disposable PostgreSQL checks. HAPI metadata/readiness returned
   HTTP 200; live clinical CRUD, Keycloak browser authentication and Fabric
   commit were not verified.

## 2. Existing-to-new domain mapping

| Existing concept | Target responsibility | Proposed evolution |
|---|---|---|
| `User` | Authentication principal and personal account | Retain account and Keycloak subject. Stop using it as organization or provider-eligibility evidence. |
| `User.role` | Legacy platform role | Retain during compatibility rollout. Add persisted organization-scoped role assignments; never authorize from client-supplied role or organization IDs. |
| `FHIRResource` | FHIR mirror/index and FHIR identifiers | Retain; link to domain profile IDs. Domain records govern approvals, membership and consent. |
| Lab-role `User` | Healthcare organization | Add `HealthcareOrganization`; map legacy organization user via a unique nullable legacy ID and preserve current FHIR identifiers. |
| `OrganizationMembership` | Employment/affiliation membership | Evolve to provider-profile + organization references, scoped role, status, effective dates, decision actor/time and history. Preserve legacy columns through rollout. |
| `LaboratoryMembership` | Lab workflow technician assignment | Retain for current workflow compatibility; link or consolidate into organization-scoped role only after parity tests. |
| Doctor-role `User` | Professional identity | Link the account to one `HealthcareProvider` profile independent of employer. Legacy accounts are not automatically verified. |
| `Consent` | Patient's final, revocable authorization | Retain as authoritative grant. Normalize resource/category scope into child rows and backfill existing resource-type JSON. |
| `ClinicalFile` | Document metadata/catalog | Evolve in place or through a staged replacement. Add issuer organization, FHIR DocumentReference ID, status, storage backend/key, encryption reference, provenance and version lineage. |
| Local file key | Physical storage location | Put behind a `DocumentStorage` interface. Keep opaque storage keys; start with encrypted local storage and allow a future object/hospital-controlled adapter. |
| Workflow, transitions, idempotency | Existing lab lifecycle | Retain; link participants to canonical patient/provider/organization records without replacing the state machine. |
| `AuditLog` / `LedgerOutbox` | Application accountability / selected external proofs | Retain. Fabric payloads remain allowlisted, pseudonymous and free of clinical content. |

Use the existing patient account ID as the initial canonical patient identity.
Do not merge patients through matching names, email, phone, or an unverified
national ID. Cross-organization identity linking needs an authenticated,
explicitly reviewed workflow; external authoritative identity integrations
are future adapters, not capabilities to claim now.

## 3. Proposed entity relationships

```text
User 1 ── 0..1 PatientProfile
User 1 ── 0..1 HealthcareProvider
User 1 ── 0..* RoleAssignment ── 0..1 HealthcareOrganization

HealthcareOrganization 1 ── 0..* OrganizationApplication
HealthcareProvider 1 ── 0..* ProviderApplication
HealthcareProvider 1 ── 0..* ProviderVerification
HealthcareOrganization 1 ── 0..* OrganizationMembership

PatientProfile 1 ── 0..* PatientProviderRelationship
HealthcareProvider 1 ── 0..* PatientProviderRelationship
PatientProviderRelationship 1 ── 0..* Referral

PatientProfile 1 ── 0..* Consent
Consent 1 ── 1..* ConsentResource
PatientProfile 1 ── 0..* ClinicalFile
ClinicalFile 1 ── 1..* DocumentVersion
ClinicalFile 1 ── 0..* DocumentAccessRequest
DocumentAccessRequest ── 0..1 Consent (created on patient approval)
ClinicalFile 1 ── 0..* FHIR DocumentReference / Provenance links
```

Recommended domain records and constraints:

- **HealthcareOrganization**: UUID, legal name, type, registration authority
  and identifier, address/contact fields, status (`PENDING`,
  `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `SUSPENDED`), review metadata,
  timestamps, optional FHIR Organization ID and nullable unique
  `legacy_user_id` during migration. Directory responses expose only
  deliberately public fields.
- **HealthcareProvider**: UUID, unique account FK, professional name,
  registration authority/number, qualifications, specialization, directory
  fields, platform eligibility state and timestamps. Enforce uniqueness on
  authority + normalized registration number when supplied. Submitted
  credentials remain unverified until documented human review or a real
  authoritative integration has run.
- **OrganizationApplication / ProviderApplication**: applicant, submitted
  fields, status, reviewer, decision/reason, timestamps and private evidence
  references. Evidence bytes use the secure storage boundary; never present
  submissions as verified.
- **ProviderVerification**: provider, source/method, evidence reference or
  digest, decision, verifier, checked/expiry and revocation metadata. Platform
  eligibility is separate from each hospital's affiliation approval.
- **OrganizationMembership**: organization FK, provider/account FK,
  organization-scoped role, status (`INVITED`, `PENDING`, `ACTIVE`,
  `SUSPENDED`, `ENDED`), effective dates and decision actors/timestamps.
  Preserve membership history; ending one hospital affiliation does not
  suspend the provider or other affiliations.
- **RoleAssignment**: user FK, role code, optional organization FK, status and
  issuer. Platform admin is platform-scoped; organization admin, provider,
  lab supervisor and technician roles are scoped to a specific organization.
- **PatientProviderRelationship**: patient, provider and optional selected
  affiliation; initiator/reason; status (`REQUESTED`, `ACCEPTED`, `DECLINED`,
  `ACTIVE`, `CLOSED`); decision/close metadata. Prevent duplicate open requests.
  A relationship is not an access grant.
- **Referral**: patient, referring and receiving verified providers,
  source/target affiliations, purpose, status and timestamps. Referenced
  documents remain independently consent-controlled.
- **ConsentResource**: consent FK, FHIR resource type, optional exact resource
  ID and optional document category. Validate that scopes are explicit and
  within the patient's choice. Backfill existing `resource_types`; retain
  compatibility reads until parity is proven.
- **DocumentVersion**: document FK, immutable version number/storage key,
  SHA-256, byte length, detected media type, encryption-key version reference,
  uploader, source organization, scan state, timestamp and `supersedes` link.
  Never replace bytes in place.
- **DocumentAccessRequest**: patient, requesting verified provider and active
  membership, relationship, requested resources/categories, purpose, status
  (`PENDING`, `APPROVED`, `DECLINED`, `CANCELLED`, `EXPIRED`), expiry and
  decision metadata. Approval creates a bounded Consent and scope rows.

Use opaque IDs, foreign keys, indexes, bounded status values, and auditable
actors/timestamps. Use UTC-aware application timestamps where compatible with
existing schema. Enforce tenant scope in service queries and authorization,
not by trusting request-body organization IDs.

## 4. Provider onboarding sequence

1. Applicant authenticates through the configured identity provider and
   submits an application tied to their validated identity subject.
2. API links or creates a non-privileged account and pending provider profile.
   Public registration cannot self-select doctor/admin/organization roles.
3. Applicant supplies registration authority/number, qualifications and
   evidence. Evidence is stored privately with a digest; no external
   registration lookup is claimed unless actually integrated.
4. Platform reviewer records a verification method/source, reviewer, decision
   and time; application may be rejected or returned for more information.
   Platform approval enables professional eligibility only, not employment.
5. A selected approved organization receives an affiliation request. Its
   organization admin approves/rejects only its own affiliation.
6. Exchange privileges require both platform eligibility and at least one
   active organization membership. Recheck mutable status from the database
   for each sensitive request.
7. Additional hospitals add memberships to the same provider profile.
   Suspending one membership affects only that organization.
8. Audit application, evidence access, verification and lifecycle decisions;
   never place credentials or evidence contents in audit/Fabric payloads.

## 5. Organization onboarding sequence

1. Authenticated representative submits legal identity, type, registration,
   address and administrative contact. The application is pending and has no
   exchange privileges.
2. Platform operations validate submitted evidence through a recorded human
   workflow or explicitly configured authoritative adapter. Pending records
   are absent from verified directory search.
3. Reviewer records `UNDER_REVIEW` then `APPROVED` or `REJECTED`, actor, time
   and reason. Later suspension revokes exchange eligibility without deleting
   history.
4. On approval, create/activate the organization and assign an authorized
   representative as its organization admin. Client fields cannot grant
   organization roles.
5. Organization admins invite/manage staff only within their organization.
   Provider eligibility remains independently reviewed at platform level.
6. Only approved active organizations and eligible providers are discoverable.
   Suspension immediately affects new exchange access and document retrieval.

## 6. Patient-provider relationship sequence

1. Patient searches active verified providers and approved organizations using
   paginated directory APIs.
2. Patient reviews a safe public profile, selects a provider and (when
   relevant) a specific active affiliation, then submits a minimal-purpose
   relationship/consultation request.
3. API verifies patient self-identity, platform eligibility, organization
   approval and active membership. The request creates no clinical permission.
4. Provider or explicitly delegated staff accepts/declines. Acceptance records
   care context only; it does not grant records.
5. Provider may request specific documents/categories and purpose. Patient
   separately approves or declines. Approval issues scoped, expiring,
   revocable Consent and a FHIR Consent representation.
6. Closing the relationship stops future relationship-dependent requests.
   Existing consent remains governed by its explicit scope/expiry/revocation;
   the patient can always revoke. Whether closing automatically revokes
   relationship-derived grants requires product-owner decision before coding.
7. Referral is a separate workflow between verified providers and never
   bypasses patient authorization for referenced records.

## 7. Cross-organization document-sharing sequence

1. Active provider uploads a document for a patient only under an active
   organization membership and permitted workflow. API verifies patient
   association, category, size, content signature and detected media type;
   filename/path never controls storage location.
2. New bytes enter quarantine, optional content scanning and an
   encryption-capable `DocumentStorage` adapter. Only validated/approved
   content becomes retrievable. Hash original bytes; keep storage key and key
   reference opaque; encryption key material is outside PostgreSQL.
3. Persist metadata, immutable version, uploader, issuing organization,
   hash, status and provenance. Create an R4 DocumentReference that points to
   an authenticated HealthHarbor content route, not a public URL or
   unrestricted FHIR Binary.
4. Patient chooses exact documents or categories, recipient provider/org,
   purpose and expiry. A provider request can propose scopes but cannot
   approve itself.
5. Patient approval creates Consent and normalized exact resource/document
   scopes. Relationship or organization membership alone is never sufficient.
6. On every retrieval, backend verifies authenticated identity, provider
   eligibility, active selected membership, relationship policy, patient
   identity, exact consent/scope, expiry, revocation and document status before
   retrieving/decrypting inside the service/storage trust boundary.
7. Stream with `Cache-Control: no-store`, safe content disposition and opaque
   IDs. Audit access with a defined delivery transaction policy. Revocation
   blocks subsequent downloads; it cannot erase already downloaded copies.
8. Replacement creates a new immutable version with supersession provenance.
   Never silently overwrite; current authorization applies to every version.

## 8. API contract proposal

Introduce `/api/v1` for new registry and exchange APIs; keep existing
unversioned routes during a compatibility rollout. Use Pydantic DTOs, stable
error codes, server-derived tenant identity, cursor pagination, validated
filters, idempotency keys for retryable creates, OpenAPI documentation and
audited security-relevant transitions. Do not expose ORM models directly.

| Method / route | Purpose and authorization |
|---|---|
| `POST /api/v1/organization-applications`; `GET .../me` | Authenticated representative applies and reads own safe status. |
| `GET /api/v1/admin/organization-applications`; `POST .../{id}/decision` | Platform admin reviews/decides with reason and reviewer metadata. |
| `GET /api/v1/organizations`; `GET .../{id}` | Public-safe directory of approved, active organizations only. |
| `POST /api/v1/provider-applications`; `GET .../me` | Authenticated applicant submits/reads own application; never self-activates. |
| `GET /api/v1/admin/provider-applications`; `POST .../{id}/decision` | Platform admin records evidence-backed eligibility decision. |
| `POST /api/v1/organizations/{org_id}/membership-invitations` | Organization admin invites staff/provider to own organization. |
| `GET /api/v1/organizations/{org_id}/memberships`; `POST .../{id}/decision` | Scoped org admin lists and decides only memberships in its tenant. |
| `GET /api/v1/providers`; `GET .../{id}` | Patient directory search/profile of active eligible providers and affiliations. |
| `POST /api/v1/patients/me/relationships`; `GET .../relationships` | Patient initiates and lists own relationships. |
| `GET /api/v1/providers/me/relationships`; `POST /api/v1/relationships/{id}/decision`; `POST .../{id}/close` | Provider lists own requests and authorized parties decide/close them. |
| `POST /api/v1/patients/{patient_id}/referrals` | Verified active provider creates referral; attached records need separate authorization. |
| `GET /api/v1/patients/me/documents` | Patient lists metadata only. |
| `POST /api/v1/organizations/{org_id}/patients/{patient_id}/documents` | Active affiliated provider uploads through validation/quarantine/storage service. |
| `POST /api/v1/patients/{patient_id}/document-access-requests`; `GET ...` | Provider requests explicit scope; only patient/requesting provider sees the request. |
| `POST /api/v1/patients/me/document-access-requests/{id}/decision` | Patient grants bounded scopes/expiry or declines; approval creates consent. |
| `GET /api/v1/documents/{id}/content` | Authenticated stream, with fresh eligibility, tenant, relationship and consent checks. |
| `POST /api/v1/consents/{id}/revoke`; `GET /api/v1/patients/me/access-history` | Patient revokes future access and inspects own history. |
| FHIR metadata and organization-authenticated exchange endpoints | Add only after server-to-server identity, scope and FHIR contracts are approved. |

Future server-to-server integration should bind OAuth2 client credentials or
mutual-TLS credentials to one approved organization, with rotation, revocation,
rate limits and least-privilege scopes. Organization identity must come from
validated credentials, never a request-body `organization_id`. Do not build
these endpoints until their threat model and consent behavior are reviewed.

## 9. Security and authorization matrix

| Principal | Registry / administration | Relationships / referrals | Clinical records |
|---|---|---|---|
| Patient | Self only | Own requests; decide access requests; close relationships; revoke own grants | Own documents; explicit resource/category grants; own access history. |
| Platform administrator | Review applications and platform eligibility; no implicit organization membership | No routine relationship access | No clinical content by default; minimum necessary audited administrative metadata only. |
| Organization administrator | Only own approved organization's profile and scoped staff/memberships | Only if explicitly delegated; cannot impersonate provider decisions by default | No patient content by virtue of admin role. |
| Verified provider | Own profile and active organization memberships | Own requests, relationships and referrals | Requires active platform eligibility, selected active membership, any required relationship, and active consent for exact resource/category. |
| Lab supervisor | Own approved lab and lab-scoped role | No general provider authority | Existing lab workflow scope only; consent/workflow rules still apply. |
| Lab technician | Own active lab membership/assignment | None | Assigned request/specimen/report workflow only. |
| Pending/suspended provider | Own application status only | Cannot create exchange relationships/referrals | No exchange access, regardless of stale JWT role. |
| External hospital system | One approved organization-bound client identity | Only approved organization workflows | Same patient identity and exact consent/resource rules; no caller-chosen cross-tenant IDs. |

For each sensitive request validate the token, then load current account,
verification, organization, membership, relationship, consent and document
state from trusted persistence. Mutable eligibility must not rely on token
claims. Required negative tests: no-consent cross-hospital access;
expired/revoked/out-of-scope grants; suspended provider; ended membership;
cross-lab technician; cross-patient read; cross-org administration; guessed
document ID; and pending organization/provider directory exclusion. Use
non-disclosing errors for opaque document IDs and audit denied sensitive
operations without leaking patient detail.

## 10. Incremental implementation plan

| Milestone | Scope and exit evidence |
|---|---|
| 1 — Architecture/domain (this proposal) | Review domain, lifecycle, migration compatibility, API and authorization matrix. **No code until reviewed.** |
| 2 — Organization/provider registry | Additive schema and controlled applications/approvals; map legacy accounts explicitly; test lifecycle, directory eligibility and tenant boundaries. |
| 3 — Patient-provider relationships | Add relationship/referral lifecycles; prove relationship does not authorize records; test multiple affiliations and lifecycle denial. |
| 4 — Secure document exchange | Storage adapter, encryption/key boundary, validation/quarantine, immutable versions/provenance, exact-scope requests and retrieval; test cross-tenant denial, revocation and guessed IDs. |
| 5 — FHIR interoperability | Map domain IDs to Practitioner/PractitionerRole/Organization/Consent/DocumentReference/Provenance; test actual disposable HAPI round trips; API remains authorization authority. |
| 6 — Hospital integration API | Versioned server-to-server authentication and org-bound scopes; test isolation without exposing database models. |
| 7 — Audit/Fabric | Privacy-reviewed event allowlist, transactional outbox and actual commit evidence; preserve hash format, advisory lock and `READ COMMITTED` fix. |
| 8 — Frontend | Patient discovery/relationship/consent/document flows, provider portal, organization portal, platform registry administration and lab continuity; accessibility and end-to-end checks. |
| 9 — System verification | Disposable PostgreSQL/HAPI/Keycloak/Fabric acceptance environment, negative authorization matrix, migration rehearsal/restore, ZAP and measured k6 results; document blockers honestly. |

Migration safeguards:

1. Add tables/nullable bridge columns first; never drop/rename legacy columns
   while old application code can run.
2. Map legacy organization/provider accounts deterministically and
   reviewably. Preserve FHIR IDs, memberships, consents, files, workflows and
   audit rows. A legacy role does not imply verified credentials or an
   approved organization.
3. Backfill normalized consent scope rows and compare counts/scope semantics
   on a disposable copy before dual-read/write rollout.
4. Switch API consumers only after compatibility and consistency checks pass.
   Keep rollback additive; do not delete legacy data in the migration.
5. Test each migration on fresh SQLite, disposable PostgreSQL and a synthetic
   copy with representative existing rows. Never rehearse against the project
   PostgreSQL database.
6. Re-encrypt/version existing files only in a separate controlled operation
   with backup, integrity verification and rollback; schema migration must
   never silently rewrite file bytes.

### Product-owner decisions needed before Milestone 2

1. Relationship closure does not automatically revoke an already granted
   consent; explicit revocation/expiry is the proposed default.
2. Platform professional verification and organization affiliation approval
   are independent gates before provider exchange privileges.
3. Organization administrators do not accept/decline consultations for a
   provider unless an explicit delegation policy is approved.
4. Confirm initial organization types and document category vocabulary.
5. Confirm document encryption key management (deployment KMS vs. locally
   supplied key outside PostgreSQL) and fail-closed behavior when scanning is
   unavailable.

Do not claim legal, Indian professional registry, or ABDM compliance without
the required validation and integrations.
