const configuredBase = import.meta.env.VITE_API_BASE
const API_BASE = (configuredBase || `${window.location.protocol}//${window.location.hostname || 'localhost'}:8000`).replace(/\/+$/, '')

async function request(path, { method = 'GET', body, token, headers: extraHeaders = {} } = {}) {
  const headers = { ...extraHeaders }
  if (token) headers.Authorization = `Bearer ${token}`
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    const detail = typeof data.detail === 'string' ? data.detail : data.detail ? JSON.stringify(data.detail) : ''
    throw new Error(detail || `Request failed (${res.status})`)
  }
  if (res.status === 204) return null
  if (res.headers.get('content-type')?.includes('application/json')) return res.json()
  return res
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
}
