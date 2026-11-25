# MASTER DEVELOPMENT PROMPT — WIRACHAIN

## Project Title
**A SECURE, CONSENT-AWARE FHIR AND PERMISSIONED BLOCKCHAIN FRAMEWORK FOR INTEROPERABLE HEALTHCARE DATA EXCHANGE AMONG PATIENTS, PHYSICIANS AND CLINICAL LABORATORIES**

Act as a senior software architect, healthcare interoperability engineer, cybersecurity engineer, blockchain developer, database architect and full-stack development lead.

Your responsibility is to DESIGN, IMPLEMENT, TEST AND DELIVER a complete, functional, integrated full-stack research prototype called **WiraChain**, strictly aligned with the attached project abstract.

This is not a generic hospital management system, patient CRUD application, appointment booking platform or simple role-based dashboard.

I want the actual research concept implemented end to end.

I am providing:
1. My original project abstract, which is the authoritative statement of requirements.
2. My existing project ZIP, which contains an earlier implementation. Treat it as legacy reference material. Inspect it, reuse genuinely useful components where appropriate, but do not allow its limitations to determine the new architecture.

Do not merely generate a project plan, architecture document, UI mockup or isolated code snippets. Build the complete application.

---

# 1. CORE RESEARCH OBJECTIVE

Build a secure, consent-aware healthcare information exchange framework that connects:

- Patients
- Physicians
- Clinical laboratories
- Laboratory technicians
- Administrators

The system must provide interoperable healthcare information exchange using HL7 FHIR resources, enforce fine-grained patient-controlled consent, implement secure laboratory workflows, and use Hyperledger Fabric as a genuine permissioned blockchain for selected audit, consent and integrity events.

Clinical data must remain off-chain in secure storage. Blockchain must provide tamper-evident provenance, not act as the clinical database.

# 2. MANDATORY TECHNOLOGY STACK

Use the following technologies:

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Backend | Python FastAPI |
| Identity management | Keycloak |
| Authentication | OAuth 2.0 / OpenID Connect |
| Healthcare interoperability | HL7 FHIR R4 |
| FHIR server | HAPI FHIR |
| Application database | PostgreSQL |
| Blockchain | Hyperledger Fabric |
| Chaincode | Go |
| Frontend styling | Modern responsive CSS / Tailwind CSS |
| API documentation | OpenAPI / Swagger |
| Performance testing | k6 or Apache JMeter |
| Security testing | OWASP ZAP |
| API testing | Postman / automated tests |
| Containerization | Docker and Docker Compose |

Do not replace mandatory components with simulated equivalents.

In particular:
- A hash-chained PostgreSQL table is not Hyperledger Fabric.
- FHIR-shaped JSON is not sufficient evidence of HAPI FHIR interoperability.
- JWT authentication alone is not Keycloak integration.
- A mock blockchain service is not an implemented permissioned blockchain.

If an infrastructure component cannot run in the development environment, still implement its genuine integration, provide reproducible deployment configuration and clearly document the limitation. Never falsely claim it is operational.

Use FHIR R4 consistently throughout the implementation.

# 3. PATIENT-CONTROLLED CONSENT MANAGEMENT

This is one of the most important parts of WiraChain.

Implement a dedicated consent management engine.

Patients must be able to:

1. View their healthcare information.
2. Select a specific physician.
3. Select the categories or specific resources the physician may access.
4. Grant permission for a defined period.
5. Set a maximum access duration of 30 days.
6. View active permissions.
7. Revoke permission before its expiration.
8. Review expired and revoked permissions.
9. View who accessed their records, when and for what purpose.

The backend must enforce these permissions.

Required rules:

- Default-deny authorization.
- Consent must be specific to the patient and authorized physician.
- Consent must include permitted resource scope.
- Consent must include validity start and end times.
- The server must enforce the 30-day maximum.
- Expired consent must automatically become ineffective.
- Early revocation must immediately prevent subsequent access.
- The frontend must never be trusted to enforce authorization.
- Cached authorization must not bypass revocation.
- Every relevant consent action must generate an auditable event.

Implement the FHIR R4 Consent resource and map its lifecycle correctly to the application's consent states.

Do not confuse authentication, RBAC, resource assignment and patient consent. They are separate authorization requirements.

# 4. FHIR INTEROPERABILITY

Integrate a real HAPI FHIR R4 server.

Implement and validate these FHIR resources:

- Patient
- Practitioner
- Organization
- ServiceRequest
- Specimen
- Observation
- DiagnosticReport
- Consent

Ensure correct references between resources.

Examples:
- A ServiceRequest references the patient, requesting practitioner and performing organization.
- A Specimen is associated with the relevant laboratory request.
- Observations reference the patient and appropriate specimen or request.
- DiagnosticReport references the relevant ServiceRequest and Observation resources.
- Consent references the patient and authorized practitioner.

Use HAPI FHIR for resource validation, persistence and retrieval.

Provide:
- FHIR resource creation.
- FHIR resource retrieval.
- FHIR resource updates with version handling.
- Reference validation.
- Resource-level authorization.
- FHIR API integration tests.

Do not simply create arbitrary JSON objects and call them FHIR resources.

# 5. ORDERED LABORATORY WORKFLOW

This must be a real workflow engine, not unrelated CRUD forms.

Implement this complete process:

### Stage 1 — Patient
The patient has a healthcare identity and can grant a physician limited access to selected medical information.

### Stage 2 — Physician
The physician:
- Views records authorized by the patient.
- Creates a laboratory test request.
- Generates a FHIR ServiceRequest.
- Assigns the request to a laboratory.
- Tracks request status.
- Reviews finalized reports.

### Stage 3 — Laboratory
The laboratory:
- Receives laboratory requests.
- Verifies the request.
- Accepts or rejects requests.
- Assigns accepted requests to authorized technicians.
- Tracks specimen processing.

### Stage 4 — Laboratory technician
The technician:
- Views only assigned laboratory work.
- Accepts assigned work.
- Registers specimens.
- Updates processing status.
- Submits observations and test results.
- Hands the completed work to an authorized laboratory reviewer.

### Stage 5 — Laboratory reviewer
The authorized reviewer:
- Reviews submitted results.
- Validates the report.
- Finalizes the DiagnosticReport.
- Records the finalization event.

### Stage 6 — Physician
The physician:
- Receives the finalized report.
- Passes the consent authorization check.
- Reviews observations and diagnostic results.
- Records clinical review.

### Stage 7 — Patient
The patient:
- Views authorized reports.
- Reviews access history.
- Controls future sharing through consent.

Implement explicit workflow states and valid state transitions.

Example:

REQUESTED → ACCEPTED → ASSIGNED → SPECIMEN_REGISTERED → PROCESSING → RESULTS_SUBMITTED → REVIEWED → FINALIZED → PHYSICIAN_REVIEWED

Reject invalid transitions.

Enforce actor identity, role, organization membership and assignment at every transition.

A technician must not be able to process an unassigned request or finalize a report without appropriate authorization.

# 6. HYPERLEDGER FABRIC — REAL BLOCKCHAIN IMPLEMENTATION

Hyperledger Fabric is mandatory.

Build a genuine permissioned network suitable for a research prototype.

Include:
- Provider organization.
- Laboratory organization.
- Fabric peers.
- Membership Service Provider identities.
- Ordering service.
- Channels.
- Endorsement policies.
- Go chaincode.
- Fabric Gateway integration.

Design chaincode for selected events:

1. ConsentGranted
2. ConsentRevoked
3. ConsentExpired
4. LaboratoryRequestAccepted
5. TechnicianAssigned
6. SpecimenRegistered
7. DiagnosticReportFinalized
8. ClinicalRecordIntegrityUpdated
9. AuthorizedRecordAccess

Each event must contain carefully selected metadata, pseudonymous references and cryptographic integrity evidence.

Do not store identifiable clinical records on-chain.

Keep the following off-chain:
- Patient names.
- Contact information.
- Medical history.
- Diagnostic reports.
- Laboratory observations.
- Prescriptions.
- Clinical documents.

Implement:
- Transaction submission.
- Endorsement.
- Commit confirmation.
- Transaction ID tracking.
- Ledger event retrieval.
- Integrity verification.
- Provenance history.

Use a transactional outbox pattern between PostgreSQL and Fabric.

Do not claim an event has been recorded on-chain until Fabric confirms successful commit.

The application must distinguish pending, committed and failed ledger events.

Blockchain should complement the consent engine, not replace access-control enforcement.

# 7. KEYCLOAK AND SECURITY

Configure Keycloak with:
- WiraChain realm.
- React frontend client.
- FastAPI backend audience.
- OAuth 2.0 / OIDC.
- Authorization Code Flow with PKCE.
- JWT signature verification.
- Role mapping.
- Token expiry handling.
- Refresh-token handling where appropriate.

Required roles:

PATIENT
PHYSICIAN
LAB_TECHNICIAN
LAB_SUPERVISOR
ADMIN

Implement backend security checks for:
- Authentication.
- Role-based authorization.
- Organization membership.
- Resource ownership.
- Laboratory assignment.
- Patient consent.
- Token validity.
- Resource-level access.

Also implement:
- Secure password and identity management through Keycloak.
- Input validation.
- SQL injection prevention.
- Rate limiting for sensitive endpoints.
- Secure CORS configuration.
- Safe error responses.
- Secrets through environment variables.
- Audit logging.
- Secure document access.

Never hardcode production credentials or secrets.

# 8. DATABASE DESIGN

Design a normalized PostgreSQL schema for application-level data.

Include entities for:
- User profiles.
- Organizations.
- Patients.
- Practitioners.
- Laboratories.
- Technicians.
- Consent records.
- Consent scopes.
- Laboratory requests.
- Technician assignments.
- Specimens.
- Workflow transitions.
- Clinical resource references.
- Audit events.
- Blockchain transaction references.
- Transactional outbox events.

Use appropriate:
- Primary keys.
- Foreign keys.
- Constraints.
- Indexes.
- Timestamps.
- Database migrations.
- Transaction management.

HAPI FHIR should manage its own FHIR persistence. Avoid creating competing duplicate clinical databases without a clear reason.

# 9. COMPLETE FRONTEND

Build a polished, modern, professional healthcare interoperability application.

The interface must reflect the seriousness of a secure clinical information exchange platform.

Do not create a generic template dashboard.

Create separate experiences for each role.

### Patient portal
- Patient profile.
- Healthcare record overview.
- Consent management.
- Grant access screen.
- Resource-level permission selection.
- Access duration selector.
- Active consent list.
- Revocation controls.
- Consent history.
- Record access history.
- Blockchain provenance verification view.

### Physician portal
- Physician profile.
- Authorized patient list.
- Patient record viewer.
- Consent status indicators.
- Laboratory request creation.
- ServiceRequest tracking.
- Laboratory result viewer.
- DiagnosticReport viewer.
- Clinical review history.

### Laboratory portal
- Incoming requests.
- Request acceptance/rejection.
- Technician assignment.
- Workload overview.
- Specimen tracking.
- Processing status.
- Report validation.
- Finalization workflow.

### Technician portal
- Assigned work queue.
- Specimen registration.
- Processing updates.
- Observation entry.
- Submission to laboratory reviewer.
- Assignment and workflow history.

### Administrator portal
- User and organization management.
- Role assignment.
- System activity.
- Security events.
- Workflow monitoring.
- Blockchain transaction monitoring.

Every screen must connect to actual backend functionality.

Implement:
- Loading states.
- Error states.
- Form validation.
- Empty states.
- Confirmation dialogs.
- Responsive layouts.
- Accessible components.
- Clear navigation.
- Useful notifications.

Avoid decorative buttons that do nothing.

# 10. AUDIT AND PROVENANCE

Implement a complete audit strategy.

Record:
- Authentication-related security events.
- Consent creation.
- Consent modification.
- Consent revocation.
- Access granted or denied.
- Laboratory request creation.
- Technician assignment.
- Specimen processing.
- Observation submission.
- Diagnostic report finalization.
- Clinical review.
- Blockchain transaction submission and confirmation.

Audit entries should identify the actor, action, timestamp, relevant resource reference, outcome and correlation ID.

Do not put sensitive patient information into application logs or blockchain events unnecessarily.

Provide a patient-accessible view of relevant record-sharing history.

# 11. TESTING AND RESEARCH EVALUATION

Build a reproducible evaluation suite.

### Functional testing
Test every role and major workflow.

### Consent testing
Test:
- No consent.
- Valid consent.
- Expired consent.
- Revoked consent.
- Resource outside authorized scope.
- Unauthorized physician.
- Consent duration greater than 30 days.
- Attempts to bypass authorization through direct API calls.

### Laboratory workflow testing
Test:
- Invalid state transitions.
- Unassigned technician access.
- Unauthorized report finalization.
- Duplicate request submissions.
- Invalid specimen references.

### Security testing
Test:
- Invalid and expired JWTs.
- Role escalation attempts.
- Unauthorized resource access.
- SQL injection attempts.
- Rate limiting.
- Broken object-level authorization.
- Consent bypass attempts.

Use safe, controlled tests against the local development environment.

### FHIR testing
Validate required resources and references using HAPI FHIR.

### Blockchain testing
Measure:
- Transaction submission latency.
- Commit latency.
- Transaction throughput.
- Ledger integrity verification.
- Blockchain integration overhead.

### Performance testing
Use k6 or JMeter.

Evaluate increasing concurrency and report:
- Requests per second.
- Average latency.
- p95 latency.
- Error rate.
- Resource utilization.

Compare an off-chain baseline with blockchain-enabled event processing.

Never invent test results. Generate reports from actual test executions.

# 12. DEVELOPMENT AND DELIVERY RULES

These instructions are mandatory.

1. First inspect the existing ZIP and the abstract thoroughly.
2. Produce a requirement-to-implementation mapping.
3. Establish the new architecture.
4. Create the repository structure.
5. Implement the backend and database.
6. Integrate Keycloak.
7. Integrate HAPI FHIR.
8. Implement the consent engine.
9. Implement the laboratory workflow.
10. Integrate Hyperledger Fabric.
11. Build the complete frontend.
12. Integrate all components.
13. Run automated tests.
14. Fix implementation errors.
15. Prepare deployment documentation.
16. Prepare research evaluation documentation.

Do not stop after creating the architecture.

Do not stop after implementing authentication.

Do not stop after implementing a basic dashboard.

Do not replace actual functionality with mock responses.

Do not use fake blockchain transactions.

Do not claim unimplemented features are complete.

Do not leave critical TODOs while declaring the project finished.

Use synthetic healthcare data for development and testing.

Use environment configuration rather than hardcoded secrets.

Keep the application modular, maintainable and documented.

Because the development machine may have limited RAM, provide lightweight development profiles and allow infrastructure components to be started independently. Do not assume all services can run simultaneously on a low-resource laptop.

# 13. REQUIRED FINAL DELIVERABLES

Deliver:

1. Complete frontend source code.
2. Complete FastAPI backend.
3. PostgreSQL schema and migrations.
4. Keycloak realm and client configuration.
5. HAPI FHIR integration.
6. Consent management engine.
7. Laboratory workflow engine.
8. Hyperledger Fabric network configuration.
9. Go chaincode.
10. Fabric integration service.
11. Docker Compose configurations.
12. Synthetic test data and seed scripts.
13. Automated test suites.
14. API documentation.
15. Architecture diagrams.
16. Deployment and setup guide for Linux.
17. Security testing report.
18. Performance evaluation report generated from real executions.
19. Research implementation mapping against my original abstract.
20. Complete README with exact setup, startup, test and troubleshooting commands.

# 14. ACCEPTANCE CRITERIA

The project is not complete unless all these scenarios work:

- A patient can grant a specific physician access to selected records for a limited period.
- The system rejects consent durations exceeding 30 days.
- The physician can access only authorized resources.
- Consent expiration blocks subsequent access.
- Early revocation blocks subsequent access.
- A physician can create a FHIR laboratory request.
- A laboratory can accept and assign that request.
- An authorized technician can register specimens and submit observations.
- An authorized reviewer can finalize the diagnostic report.
- The physician can retrieve the report after passing authorization checks.
- The patient can review relevant sharing history.
- Selected consent, workflow and integrity events are committed to Hyperledger Fabric.
- Blockchain transactions can be independently verified.
- Clinical data remain off-chain.
- Automated tests demonstrate the expected authorization and workflow behaviour.
- The complete frontend communicates with the actual backend and infrastructure.

# 15. HOW TO WORK WITH ME

I am a CSE engineering student developing this as a final-year research project.

I need working software, not just explanations.

Work systematically. Maintain a clear record of implemented components, remaining components, test results and known limitations.

If you have access to my project files and terminal environment, inspect, modify, execute and test them directly.

If you are operating in a chat-only environment, create complete files and provide exact paths and commands. Do not pretend to have executed code you have not run.

When an architectural decision is necessary, use the most defensible engineering choice consistent with my abstract. Ask me only when a genuinely essential decision cannot be resolved responsibly.

Prioritize correctness, security, interoperability and research validity over superficial UI polish.

**FINAL INSTRUCTION: Build WiraChain as the actual secure, consent-aware FHIR and permissioned-blockchain healthcare data exchange framework described in my abstract. Do not downgrade it into a basic hospital management application.**# MASTER DEVELOPMENT PROMPT — WIRACHAIN

## Project Title
**A SECURE, CONSENT-AWARE FHIR AND PERMISSIONED BLOCKCHAIN FRAMEWORK FOR INTEROPERABLE HEALTHCARE DATA EXCHANGE AMONG PATIENTS, PHYSICIANS AND CLINICAL LABORATORIES**

Act as a senior software architect, healthcare interoperability engineer, cybersecurity engineer, blockchain developer, database architect and full-stack development lead.

Your responsibility is to DESIGN, IMPLEMENT, TEST AND DELIVER a complete, functional, integrated full-stack research prototype called **WiraChain**, strictly aligned with the attached project abstract.

This is not a generic hospital management system, patient CRUD application, appointment booking platform or simple role-based dashboard.

I want the actual research concept implemented end to end.

I am providing:
1. My original project abstract, which is the authoritative statement of requirements.
2. My existing project ZIP, which contains an earlier implementation. Treat it as legacy reference material. Inspect it, reuse genuinely useful components where appropriate, but do not allow its limitations to determine the new architecture.

Do not merely generate a project plan, architecture document, UI mockup or isolated code snippets. Build the complete application.

---

# 1. CORE RESEARCH OBJECTIVE

Build a secure, consent-aware healthcare information exchange framework that connects:

- Patients
- Physicians
- Clinical laboratories
- Laboratory technicians
- Administrators

The system must provide interoperable healthcare information exchange using HL7 FHIR resources, enforce fine-grained patient-controlled consent, implement secure laboratory workflows, and use Hyperledger Fabric as a genuine permissioned blockchain for selected audit, consent and integrity events.

Clinical data must remain off-chain in secure storage. Blockchain must provide tamper-evident provenance, not act as the clinical database.

# 2. MANDATORY TECHNOLOGY STACK

Use the following technologies:

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Backend | Python FastAPI |
| Identity management | Keycloak |
| Authentication | OAuth 2.0 / OpenID Connect |
| Healthcare interoperability | HL7 FHIR R4 |
| FHIR server | HAPI FHIR |
| Application database | PostgreSQL |
| Blockchain | Hyperledger Fabric |
| Chaincode | Go |
| Frontend styling | Modern responsive CSS / Tailwind CSS |
| API documentation | OpenAPI / Swagger |
| Performance testing | k6 or Apache JMeter |
| Security testing | OWASP ZAP |
| API testing | Postman / automated tests |
| Containerization | Docker and Docker Compose |

Do not replace mandatory components with simulated equivalents.

In particular:
- A hash-chained PostgreSQL table is not Hyperledger Fabric.
- FHIR-shaped JSON is not sufficient evidence of HAPI FHIR interoperability.
- JWT authentication alone is not Keycloak integration.
- A mock blockchain service is not an implemented permissioned blockchain.

If an infrastructure component cannot run in the development environment, still implement its genuine integration, provide reproducible deployment configuration and clearly document the limitation. Never falsely claim it is operational.

Use FHIR R4 consistently throughout the implementation.

# 3. PATIENT-CONTROLLED CONSENT MANAGEMENT

This is one of the most important parts of WiraChain.

Implement a dedicated consent management engine.

Patients must be able to:

1. View their healthcare information.
2. Select a specific physician.
3. Select the categories or specific resources the physician may access.
4. Grant permission for a defined period.
5. Set a maximum access duration of 30 days.
6. View active permissions.
7. Revoke permission before its expiration.
8. Review expired and revoked permissions.
9. View who accessed their records, when and for what purpose.

The backend must enforce these permissions.

Required rules:

- Default-deny authorization.
- Consent must be specific to the patient and authorized physician.
- Consent must include permitted resource scope.
- Consent must include validity start and end times.
- The server must enforce the 30-day maximum.
- Expired consent must automatically become ineffective.
- Early revocation must immediately prevent subsequent access.
- The frontend must never be trusted to enforce authorization.
- Cached authorization must not bypass revocation.
- Every relevant consent action must generate an auditable event.

Implement the FHIR R4 Consent resource and map its lifecycle correctly to the application's consent states.

Do not confuse authentication, RBAC, resource assignment and patient consent. They are separate authorization requirements.

# 4. FHIR INTEROPERABILITY

Integrate a real HAPI FHIR R4 server.

Implement and validate these FHIR resources:

- Patient
- Practitioner
- Organization
- ServiceRequest
- Specimen
- Observation
- DiagnosticReport
- Consent

Ensure correct references between resources.

Examples:
- A ServiceRequest references the patient, requesting practitioner and performing organization.
- A Specimen is associated with the relevant laboratory request.
- Observations reference the patient and appropriate specimen or request.
- DiagnosticReport references the relevant ServiceRequest and Observation resources.
- Consent references the patient and authorized practitioner.

Use HAPI FHIR for resource validation, persistence and retrieval.

Provide:
- FHIR resource creation.
- FHIR resource retrieval.
- FHIR resource updates with version handling.
- Reference validation.
- Resource-level authorization.
- FHIR API integration tests.

Do not simply create arbitrary JSON objects and call them FHIR resources.

# 5. ORDERED LABORATORY WORKFLOW

This must be a real workflow engine, not unrelated CRUD forms.

Implement this complete process:

### Stage 1 — Patient
The patient has a healthcare identity and can grant a physician limited access to selected medical information.

### Stage 2 — Physician
The physician:
- Views records authorized by the patient.
- Creates a laboratory test request.
- Generates a FHIR ServiceRequest.
- Assigns the request to a laboratory.
- Tracks request status.
- Reviews finalized reports.

### Stage 3 — Laboratory
The laboratory:
- Receives laboratory requests.
- Verifies the request.
- Accepts or rejects requests.
- Assigns accepted requests to authorized technicians.
- Tracks specimen processing.

### Stage 4 — Laboratory technician
The technician:
- Views only assigned laboratory work.
- Accepts assigned work.
- Registers specimens.
- Updates processing status.
- Submits observations and test results.
- Hands the completed work to an authorized laboratory reviewer.

### Stage 5 — Laboratory reviewer
The authorized reviewer:
- Reviews submitted results.
- Validates the report.
- Finalizes the DiagnosticReport.
- Records the finalization event.

### Stage 6 — Physician
The physician:
- Receives the finalized report.
- Passes the consent authorization check.
- Reviews observations and diagnostic results.
- Records clinical review.

### Stage 7 — Patient
The patient:
- Views authorized reports.
- Reviews access history.
- Controls future sharing through consent.

Implement explicit workflow states and valid state transitions.

Example:

REQUESTED → ACCEPTED → ASSIGNED → SPECIMEN_REGISTERED → PROCESSING → RESULTS_SUBMITTED → REVIEWED → FINALIZED → PHYSICIAN_REVIEWED

Reject invalid transitions.

Enforce actor identity, role, organization membership and assignment at every transition.

A technician must not be able to process an unassigned request or finalize a report without appropriate authorization.

# 6. HYPERLEDGER FABRIC — REAL BLOCKCHAIN IMPLEMENTATION

Hyperledger Fabric is mandatory.

Build a genuine permissioned network suitable for a research prototype.

Include:
- Provider organization.
- Laboratory organization.
- Fabric peers.
- Membership Service Provider identities.
- Ordering service.
- Channels.
- Endorsement policies.
- Go chaincode.
- Fabric Gateway integration.

Design chaincode for selected events:

1. ConsentGranted
2. ConsentRevoked
3. ConsentExpired
4. LaboratoryRequestAccepted
5. TechnicianAssigned
6. SpecimenRegistered
7. DiagnosticReportFinalized
8. ClinicalRecordIntegrityUpdated
9. AuthorizedRecordAccess

Each event must contain carefully selected metadata, pseudonymous references and cryptographic integrity evidence.

Do not store identifiable clinical records on-chain.

Keep the following off-chain:
- Patient names.
- Contact information.
- Medical history.
- Diagnostic reports.
- Laboratory observations.
- Prescriptions.
- Clinical documents.

Implement:
- Transaction submission.
- Endorsement.
- Commit confirmation.
- Transaction ID tracking.
- Ledger event retrieval.
- Integrity verification.
- Provenance history.

Use a transactional outbox pattern between PostgreSQL and Fabric.

Do not claim an event has been recorded on-chain until Fabric confirms successful commit.

The application must distinguish pending, committed and failed ledger events.

Blockchain should complement the consent engine, not replace access-control enforcement.

# 7. KEYCLOAK AND SECURITY

Configure Keycloak with:
- WiraChain realm.
- React frontend client.
- FastAPI backend audience.
- OAuth 2.0 / OIDC.
- Authorization Code Flow with PKCE.
- JWT signature verification.
- Role mapping.
- Token expiry handling.
- Refresh-token handling where appropriate.

Required roles:

PATIENT
PHYSICIAN
LAB_TECHNICIAN
LAB_SUPERVISOR
ADMIN

Implement backend security checks for:
- Authentication.
- Role-based authorization.
- Organization membership.
- Resource ownership.
- Laboratory assignment.
- Patient consent.
- Token validity.
- Resource-level access.

Also implement:
- Secure password and identity management through Keycloak.
- Input validation.
- SQL injection prevention.
- Rate limiting for sensitive endpoints.
- Secure CORS configuration.
- Safe error responses.
- Secrets through environment variables.
- Audit logging.
- Secure document access.

Never hardcode production credentials or secrets.

# 8. DATABASE DESIGN

Design a normalized PostgreSQL schema for application-level data.

Include entities for:
- User profiles.
- Organizations.
- Patients.
- Practitioners.
- Laboratories.
- Technicians.
- Consent records.
- Consent scopes.
- Laboratory requests.
- Technician assignments.
- Specimens.
- Workflow transitions.
- Clinical resource references.
- Audit events.
- Blockchain transaction references.
- Transactional outbox events.

Use appropriate:
- Primary keys.
- Foreign keys.
- Constraints.
- Indexes.
- Timestamps.
- Database migrations.
- Transaction management.

HAPI FHIR should manage its own FHIR persistence. Avoid creating competing duplicate clinical databases without a clear reason.

# 9. COMPLETE FRONTEND

Build a polished, modern, professional healthcare interoperability application.

The interface must reflect the seriousness of a secure clinical information exchange platform.

Do not create a generic template dashboard.

Create separate experiences for each role.

### Patient portal
- Patient profile.
- Healthcare record overview.
- Consent management.
- Grant access screen.
- Resource-level permission selection.
- Access duration selector.
- Active consent list.
- Revocation controls.
- Consent history.
- Record access history.
- Blockchain provenance verification view.

### Physician portal
- Physician profile.
- Authorized patient list.
- Patient record viewer.
- Consent status indicators.
- Laboratory request creation.
- ServiceRequest tracking.
- Laboratory result viewer.
- DiagnosticReport viewer.
- Clinical review history.

### Laboratory portal
- Incoming requests.
- Request acceptance/rejection.
- Technician assignment.
- Workload overview.
- Specimen tracking.
- Processing status.
- Report validation.
- Finalization workflow.

### Technician portal
- Assigned work queue.
- Specimen registration.
- Processing updates.
- Observation entry.
- Submission to laboratory reviewer.
- Assignment and workflow history.

### Administrator portal
- User and organization management.
- Role assignment.
- System activity.
- Security events.
- Workflow monitoring.
- Blockchain transaction monitoring.

Every screen must connect to actual backend functionality.

Implement:
- Loading states.
- Error states.
- Form validation.
- Empty states.
- Confirmation dialogs.
- Responsive layouts.
- Accessible components.
- Clear navigation.
- Useful notifications.

Avoid decorative buttons that do nothing.

# 10. AUDIT AND PROVENANCE

Implement a complete audit strategy.

Record:
- Authentication-related security events.
- Consent creation.
- Consent modification.
- Consent revocation.
- Access granted or denied.
- Laboratory request creation.
- Technician assignment.
- Specimen processing.
- Observation submission.
- Diagnostic report finalization.
- Clinical review.
- Blockchain transaction submission and confirmation.

Audit entries should identify the actor, action, timestamp, relevant resource reference, outcome and correlation ID.

Do not put sensitive patient information into application logs or blockchain events unnecessarily.

Provide a patient-accessible view of relevant record-sharing history.

# 11. TESTING AND RESEARCH EVALUATION

Build a reproducible evaluation suite.

### Functional testing
Test every role and major workflow.

### Consent testing
Test:
- No consent.
- Valid consent.
- Expired consent.
- Revoked consent.
- Resource outside authorized scope.
- Unauthorized physician.
- Consent duration greater than 30 days.
- Attempts to bypass authorization through direct API calls.

### Laboratory workflow testing
Test:
- Invalid state transitions.
- Unassigned technician access.
- Unauthorized report finalization.
- Duplicate request submissions.
- Invalid specimen references.

### Security testing
Test:
- Invalid and expired JWTs.
- Role escalation attempts.
- Unauthorized resource access.
- SQL injection attempts.
- Rate limiting.
- Broken object-level authorization.
- Consent bypass attempts.

Use safe, controlled tests against the local development environment.

### FHIR testing
Validate required resources and references using HAPI FHIR.

### Blockchain testing
Measure:
- Transaction submission latency.
- Commit latency.
- Transaction throughput.
- Ledger integrity verification.
- Blockchain integration overhead.

### Performance testing
Use k6 or JMeter.

Evaluate increasing concurrency and report:
- Requests per second.
- Average latency.
- p95 latency.
- Error rate.
- Resource utilization.

Compare an off-chain baseline with blockchain-enabled event processing.

Never invent test results. Generate reports from actual test executions.

# 12. DEVELOPMENT AND DELIVERY RULES

These instructions are mandatory.

1. First inspect the existing ZIP and the abstract thoroughly.
2. Produce a requirement-to-implementation mapping.
3. Establish the new architecture.
4. Create the repository structure.
5. Implement the backend and database.
6. Integrate Keycloak.
7. Integrate HAPI FHIR.
8. Implement the consent engine.
9. Implement the laboratory workflow.
10. Integrate Hyperledger Fabric.
11. Build the complete frontend.
12. Integrate all components.
13. Run automated tests.
14. Fix implementation errors.
15. Prepare deployment documentation.
16. Prepare research evaluation documentation.

Do not stop after creating the architecture.

Do not stop after implementing authentication.

Do not stop after implementing a basic dashboard.

Do not replace actual functionality with mock responses.

Do not use fake blockchain transactions.

Do not claim unimplemented features are complete.

Do not leave critical TODOs while declaring the project finished.

Use synthetic healthcare data for development and testing.

Use environment configuration rather than hardcoded secrets.

Keep the application modular, maintainable and documented.

Because the development machine may have limited RAM, provide lightweight development profiles and allow infrastructure components to be started independently. Do not assume all services can run simultaneously on a low-resource laptop.

# 13. REQUIRED FINAL DELIVERABLES

Deliver:

1. Complete frontend source code.
2. Complete FastAPI backend.
3. PostgreSQL schema and migrations.
4. Keycloak realm and client configuration.
5. HAPI FHIR integration.
6. Consent management engine.
7. Laboratory workflow engine.
8. Hyperledger Fabric network configuration.
9. Go chaincode.
10. Fabric integration service.
11. Docker Compose configurations.
12. Synthetic test data and seed scripts.
13. Automated test suites.
14. API documentation.
15. Architecture diagrams.
16. Deployment and setup guide for Linux.
17. Security testing report.
18. Performance evaluation report generated from real executions.
19. Research implementation mapping against my original abstract.
20. Complete README with exact setup, startup, test and troubleshooting commands.

# 14. ACCEPTANCE CRITERIA

The project is not complete unless all these scenarios work:

- A patient can grant a specific physician access to selected records for a limited period.
- The system rejects consent durations exceeding 30 days.
- The physician can access only authorized resources.
- Consent expiration blocks subsequent access.
- Early revocation blocks subsequent access.
- A physician can create a FHIR laboratory request.
- A laboratory can accept and assign that request.
- An authorized technician can register specimens and submit observations.
- An authorized reviewer can finalize the diagnostic report.
- The physician can retrieve the report after passing authorization checks.
- The patient can review relevant sharing history.
- Selected consent, workflow and integrity events are committed to Hyperledger Fabric.
- Blockchain transactions can be independently verified.
- Clinical data remain off-chain.
- Automated tests demonstrate the expected authorization and workflow behaviour.
- The complete frontend communicates with the actual backend and infrastructure.

# 15. HOW TO WORK WITH ME

I am a CSE engineering student developing this as a final-year research project.

I need working software, not just explanations.

Work systematically. Maintain a clear record of implemented components, remaining components, test results and known limitations.

If you have access to my project files and terminal environment, inspect, modify, execute and test them directly.

If you are operating in a chat-only environment, create complete files and provide exact paths and commands. Do not pretend to have executed code you have not run.

When an architectural decision is necessary, use the most defensible engineering choice consistent with my abstract. Ask me only when a genuinely essential decision cannot be resolved responsibly.

Prioritize correctness, security, interoperability and research validity over superficial UI polish.

**FINAL INSTRUCTION: Build WiraChain as the actual secure, consent-aware FHIR and permissioned-blockchain healthcare data exchange framework described in my abstract. Do not downgrade it into a basic hospital management application.**