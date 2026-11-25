A SECURE, CONSENT-AWARE FHIR AND PERMISSIONED BLOCKCHAIN
FRAMEWORK FOR INTEROPERABLE HEALTHCARE DATA EXCHANGE
AMONG PATIENTS, PHYSICIANS AND CLINICAL LABORATORIES
Abstract:
Healthcare information is increasingly distributed across patients, physicians, hospitals, and clinical laboratories,
creating challenges in interoperability, secure data sharing, patient consent, and auditability. Conventional healthcare
systems often rely on isolated databases and organization-specific interfaces, which can make controlled exchange of
laboratory requests and diagnostic reports difficult. Secure and interoperable exchange is particularly important in the
workflow connecting patients, doctors, and laboratory technicians. This project proposes a secure, consent-aware
healthcare data exchange framework based on HL7 Fast Healthcare Interoperability Resources (FHIR) and a
permissioned blockchain. The proposed framework uses FHIR resources to standardize the exchange of patient
information, laboratory test requests, observations, specimens, and diagnostic reports between healthcare participants.
A fine-grained consent mechanism enables patients to grant specific doctors access to selected healthcare resources
for a limited period of up to 30 days, with automatic expiry and early revocation. Role-based access control ensures
that doctors, laboratory technicians, patients, and administrators receive only the permissions required for their
responsibilities. Clinical data are maintained off-chain in secure storage, while the permissioned blockchain records
selected consent, audit, and integrity events to provide tamper-evident provenance. The system will be implemented as
a research prototype with patient, doctor, and laboratory interfaces, a FHIR-based API layer, secure authentication,
consent management, and laboratory workflow integration. The prototype will be evaluated through functional testing,
controlled penetration testing, and scalability and performance experiments under increasing workloads. The
evaluation will examine unauthorized-access prevention, consent expiry and revocation, FHIR interoperability,
auditability, response time, throughput, and blockchain overhead. The proposed framework aims to demonstrate a
practical approach for secure, patient-controlled, and interoperable healthcare data exchange while identifying the
security and scalability considerations involved in integrating FHIR and permissioned blockchain technologies.
Recommended Data / Standards: HL7 FHIR R4/R5 resources including Patient, Practitioner, ServiceRequest, Specimen,
Observation, DiagnosticReport and Consent; synthetic patient and laboratory data for prototype evaluation.
Implementation Tools: React.js, FastAPI/Python, HAPI FHIR, PostgreSQL, Keycloak, OAuth 2.0/OpenID Connect,
Hyperledger Fabric, Docker, Git/GitHub, Postman, OWASP ZAP, Burp Suite Community Edition, Apache JMeter or k6, Visual
Studio Code, Linux/Windows.