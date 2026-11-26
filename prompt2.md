# HEALTHHARBOR — MASTER IMPLEMENTATION PROMPT
## Milestone 2: Verified Healthcare Organization & Provider Registry

You are working inside my existing HealthHarbor repository:

`/home/pamarthi-avinash/Downloads/healthcare-exchange`

Your task is to implement **Milestone 2: Healthcare Organization and Provider Registry**, following the architecture proposal in `MILESTONE_1_DESIGN.md`.

This is an existing final-year engineering project. Do not rebuild it from scratch, replace its architecture, or turn it into a generic hospital-management CRUD application.

---

## 1. Product vision and engineering philosophy

HealthHarbor is intended to become a secure, consent-aware healthcare interoperability platform.

Its purpose is to allow patients and verified healthcare professionals from different hospitals and laboratories to exchange relevant medical information securely, with patient authorization and accountability.

The long-term system must support:

- Patients discovering verified doctors and participating hospitals.
- Healthcare organizations joining the network through a controlled onboarding process.
- Doctors establishing verified professional identities.
- Doctors having separate, independently managed affiliations with multiple hospitals.
- Organization administrators managing their own organization's staff.
- Patients initiating healthcare relationships and controlling access to their records.
- Secure cross-organization exchange of prescriptions, laboratory reports, clinical documents, and other relevant records.
- FHIR R4 as the interoperability layer.
- Blockchain as a limited tamper-evident audit mechanism, not a storage location for clinical information.

The current milestone establishes the identity and organizational trust foundation for those capabilities.

**Build the foundation that makes the future exchange network trustworthy. Do not implement unrelated features just to increase the feature count.**

---

## 2. Mandatory repository inspection

Before changing anything:

1. Read `prompt.md` completely. Follow its existing instructions and project structure.
2. Read:
   - `MILESTONE_1_DESIGN.md`
   - `ARCHITECTURE_REVIEW.md`
   - `PROJECT_STATUS.md`
   - `IMPLEMENTATION_STATUS.md`
   - `SECURITY_ASSESSMENT.md`
   - `TESTING_REPORT.md`
   - `INTEGRATION_GUIDE.md`
   - `README.md`
3. Inspect the existing backend models, schemas, routers, services, migrations, tests, frontend components, API utilities, and authentication implementation.
4. Run `git status --short` and inspect existing changes before editing.
5. Identify the exact implementation dependencies and compatibility risks.

Do not assume that the architecture proposal perfectly matches every current source file. If you discover a conflict, document it and adapt the implementation without breaking existing behavior.

Preserve all existing user work and uncommitted changes.

---

## 3. Milestone scope

Implement only these capabilities:

### A. Healthcare organization registry

Introduce a proper healthcare organization domain entity.

An organization must have:

- Unique internal identifier.
- Legal/display name.
- Organization type.
- Registration authority and registration identifier, where applicable.
- Address and contact information.
- Application and verification status.
- Created and updated timestamps.
- Reviewer and decision metadata.
- Existing FHIR Organization linkage where appropriate.
- A compatibility mapping to legacy organization accounts where necessary.

Organization lifecycle:

`PENDING → UNDER_REVIEW → APPROVED / REJECTED`

Approved organizations may later become:

`SUSPENDED`

A pending or rejected organization must not receive healthcare exchange privileges.

Do not treat an ordinary user account as proof that a hospital is legitimate.

### B. Organization onboarding

Implement a controlled onboarding workflow.

1. An authenticated representative submits an organization application.
2. The application remains pending.
3. A platform administrator reviews the application.
4. The reviewer records a decision and reason.
5. Approval activates the organization.
6. The authorized representative receives organization-administrator privileges through a server-controlled assignment.
7. Organization administrators can manage only their own organization.

Do not allow public registration to assign platform-admin or organization-admin roles.

Do not claim external registration verification unless an actual integration or documented manual verification process has been performed.

### C. Healthcare provider registry

Introduce a healthcare provider profile independent of the login account.

A provider profile should support:

- Professional name.
- Professional registration authority.
- Registration number.
- Qualifications.
- Specialization.
- Public profile fields.
- Verification status.
- Verification evidence references.
- Review metadata.
- FHIR Practitioner linkage where appropriate.

Provider lifecycle:

`PENDING → UNDER_REVIEW → VERIFIED / REJECTED`

A verified provider may later become:

`SUSPENDED`

Important:

- An account with the role `doctor` is not automatically a verified provider.
- A submitted registration number is not proof of verification.
- Do not invent professional credentials.
- Do not claim integration with an official medical registry unless implemented and verified.
- Keep private verification evidence inaccessible to public directory endpoints.

### D. Provider verification

Implement a platform-controlled review workflow.

The platform administrator must be able to:

- View pending provider applications.
- Inspect submitted professional information.
- Review evidence references through authorized access.
- Approve or reject applications.
- Record a decision reason.
- Suspend a previously verified provider where necessary.
- Inspect the decision history.

Every important decision must be audited.

Provider verification must remain separate from organization affiliation.

### E. Organization membership and affiliation

A verified provider must be able to belong to multiple approved healthcare organizations.

Each affiliation must independently contain:

- Organization.
- Provider/account.
- Organization-scoped role.
- Membership status.
- Invitation and approval information.
- Effective dates.
- Decision actor and timestamps.

Membership lifecycle:

`INVITED → PENDING → ACTIVE`

Alternative terminal or restricted states:

`REJECTED`, `SUSPENDED`, `ENDED`

Rules:

- Organization administrators manage only their own organization.
- An organization cannot activate an unverified provider for healthcare exchange.
- Suspending one affiliation must not suspend the provider's other active affiliations.
- Ending one affiliation must not delete the provider account or professional profile.
- Membership status must be checked against the database during authorization.
- A client must never be trusted to assign itself an organization role.

### F. Role and authorization foundation

Introduce or extend organization-scoped role assignments without breaking the existing authentication system.

Maintain a clear distinction between:

1. Identity authentication.
2. Platform-level authorization.
3. Professional verification.
4. Organization membership.
5. Organization-specific permissions.

Keycloak authenticates the identity. The application database remains authoritative for mutable provider verification, organization approval, membership status, and organization-scoped authorization.

Do not trust stale JWT claims for mutable membership or verification decisions.

Do not allow the frontend to decide whether an operation is authorized.

---

## 4. API implementation

Implement the registry API using the existing FastAPI conventions.

Use the proposed `/api/v1` namespace unless the repository reveals a compatibility issue that must be documented.

Expected API capabilities:

**Organization applications**
- Submit application.
- View own application.
- List applications for platform administrators.
- Review and decide applications.
- View approved organization directory profiles.

**Provider applications**
- Submit professional application.
- View own application.
- List applications for platform administrators.
- Review and decide applications.
- View approved provider directory profiles.

**Organization memberships**
- Invite or request provider affiliation.
- List memberships belonging to the authenticated administrator's organization.
- Approve or reject membership requests.
- Suspend or end memberships.
- View the current provider's own affiliations.

All endpoints must have:

- Pydantic request and response schemas.
- Server-side authorization.
- Input validation.
- Consistent error responses.
- Pagination for directory and administrative lists.
- Appropriate database indexes and constraints.
- Audit logging for security-relevant changes.
- Tests for authorized and unauthorized access.

Never expose raw SQLAlchemy models directly.

Never accept a client-supplied organization ID as proof of organizational authority.

---

## 5. Frontend implementation

Build usable workflows within the existing React application.

Do not redesign the entire application.

Add or extend the appropriate workspaces:

**Platform administration**
- Organization application review.
- Provider application review.
- Verification decisions.
- Organization/provider status management.
- Membership oversight.

**Organization administration**
- Organization profile.
- Organization staff and provider memberships.
- Pending affiliation requests.
- Active, suspended, and ended memberships.

**Provider workspace**
- Professional profile.
- Verification status.
- Application status and review feedback.
- Organization affiliations.

**Patient-facing directory**
- Display only approved active organizations.
- Display only currently verified providers with eligible active affiliations.
- Show meaningful professional and organization information.
- Do not expose private registration evidence or administrative data.

All frontend actions must use real backend APIs.

Do not create fake dashboards with hardcoded data and present them as implemented functionality.

Provide useful loading, empty, success, and error states.

Maintain a consistent, professional healthcare product experience.

---

## 6. Database and migration safety

This is an existing application with historical data.

Use additive, reversible migrations wherever possible.

Before creating migrations:

- Inspect the current schema and migration history.
- Identify existing organization and provider account representations.
- Identify existing membership relationships.
- Identify existing FHIR references and foreign keys.
- Identify existing test fixtures that depend on the current schema.

Migration requirements:

1. Preserve existing users.
2. Preserve existing provider accounts.
3. Preserve existing organization-related accounts.
4. Preserve existing memberships.
5. Preserve existing consent records.
6. Preserve existing FHIR identifiers.
7. Preserve existing laboratory workflows.
8. Preserve existing clinical files and audit records.
9. Do not automatically mark legacy doctors as verified.
10. Do not automatically mark legacy organizations as approved.

Use explicit compatibility mappings and safe defaults.

Test migrations on fresh SQLite and disposable PostgreSQL databases.

Do not migrate or modify the existing project PostgreSQL database.

Do not delete or rewrite historical records to make migrations pass.

---

## 7. Security requirements

Security is a core product requirement, not a final checklist.

Implement and test:

- Authentication on protected routes.
- Platform-admin authorization.
- Organization-level tenant isolation.
- Provider verification checks.
- Organization approval checks.
- Active membership checks.
- Protection against horizontal privilege escalation.
- Protection against vertical privilege escalation.
- Protection against guessed organization/provider IDs.
- Protection against unauthorized membership creation.
- Protection against self-approval.
- Protection against public exposure of verification evidence.
- Protection against stale role and membership information.
- Audit logging for application decisions and membership transitions.

Use fail-closed authorization.

A suspended provider must not gain exchange privileges through an old JWT.

An administrator of Hospital A must not manage Hospital B.

A verified doctor without an active organization membership must not gain organization-based exchange access.

An organization administrator must not approve their own platform-level organization verification.

---

## 8. FHIR and blockchain boundaries

Keep the existing architectural responsibilities clear.

FHIR R4:

- Use Practitioner for provider identity representation.
- Use Organization for healthcare organization representation.
- Use PractitionerRole when representing a provider's role at a specific organization.
- Preserve the mapping between internal domain IDs and FHIR resource identifiers.
- Keep application authorization in the backend.
- Do not treat the existence of a FHIR resource as proof of verification.

Hyperledger Fabric:

- Do not store professional documents, credentials, patient data, or organization secrets on-chain.
- Do not introduce unnecessary blockchain transactions for every database operation.
- If existing outbox patterns require events for verification or organization approval, define a minimal allowlisted event contract.
- Preserve existing ledger event conventions and transactional outbox behavior.

Do not claim live FHIR or Fabric integration unless the corresponding integration has actually been tested.

---

## 9. Required tests

Add meaningful tests, not only happy-path tests.

At minimum, test:

**Organization**
- Application submission.
- Pending organization exclusion from directory.
- Administrator approval.
- Administrator rejection.
- Organization suspension.
- Unauthorized approval.
- Cross-organization administration denial.

**Provider**
- Provider application submission.
- Pending provider exclusion from directory.
- Verification approval.
- Rejection.
- Suspension.
- Unverified provider denied exchange eligibility.
- Unauthorized verification denial.

**Membership**
- Invitation and approval.
- Unverified provider cannot become active.
- Organization A cannot manage organization B.
- Membership suspension removes that organization's access.
- Membership termination preserves historical records.
- Multiple independent organization affiliations.
- One affiliation's suspension does not disable another valid affiliation.

**Authorization**
- Client cannot self-assign privileged roles.
- Client cannot change its organization identity.
- Stale token cannot bypass current database status.
- Guessed IDs cannot expose private application data.
- Verification evidence is not publicly accessible.

Run the complete existing test suite after adding the new tests.

Do not weaken or remove existing security tests to make the new implementation pass.

---

## 10. Strict implementation sequence

Work in these stages:

**Stage 1 — Repository and design validation**

Inspect the current repository and compare it with `MILESTONE_1_DESIGN.md`.

Produce a short implementation map showing:
- Existing files to extend.
- New files to create.
- Models and relationships.
- Migration strategy.
- API endpoints.
- Frontend components.
- Security dependencies.
- Test plan.

If a significant design decision conflicts with the existing application, document it before proceeding.

**Stage 2 — Backend domain and migration**

Implement organization/provider entities, membership lifecycle, schemas, services, and additive migrations.

Verify database constraints and compatibility before proceeding.

**Stage 3 — API and authorization**

Implement registry endpoints and centralized authorization services.

Run focused backend tests, including negative authorization tests.

**Stage 4 — Frontend workflows**

Implement the corresponding administrative, organization, provider, and patient-directory workflows using real APIs.

**Stage 5 — Integration and verification**

Run all available tests, migrations, frontend build, static checks, and relevant integration tests.

Record exactly what was tested and what remains unverified.

If a stage fails, fix the underlying issue before proceeding.

Do not conceal failures or mark incomplete work as complete.

---

## 11. Non-negotiable repository protections

- Do not run destructive database commands.
- Do not modify the existing project PostgreSQL database.
- Do not delete user files or existing functionality.
- Do not reset Git history.
- Do not overwrite unrelated user edits.
- Do not modify the historical audit entry #33.
- Do not change the existing audit hash-chain format.
- Preserve the PostgreSQL `READ COMMITTED` audit concurrency fix.
- Do not remove existing tests.
- Do not commit or push unless explicitly instructed.
- Do not use real patient information. Use synthetic test data only.

Before every substantial change, understand the existing implementation.

---

## 12. Documentation and final report

Update the relevant documentation:

- `PROJECT_STATUS.md`
- `IMPLEMENTATION_STATUS.md`
- `ARCHITECTURE_REVIEW.md`
- `SECURITY_ASSESSMENT.md`
- `TESTING_REPORT.md`
- `INTEGRATION_GUIDE.md`
- `README.md`, only where necessary.

At completion, report:

1. Features actually implemented.
2. Database entities and migration details.
3. API endpoints added.
4. Frontend workflows added.
5. Security controls implemented.
6. Tests executed and exact results.
7. Tests skipped or blocked, with reasons.
8. Existing functionality preserved.
9. Remaining risks and known limitations.
10. Exact recommended next milestone.

Clearly distinguish:
- Implemented.
- Tested locally.
- Integration-tested.
- Not yet verified.

Do not claim production readiness.

---

## Final engineering principle

HealthHarbor must become a trustworthy healthcare exchange system, not merely a collection of dashboards.

Every identity must have a trustworthy origin. Every organization must have controlled membership. Every professional privilege must be independently justified. Every future clinical-data exchange must be explicitly authorized and auditable.

Build carefully, preserve what already works, and prove every important security boundary with tests.

**Begin with Stage 1. Proceed through the stages only when the preceding stage has passed its verification gate.**