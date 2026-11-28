const configuredBase = import.meta.env.VITE_API_BASE
const defaultApiHost = window.location.hostname === 'localhost'
  ? '127.0.0.1'
  : window.location.hostname || '127.0.0.1'
const API_BASE = (configuredBase || `${window.location.protocol}//${defaultApiHost}:8000`).replace(/\/+$/, '')
const REQUEST_TIMEOUT_MS = 15000

async function request(path, { method = 'GET', body, token, headers: extraHeaders = {} } = {}) {
  const headers = { ...extraHeaders }
  if (token) headers.Authorization = `Bearer ${token}`
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
      signal: controller.signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      const detail = typeof data.detail === 'string' ? data.detail : data.detail ? JSON.stringify(data.detail) : ''
      throw new Error(detail || `Request failed (${res.status})`)
    }
    if (res.status === 204) return null
    if (res.headers.get('content-type')?.includes('application/json')) return await res.json()
    return res
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`The API did not respond within ${REQUEST_TIMEOUT_MS / 1000} seconds. Check that the backend is running at ${API_BASE}.`)
    }
    if (error instanceof TypeError) {
      throw new Error(`Could not connect to the API at ${API_BASE}. Check the backend health endpoint and frontend API URL.`)
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  me: (token) => request('/auth/me', { token }),
  provisionOidcPatient: (token) => request('/auth/oidc/provision-patient', { method: 'POST', token }),

  getPatient: (id, token) => request(`/fhir/Patient/${id}`, { token }),
  accessiblePatients: (token) => request('/fhir/patients/accessible', { token }),
  listDocumentPatients: (token) => request('/files/patients', { token }),
  listPhysicians: (token) => request('/fhir/physicians', { token }),
  listLaboratories: (token) => request('/fhir/laboratories', { token }),
  createServiceRequest: (payload, token, idempotencyKey) => request('/fhir/ServiceRequest', {
    method: 'POST',
    body: payload,
    token,
    headers: { 'Idempotency-Key': idempotencyKey },
  }),
  listServiceRequests: (token) => request('/fhir/ServiceRequest', { token }),
  createDiagnosticReport: (payload, token) => request('/fhir/DiagnosticReport', { method: 'POST', body: payload, token }),
  listDiagnosticReports: (token) => request('/fhir/DiagnosticReport', { token }),
  acceptServiceRequest: (id, token) => request(`/fhir/ServiceRequest/${id}/accept`, { method: 'POST', token }),
  assignTechnician: (id, technician_email, token) => request(`/fhir/ServiceRequest/${id}/assign`, { method: 'POST', body: { technician_email }, token }),
  registerSpecimen: (id, payload, token) => request(`/fhir/ServiceRequest/${id}/specimen`, { method: 'POST', body: payload, token }),
  startProcessing: (id, token) => request(`/fhir/ServiceRequest/${id}/processing`, { method: 'POST', token }),
  finalizeReport: (id, token) => request(`/fhir/ServiceRequest/${id}/finalize`, { method: 'POST', token }),
  amendDiagnosticReport: (id, payload, token) => request(`/fhir/DiagnosticReport/${encodeURIComponent(id)}/amend`, { method: 'POST', body: payload, token }),
  recordClinicalReview: (id, token) => request(`/fhir/ServiceRequest/${id}/physician-review`, { method: 'POST', token }),

  listFiles: (token) => request('/files', { token }),
  uploadFile: (file, { patient_id, service_request_id, category = 'clinical-record' } = {}, token) => {
    const body = new FormData()
    body.append('file', file)
    if (patient_id) body.append('patient_id', patient_id)
    if (service_request_id) body.append('service_request_id', service_request_id)
    body.append('category', category)
    return request('/files', { method: 'POST', body, token })
  },
  downloadFile: async (id, token) => {
    const response = await request(`/files/${encodeURIComponent(id)}/download`, { token })
    return response.blob()
  },
  deleteFile: (id, token) => request(`/files/${encodeURIComponent(id)}`, { method: 'DELETE', token }),

  grantConsent: (payload, token) => request('/consent/grant', { method: 'POST', body: payload, token }),
  revokeConsent: (id, token) => request(`/consent/revoke/${id}`, { method: 'POST', token }),
  myConsents: (token) => request('/consent/active', { token }),
  accessHistory: (token) => request('/consent/access-history', { token }),

  auditLog: (token) => request('/audit/log', { token }),
  auditVerify: (token) => request('/audit/verify', { token }),
  provisionUser: (payload, token) => request('/auth/users', { method: 'POST', body: payload, token }),
  addLabTechnician: (payload, token) => request('/auth/laboratory-memberships', { method: 'POST', body: payload, token }),
  listOrganizationMemberships: (token) => request('/auth/organization-memberships', { token }),
  addOrganizationPractitioner: (payload, token) => request('/auth/organization-memberships', { method: 'POST', body: payload, token }),
  removeOrganizationPractitioner: (id, token) => request(`/auth/organization-memberships/${encodeURIComponent(id)}`, { method: 'DELETE', token }),
  consentOrganizations: (token) => request('/consent/organizations', { token }),

  registryOrganizations: (token) => request('/api/v1/organizations', { token }),
  registryProviders: (token) => request('/api/v1/providers', { token }),
  myOrganizationApplications: (token) => request('/api/v1/organization-applications/me', { token }),
  submitOrganizationApplication: (payload, token) => request('/api/v1/organization-applications', { method: 'POST', body: payload, token }),
  myProviderApplications: (token) => request('/api/v1/provider-applications/me', { token }),
  myProviderProfile: (token) => request('/api/v1/providers/me', { token }),
  submitProviderApplication: (payload, token) => request('/api/v1/provider-applications', { method: 'POST', body: payload, token }),
  myProviderAffiliations: (token) => request('/api/v1/providers/me/affiliations', { token }),
  respondToAffiliation: (id, payload, token) => request(`/api/v1/affiliations/${encodeURIComponent(id)}/response`, { method: 'POST', body: payload, token }),
  managedOrganizations: (token) => request('/api/v1/my/organizations', { token }),
  organizationAffiliations: (organizationId, token) => request(`/api/v1/organizations/${encodeURIComponent(organizationId)}/affiliations`, { token }),
  providerCandidates: (organizationId, token) => request(`/api/v1/organizations/${encodeURIComponent(organizationId)}/provider-candidates`, { token }),
  inviteProvider: (organizationId, payload, token) => request(`/api/v1/organizations/${encodeURIComponent(organizationId)}/affiliations`, { method: 'POST', body: payload, token }),
  decideAffiliation: (organizationId, affiliationId, payload, token) => request(`/api/v1/organizations/${encodeURIComponent(organizationId)}/affiliations/${encodeURIComponent(affiliationId)}/decision`, { method: 'POST', body: payload, token }),
  adminOrganizationApplications: (token) => request('/api/v1/admin/organization-applications', { token }),
  decideOrganizationApplication: (id, payload, token) => request(`/api/v1/admin/organization-applications/${encodeURIComponent(id)}/decision`, { method: 'POST', body: payload, token }),
  adminProviderApplications: (token) => request('/api/v1/admin/provider-applications', { token }),
  decideProviderApplication: (id, payload, token) => request(`/api/v1/admin/provider-applications/${encodeURIComponent(id)}/decision`, { method: 'POST', body: payload, token }),
  adminAffiliations: (token) => request('/api/v1/admin/affiliations', { token }),
  organizationReviewHistory: (id, token) => request(`/api/v1/admin/organizations/${encodeURIComponent(id)}/history`, { token }),
  providerReviewHistory: (id, token) => request(`/api/v1/admin/providers/${encodeURIComponent(id)}/history`, { token }),
  affiliationHistory: (id, token) => request(`/api/v1/affiliations/${encodeURIComponent(id)}/history`, { token }),
  createCrossHospitalExchange: (payload, token) => request('/api/v1/cross-hospital/exchange-requests', { method: 'POST', body: payload, token }),
  myPatientCrossHospitalExchanges: (token) => request('/api/v1/cross-hospital/exchange-requests/me/patient', { token }),
  myProviderCrossHospitalExchanges: (token) => request('/api/v1/cross-hospital/exchange-requests/me/provider', { token }),
  decideCrossHospitalExchange: (id, payload, token) => request(`/api/v1/cross-hospital/exchange-requests/${encodeURIComponent(id)}/patient-decision`, { method: 'POST', body: payload, token }),
  crossHospitalExchangeDocuments: (id, token) => request(`/api/v1/cross-hospital/exchange-requests/${encodeURIComponent(id)}/documents`, { token }),
  downloadCrossHospitalExchangeDocument: async (exchangeId, documentId, token) => {
    const response = await request(`/api/v1/cross-hospital/exchange-requests/${encodeURIComponent(exchangeId)}/documents/${encodeURIComponent(documentId)}/download`, { token })
    return response.blob()
  },
  importCrossHospitalDocument: (exchangeId, documentId, token) => request(`/api/v1/cross-hospital/exchange-requests/${encodeURIComponent(exchangeId)}/documents/${encodeURIComponent(documentId)}/import`, { method: 'POST', token }),
  createPrescription: (payload, token) => request('/api/v1/prescriptions', { method: 'POST', body: payload, token }),
  transitionPrescription: (id, payload, token) => request(`/api/v1/prescriptions/${encodeURIComponent(id)}/transition`, { method: 'POST', body: payload, token }),
  myPatientPrescriptions: (token) => request('/api/v1/prescriptions/me/patient', { token }),
  myProviderPrescriptions: (token) => request('/api/v1/prescriptions/me/provider', { token }),
  createClinicalReview: (payload, token) => request('/api/v1/clinical-reviews', { method: 'POST', body: payload, token }),
  myPatientClinicalReviews: (token) => request('/api/v1/clinical-reviews/me/patient', { token }),
  myProviderClinicalReviews: (token) => request('/api/v1/clinical-reviews/me/provider', { token }),
 initiateCareConnection: (payload, token) => request('/api/v1/care-connections', { method: 'POST', body: payload, token }),
 myPatientCareConnections: (token) => request('/api/v1/care-connections/me/patient', { token }),
 myProviderCareConnections: (token) => request('/api/v1/care-connections/me/provider', { token }),
 respondCareConnection: (id, payload, token) => request(`/api/v1/care-connections/${encodeURIComponent(id)}/provider-response`, { method: 'POST', body: payload, token }),
 createRecordRequest: (payload, token) => request('/api/v1/record-requests', { method: 'POST', body: payload, token }),
 myProviderRecordRequests: (token) => request('/api/v1/record-requests/me/provider', { token }),
 myPatientRecordRequests: (token) => request('/api/v1/record-requests/me/patient', { token }),
 decideRecordRequest: (id, payload, token) => request(`/api/v1/record-requests/${encodeURIComponent(id)}/patient-decision`, { method: 'POST', body: payload, token }),
 cancelRecordRequest: (id, token) => request(`/api/v1/record-requests/${encodeURIComponent(id)}/cancel`, { method: 'POST', token }),
}
