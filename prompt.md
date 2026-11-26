# MASTER DEVELOPMENT PROMPT
# HealthHarbor — Patient-Centric, Consent-Aware Healthcare Information Exchange Network

## 1. Your Role

Act as a principal software architect, senior healthcare interoperability engineer, backend engineer, application security specialist, database architect, and frontend product engineer.

You are working on an existing project named HealthHarbor.

Your task is to evolve the existing application into a secure, patient-centric healthcare information exchange platform that connects independently operated hospitals, doctors, diagnostic laboratories, and patients.

Do not treat this as a new project.

Inspect the existing repository, preserve completed functionality, understand existing architectural decisions, and extend the system incrementally.

The final objective is a working healthcare exchange network, not merely a collection of disconnected dashboards.

---

# 2. PRODUCT VISION — NON-NEGOTIABLE

The central problem HealthHarbor must solve:

A patient visits Hospital A, receives prescriptions, laboratory reports, diagnostic results, and other clinical documents.

Later, the same patient visits a different doctor at Hospital B.

The patient should be able to identify that doctor, authorize access to relevant medical records, and securely share those records without depending on physical documents or manually transferring files between hospitals.

The receiving doctor should be able to review the authorized records and continue the patient's care.

The patient remains at the center of the system.

HealthHarbor must provide:

1. Verified healthcare professional identities.
2. Verified healthcare organizations.
3. Controlled hospital and laboratory onboarding.
4. Patient-doctor discovery and relationships.
5. Patient-controlled consent.
6. Secure cross-organization document exchange.
7. Healthcare interoperability through FHIR.
8. Traceable access and document provenance.
9. Organization-level administration.
10. A scalable foundation for future hospital integrations.

The platform should support the exchange of:

- Prescriptions.
- Laboratory reports.
- Diagnostic reports.
- Medical certificates.
- Discharge summaries.
- Clinical documents.
- Relevant FHIR resources.
- Other permitted patient healthcare records.

Do not reduce the product to a file-upload application.

---

# 3. EXISTING ARCHITECTURE — PRESERVE AND EXTEND

The current project uses:

- Frontend: React + Vite.
- Backend: FastAPI + Python.
- ORM: SQLAlchemy.
- Migrations: Alembic.
- Database: PostgreSQL.
- Authentication: Keycloak / OIDC / OAuth2 Authorization Code + PKCE.
- Healthcare interoperability: HAPI FHIR R4.
- Blockchain: Hyperledger Fabric with Go chaincode.
- Integration: Fabric HTTP Gateway adapter and transactional outbox.
- Infrastructure: Docker Compose.
- Security testing: Python tests and OWASP ZAP.
- Performance testing: k6.

Inspect the current source code before designing new modules.

Existing capabilities include:

- Patient, physician, administrator, laboratory supervisor, and technician roles.
- Organization membership.
- Patient consent management.
- Named-physician organization consent.
- Resource-scoped access authorization.
- Clinical file upload and download.
- Laboratory workflow.
- FHIR server integration foundations.
- Keycloak integration foundations.
- Blockchain event integration foundations.
- Audit hash-chain logging.
- Database-backed login rate limiting.

Do not duplicate existing functionality.

Reuse and extend existing models, services, routers, schemas, and frontend components wherever appropriate.

Read the latest:
- PROJECT_STATUS.md
- IMPLEMENTATION_STATUS.md
- SECURITY_ASSESSMENT.md
- TESTING_REPORT.md
- INTEGRATION_GUIDE.md
- ARCHITECTURE_REVIEW.md
- prompt.md

Treat these documents and the current source code as the starting point.

---

# 4. ARCHITECTURAL DIRECTION

Use a centralized, multi-tenant healthcare exchange architecture for the initial implementation.

HealthHarbor will provide a shared exchange platform connecting participating healthcare organizations.

However, design integration boundaries so that future hospitals can retain their own HIS/EHR systems and exchange information through standardized APIs.

The logical architecture should contain:

A. Identity and Access Layer
- Keycloak.
- Patient identity.
- Professional identity.
- Organization identity.
- Role and permission management.

B. Healthcare Registry Layer
- Healthcare organization registry.
- Verified provider registry.
- Organization membership.
- Professional verification.
- Hospital onboarding.

C. Patient Relationship Layer
- Provider discovery.
- Patient-doctor relationships.
- Consultation requests.
- Referrals.
- Record-sharing requests.

D. Consent and Authorization Layer
- Patient consent.
- Resource-level authorization.
- Organization-level authorization.
- Named-provider authorization.
- Consent expiration.
- Consent revocation.
- Access history.

E. Healthcare Exchange Layer
- Document discovery.
- Secure document storage.
- Secure document retrieval.
- Cross-organization sharing.
- FHIR interoperability.
- Document provenance.

F. Clinical Workflow Layer
- Prescriptions.
- Laboratory requests.
- Laboratory reports.
- Diagnostic reports.
- Physician review.

G. Trust and Audit Layer
- Application audit records.
- Integrity verification.
- Hyperledger Fabric integration for selected verifiable events.

H. Administration Layer
- Platform administrator.
- Organization administrator.
- Provider approval.
- Organization approval.
- Membership management.
- Compliance and audit review.

---

# 5. PHASE ONE — HEALTHCARE ORGANIZATION REGISTRY

Build a proper organization onboarding and management system.

Supported organization types:

- Hospitals.
- Clinics.
- Diagnostic laboratories.
- Other authorized healthcare institutions.

Each organization should have:

- Unique organization identifier.
- Legal or registered name.
- Organization type.
- Registration details.
- Address.
- Contact information.
- Administrative contact.
- Verification status.
- Activation status.
- Created and updated timestamps.

Organization registration workflow:

1. An authorized representative submits an organization registration request.
2. The platform administrator reviews the request.
3. Supporting registration information is checked.
4. The organization is approved or rejected.
5. An organization administrator is assigned.
6. The organization becomes active.
7. The administrator can manage its staff and memberships.

Organization statuses should include appropriate states such as:

- PENDING.
- UNDER_REVIEW.
- APPROVED.
- REJECTED.
- SUSPENDED.

Do not allow unapproved organizations to access exchange services.

Implement organization administration APIs and frontend screens.

---

# 6. PHASE TWO — VERIFIED HEALTHCARE PROVIDER REGISTRY

Build a professional identity system for doctors.

A doctor must have an independent professional identity, separate from their employment at a particular hospital.

A doctor profile should support:

- Unique provider identifier.
- Full name.
- Professional registration number.
- Registration authority.
- Qualifications.
- Specialization.
- Contact details.
- Professional verification status.
- Account activation status.
- Organization memberships.

Doctor onboarding workflow:

1. Doctor submits a registration request.
2. Doctor provides professional details and supporting evidence.
3. HealthHarbor platform administrators review professional eligibility.
4. The selected hospital verifies the doctor's affiliation.
5. Both required approvals are recorded.
6. The doctor receives an active account.
7. The doctor can access authorized HealthHarbor services.

Implement a controlled approval workflow.

Do not automatically activate professional accounts after ordinary email registration.

Do not invent professional credentials or claim to verify a medical registration number against an external authority unless an actual verification integration exists.

Design the verification service so authoritative professional registration sources can be integrated later.

### Multi-hospital memberships

A doctor may work at more than one hospital.

Therefore:

- Provider identity must not be duplicated for each hospital.
- A doctor can have multiple organization memberships.
- Each membership has its own status and permissions.
- An organization administrator can manage only their own organization's memberships.
- Suspending one membership must not automatically suspend the provider's entire professional identity.
- Revocation of platform-level professional eligibility must block the provider's exchange privileges.

Implement proper membership lifecycle management.

---

# 7. PHASE THREE — ACCOUNT AND ROLE MANAGEMENT

Integrate the registry with the existing Keycloak authentication system.

Keycloak remains responsible for authentication.

FastAPI and PostgreSQL remain responsible for application-specific authorization, provider profiles, organization memberships, and approval workflows.

Implement:

- Patient self-registration.
- Doctor application registration.
- Organization registration.
- Administrator-managed staff provisioning.
- Technician registration or invitation.
- Account activation.
- Account suspension.
- Membership termination.
- Role assignment.
- Organization-scoped permissions.

Never trust role or organization identifiers supplied directly by a frontend request.

Derive the authenticated user's identity from validated tokens and resolve permissions from trusted backend records.

Maintain clear separation between:

- Platform administrator.
- Organization administrator.
- Verified doctor.
- Patient.
- Laboratory supervisor.
- Laboratory technician.

Create a proper administration workspace for:

1. Platform administrators.
2. Hospital administrators.
3. Laboratory administrators.

Each must have appropriate boundaries.

---

# 8. PHASE FOUR — PATIENT-CENTRIC PROVIDER DISCOVERY

Build a verified healthcare provider directory.

Patients must be able to discover providers through:

- Doctor name.
- Professional registration identifier.
- Specialization.
- Hospital.
- Organization.
- Location.

Only eligible verified providers should appear as active exchange participants.

Doctor search results should display:

- Doctor name.
- Verified professional status.
- Specialization.
- Qualifications where verified.
- Professional registration information where appropriate.
- Participating hospital affiliations.
- Organization status.

Patients must be able to view a provider's profile before initiating a relationship.

Do not expose sensitive personal information or private contact information unnecessarily.

Build:

- Provider search API.
- Organization search API.
- Provider profile API.
- Provider directory frontend.
- Hospital directory frontend.

Implement pagination, filtering, validation, and safe query handling.

---

# 9. PHASE FIVE — PATIENT-DOCTOR RELATIONSHIPS AND INITIAL COMMUNICATION

A patient discovering a doctor must not automatically grant access to all medical records.

Introduce a formal patient-provider relationship lifecycle.

Possible states:

- REQUESTED.
- ACCEPTED.
- DECLINED.
- ACTIVE.
- CLOSED.

Support:

1. Patient initiates a relationship or consultation request.
2. Doctor or authorized hospital staff reviews it.
3. Doctor accepts or declines.
4. HealthHarbor records the relationship.
5. Doctor may request specific clinical information.
6. Patient approves or rejects the record-sharing request.

Also implement a referral workflow where an existing physician can refer a patient to another verified provider.

The referral must preserve:

- Referring provider.
- Receiving provider.
- Patient identity.
- Referral purpose.
- Relevant document references.
- Consent or other valid authorization.
- Referral status.
- Timestamps.

Do not confuse a patient-doctor relationship with authorization to read all records.

A relationship provides context. Consent determines permitted access.

Do not build an unrestricted doctor-to-doctor messaging system unless necessary for the defined clinical workflow.

If communication is implemented, use controlled clinical messages or referral requests, not unrestricted personal messaging.

---

# 10. PHASE SIX — SECURE CROSS-ORGANIZATION DOCUMENT EXCHANGE

This is the most important functional capability of HealthHarbor.

Build a proper document exchange service.

Documents may originate from:

- Hospitals.
- Clinics.
- Doctors.
- Diagnostic laboratories.
- Other authorized healthcare institutions.

Supported document categories should include:

- Prescriptions.
- Laboratory reports.
- Diagnostic reports.
- Discharge summaries.
- Medical certificates.
- Clinical notes.
- Other permitted documents.

### Document ingestion

When an authorized provider uploads a document:

1. Authenticate the uploader.
2. Verify their professional status.
3. Verify their organization membership.
4. Validate patient association.
5. Validate document type and size.
6. Validate file content rather than trusting file extensions.
7. Perform safe file scanning where available.
8. Encrypt the document before persistent storage.
9. Calculate a cryptographic integrity hash.
10. Persist document metadata.
11. Create or update the relevant FHIR resource.
12. Record document provenance and audit events.

### Document storage

Implement a storage abstraction.

Do not tightly couple business logic to a single local filesystem path.

The initial deployment may use encrypted local or object storage, but the architecture should support future S3-compatible or hospital-controlled storage.

Store metadata separately from document bytes.

The document metadata should contain:

- Document identifier.
- Patient identifier.
- Uploading provider.
- Source organization.
- Document category.
- FHIR DocumentReference identifier.
- Storage reference.
- Integrity hash.
- Encryption metadata where appropriate.
- Creation timestamp.
- Document status.
- Provenance information.

Never store document contents directly on Hyperledger Fabric.

### Patient-controlled sharing

A patient should be able to:

1. View their available clinical documents.
2. Select one or more documents.
3. Select a verified doctor or organization.
4. Choose the permitted document categories or specific resources.
5. Set an appropriate expiration period.
6. Review the sharing request.
7. Grant or reject consent.
8. Revoke future access.
9. View the access history.

Enforce consent at the backend for every protected operation.

Frontend visibility is not authorization.

### Secure document retrieval

When a doctor at Hospital B requests a document originating from Hospital A:

1. Validate the doctor's authentication.
2. Validate professional eligibility.
3. Validate active organization membership.
4. Resolve the patient identity.
5. Validate the patient-provider relationship where applicable.
6. Validate the exact consent grant and resource scope.
7. Validate expiration and revocation.
8. Authorize the document request.
9. Retrieve the encrypted document.
10. Decrypt only within the authorized service boundary.
11. Stream the document securely to the authorized recipient.
12. Record the access event.

Use authenticated streaming or short-lived, narrowly scoped download links.

Avoid permanent public file URLs.

Do not allow access through predictable document IDs.

Prevent IDOR and cross-organization access.

Revocation must block subsequent retrievals. Do not claim that revocation can erase copies already legitimately downloaded by recipients.

### Document integrity

Use cryptographic hashes to detect unexpected document changes.

Preserve document provenance:

- Who created it.
- Which organization issued it.
- Who uploaded it.
- When it was uploaded.
- Whether it was subsequently replaced or superseded.

Do not silently overwrite clinical documents.

Use versioning or supersession records where appropriate.

---

# 11. PHASE SEVEN — FHIR INTEROPERABILITY

Use HAPI FHIR R4 as the interoperability foundation.

Inspect existing resource implementations before adding new ones.

Use appropriate FHIR resources, including where supported:

- Patient.
- Practitioner.
- PractitionerRole.
- Organization.
- Encounter.
- Consent.
- DocumentReference.
- Binary.
- ServiceRequest.
- Observation.
- DiagnosticReport.
- MedicationRequest.
- Provenance.

FHIR resource selection must reflect actual application workflows.

Implement consistent identifiers and references.

For document exchange:

- DocumentReference should describe the document.
- Binary or another supported secure storage mechanism may represent document content where appropriate.
- Do not expose unrestricted Binary endpoints.
- Do not assume FHIR server authorization automatically enforces HealthHarbor consent.
- Backend authorization must remain authoritative.

Test actual resource creation and retrieval.

Do not claim full FHIR interoperability based only on successful server startup or metadata retrieval.

---

# 12. PHASE EIGHT — MULTI-HOSPITAL EXCHANGE API

HealthHarbor should eventually support hospitals that already operate their own management systems.

Create a clearly defined integration API.

Support future integration through:

- FHIR REST APIs.
- Secure server-to-server authentication.
- Organization identity.
- Authorized document exchange.
- Patient identity resolution.
- Consent verification.
- Audit and provenance.

Do not require every hospital to replace its existing HIS/EHR.

The initial deployment can provide HealthHarbor web portals, while integration APIs allow existing systems to participate.

Design the API with versioning, documentation, input validation, and strict organization isolation.

Do not expose internal database models directly as public API contracts.

---

# 13. PHASE NINE — AUDIT AND HYPERLEDGER FABRIC

Retain the existing audit architecture.

The PostgreSQL audit logger remains responsible for application audit records.

Hyperledger Fabric should be used selectively for verifiable events.

Potential events:

- Document registration.
- Document integrity hash.
- Consent grant.
- Consent revocation.
- Authorized sharing event.
- Organization verification event.

Do not put:

- Patient names.
- Medical reports.
- Prescriptions.
- Clinical observations.
- Personal identifiers.
- Authentication secrets.

on the blockchain.

Use appropriate pseudonymous references and data minimization.

Only report a ledger event as committed after Fabric confirms the transaction.

Preserve the transactional outbox and retry mechanism.

### Critical historical audit protection

The known historical audit discontinuity at PostgreSQL entry #33 must remain untouched.

Do not:

- Rewrite it.
- Recompute its stored hashes.
- Delete it.
- Reset the database.
- Conceal the integrity warning.

The recent PostgreSQL READ COMMITTED concurrency fix must be preserved.

New audit events must continue linking to the immediate previous entry according to the existing audit format.

---

# 14. PHASE TEN — FRONTEND PRODUCT EXPERIENCE

The application must feel like one coherent healthcare platform.

Extend the existing React frontend rather than creating unrelated dashboards.

Build the following workspaces.

### Patient Portal

- Personal dashboard.
- Medical records.
- Prescriptions.
- Laboratory reports.
- Diagnostic documents.
- Provider directory.
- Hospital directory.
- Doctor relationship requests.
- Referrals.
- Sharing requests.
- Consent management.
- Access history.

### Doctor Portal

- Professional profile.
- Verification status.
- Organization memberships.
- Patient relationship requests.
- Patient list limited to authorized relationships.
- Record access requests.
- Authorized medical records.
- Prescriptions and clinical documents.
- Laboratory workflows.
- Referrals.
- Clinical review history.

### Hospital Administration Portal

- Organization profile.
- Organization verification status.
- Staff directory.
- Doctor affiliation requests.
- Membership management.
- Staff invitations.
- Organization-level audit information.
- Integration configuration.

### Laboratory Portal

- Laboratory profile.
- Supervisor workspace.
- Technician memberships.
- Assigned requests.
- Specimen processing.
- Results submission.
- Report publishing.

### Platform Administration Portal

- Organization onboarding.
- Professional verification requests.
- Organization approval.
- Provider approval.
- Account suspension.
- Organization management.
- Security and audit review.

Use a consistent design system.

Prioritize clarity, accessibility, responsive layouts, predictable navigation, meaningful loading states, and useful error messages.

Do not create decorative controls that do nothing.

Every important action must connect to a real backend operation.

---

# 15. PHASE ELEVEN — DATABASE AND DOMAIN MODEL

Inspect the existing SQLAlchemy models and Alembic history.

Design new domain models only where necessary.

Potential domain entities:

- HealthcareOrganization.
- HealthcareProvider.
- ProviderVerification.
- OrganizationMembership.
- OrganizationApplication.
- ProviderApplication.
- PatientProviderRelationship.
- ConsultationRequest.
- Referral.
- DocumentMetadata.
- DocumentVersion.
- DocumentAccessRequest.
- DocumentShare.
- Consent.
- ConsentResource.
- DocumentProvenance.

Reuse existing User, Consent, Organization, and membership models where they already fulfill the required responsibilities.

Establish:

- Foreign key constraints.
- Unique identifiers.
- Appropriate indexes.
- Status constraints.
- Created and updated timestamps.
- Referential integrity.
- Tenant isolation.

Use Alembic migrations.

Do not modify live databases during implementation.

Test migrations on disposable PostgreSQL and SQLite databases where supported.

Preserve existing records and backward compatibility.

---

# 16. PHASE TWELVE — SECURITY AND PRIVACY

Security must be built into every workflow.

Verify:

- OIDC authentication.
- Professional verification.
- Organization membership.
- Role-based authorization.
- Patient ownership.
- Consent enforcement.
- Resource-level authorization.
- Cross-organization isolation.
- File integrity.
- Secure storage.
- Secure transfer.
- Audit logging.
- Rate limiting.
- Input validation.
- Error sanitization.
- Secret management.

Explicitly test:

1. Doctor from Hospital B attempting to access a Hospital A patient's records without consent.
2. Doctor with expired consent attempting retrieval.
3. Doctor with revoked consent attempting retrieval.
4. Doctor attempting access outside the granted resource scope.
5. Suspended doctor attempting exchange access.
6. Doctor whose hospital membership has been terminated.
7. Technician attempting access to another laboratory's requests.
8. Patient attempting to access another patient's documents.
9. Organization administrator attempting to manage another organization's users.
10. Unauthorized user attempting to retrieve a file using a guessed document identifier.

All unauthorized operations must fail safely and be auditable.

Do not use real patient data.

Consider applicable Indian healthcare privacy and data protection requirements, professional registration requirements, and future ABDM compatibility.

Do not claim legal or ABDM compliance without the necessary validation and integrations.

---

# 17. IMPLEMENTATION STRATEGY

Do not implement all modules in one uncontrolled code-generation pass.

Work in these development milestones.

## Milestone 1 — Domain and architecture design

- Inspect current implementation.
- Map existing models and services.
- Identify reusable components.
- Design domain relationships.
- Produce API contracts.
- Produce migration plan.
- Produce authorization matrix.

Do not modify code until the design is reviewed.

## Milestone 2 — Organization and provider registry

- Organization onboarding.
- Provider onboarding.
- Professional verification.
- Organization approval.
- Multi-hospital membership.
- Administrative management.

## Milestone 3 — Patient-provider relationships

- Provider discovery.
- Organization directory.
- Patient-doctor requests.
- Referral workflows.
- Relationship lifecycle.

## Milestone 4 — Secure document exchange

- Document metadata.
- Encrypted storage.
- Document discovery.
- Patient-controlled sharing.
- Consent-aware retrieval.
- Document provenance.
- Cross-organization tests.

## Milestone 5 — FHIR interoperability

- Provider and organization resource mapping.
- DocumentReference integration.
- Clinical resource exchange.
- Real FHIR round-trip tests.

## Milestone 6 — External hospital integration

- Versioned integration APIs.
- Organization authentication.
- FHIR exchange.
- Server-to-server workflows.

## Milestone 7 — Blockchain and audit verification

- Event selection.
- Outbox integration.
- Fabric commit confirmation.
- Audit integrity tests.

## Milestone 8 — Complete frontend experience

- Patient portal.
- Doctor portal.
- Hospital administration.
- Platform administration.
- Laboratory portal.
- End-to-end workflows.

## Milestone 9 — Complete system verification

- Cross-hospital acceptance tests.
- Security tests.
- Migration tests.
- Integration tests.
- Performance tests.
- Deployment documentation.

After each milestone, report changes and test evidence.

---

# 18. NON-NEGOTIABLE DEVELOPMENT SAFETY RULES

- Never rebuild the application from scratch.
- Never delete existing working features.
- Never overwrite user modifications.
- Never modify historical audit entry #33.
- Never reset or truncate the project database.
- Never use Docker volume deletion.
- Never execute migrations against the live project database without explicit approval.
- Use disposable test databases and synthetic patient data.
- Do not hardcode passwords, tokens, secrets, or private keys.
- Do not disable security controls to make workflows succeed.
- Do not introduce fake successful external integrations.
- Do not report unverified integrations as completed.
- Do not create commits or push code without permission.
- Do not modify unrelated files.
- Keep changes small, reviewable, and testable.

If a required integration is unavailable, build the proper interface and document the limitation. Do not pretend the integration works.

---

# 19. DEFINITION OF SUCCESS

HealthHarbor should eventually demonstrate this complete scenario:

1. Hospital A applies to join HealthHarbor.
2. Platform administrator verifies and approves Hospital A.
3. Hospital A administrator creates or invites staff memberships.
4. A doctor submits professional registration details.
5. Professional eligibility is verified.
6. Hospital A approves the doctor's affiliation.
7. Doctor account becomes active.
8. Patient registers and authenticates.
9. Patient visits Hospital A.
10. Doctor creates a prescription.
11. Laboratory technician processes a laboratory request and publishes a report.
12. Clinical records become discoverable by the patient.
13. Patient later discovers a verified doctor at Hospital B.
14. Patient initiates a consultation or relationship request.
15. Doctor accepts the relationship.
16. Doctor requests specific previous medical records.
17. Patient grants resource-scoped consent.
18. Hospital B retrieves the permitted records securely.
19. Doctor reviews the previous prescription and laboratory report.
20. The patient can inspect access history and revoke future access.
21. Every important operation has appropriate audit and provenance records.
22. Eligible blockchain events receive actual Fabric commit confirmation.

The same patient must retain a consistent identity across participating organizations.

Hospital B must not be able to access unrelated records or other patients' information.

This workflow is the central acceptance criterion.

---

# 20. FINAL REPORTING REQUIREMENTS

After every milestone, provide:

1. What was inspected.
2. What was implemented.
3. Files changed.
4. Database changes.
5. API endpoints added or modified.
6. Frontend workflows added.
7. Security controls implemented.
8. Tests executed.
9. Actual test results.
10. Unresolved issues.
11. Environment limitations.
12. Exact next milestone.

Maintain the project documentation:

- PROJECT_STATUS.md
- IMPLEMENTATION_STATUS.md
- SECURITY_ASSESSMENT.md
- TESTING_REPORT.md
- INTEGRATION_GUIDE.md
- ARCHITECTURE_REVIEW.md

Keep documentation consistent with actual code and test evidence.

# STARTING INSTRUCTION

Begin with Milestone 1 only.

Inspect the existing repository and produce:

1. Current architecture assessment.
2. Existing-to-new domain mapping.
3. Database entity relationship proposal.
4. Provider onboarding sequence.
5. Organization onboarding sequence.
6. Patient-provider relationship sequence.
7. Cross-organization document-sharing sequence.
8. API contract proposal.
9. Security and authorization matrix.
10. Incremental implementation plan.

Do not start implementing Milestones 2–9 until Milestone 1 has been presented for review.

Your objective is to build HealthHarbor as a trustworthy healthcare information exchange network where patients remain in control of their medical records and verified healthcare professionals can securely collaborate across organizational boundaries.