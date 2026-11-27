import { useEffect, useState } from 'react'
import { api } from '../api'
import TransferStatus from '../components/TransferStatus'

export default function DoctorDashboard({ token }) {
  const [patients, setPatients] = useState([])
  const [laboratories, setLaboratories] = useState([])
  const [requests, setRequests] = useState([])
  const [reports, setReports] = useState([])
  const [reviewingId, setReviewingId] = useState('')
  const [creatingRequest, setCreatingRequest] = useState(false)
  const [requestKey, setRequestKey] = useState(() => crypto.randomUUID())
  const [form, setForm] = useState({
    patient_email: '',
    lab_email: '',
    test_code: '2345-7',
    test_display: 'Glucose [Mass/volume] in Serum or Plasma',
    note: '',
  })
  const [message, setMessage] = useState('')
  const [err, setErr] = useState('')
  const [careConnections, setCareConnections] = useState([])
  const [recordRequests, setRecordRequests] = useState([])
  const [providerAffiliations, setProviderAffiliations] = useState([])
  const [crossHospitalExchanges, setCrossHospitalExchanges] = useState([])
  const [registryOrganizations, setRegistryOrganizations] = useState([])
  const [crossHospitalForm, setCrossHospitalForm] = useState({ patient_id: '', source_organization_id: '', resource_types: ['Document'], requested_duration_days: 30, reason: '' })
  const [recordRequestForm, setRecordRequestForm] = useState({ patient_id: '', organization_id: '', resource_types: ['Document'], requested_duration_days: 30, reason: '' })

  async function refresh() {
    try {
      const [p, l, r, d, c, q, affiliations, exchanges, organizations] = await Promise.all([
        api.accessiblePatients(token),
        api.listLaboratories(token),
        api.listServiceRequests(token),
        api.listDiagnosticReports(token),
        api.myProviderCareConnections(token),
        api.myProviderRecordRequests(token),
        api.myProviderAffiliations(token),
        api.myProviderCrossHospitalExchanges(token),
        api.registryOrganizations(token),
      ])
      setPatients(p); setLaboratories(l); setRequests(r); setReports(d); setCareConnections(c); setRecordRequests(q); setProviderAffiliations(affiliations); setCrossHospitalExchanges(exchanges); setRegistryOrganizations(organizations)
      if (!form.lab_email && l.length > 0) setForm((current) => ({ ...current, lab_email: l[0].email }))
    } catch (e) { setErr(e.message) }
  }

  useEffect(() => { refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function submitRequest(e) {
    e.preventDefault()
    setErr(''); setMessage('')
    setCreatingRequest(true)
    try {
      await api.createServiceRequest(form, token, requestKey)
      setMessage('Lab test request created.')
      setRequestKey(crypto.randomUUID())
      refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setCreatingRequest(false)
    }
  }

  async function respondConnection(connection, decision) {
    setErr(''); setMessage('')
    try {
      await api.respondCareConnection(connection.id, {
        decision,
        response: decision === 'ACCEPTED' ? 'I accept this care connection.' : 'I am unable to accept this care connection.',
      }, token)
      setMessage('Care connection response saved.')
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  async function submitCrossHospitalExchange(e) {
    e.preventDefault()
    setErr(''); setMessage('')
    const requestingAffiliation = providerAffiliations.find((item) => item.status === 'ACTIVE')
    if (!requestingAffiliation) {
      setErr('An active organization affiliation is required.')
      return
    }
    try {
      await api.createCrossHospitalExchange({
        patient_id: crossHospitalForm.patient_id,
        requesting_organization_id: requestingAffiliation.organization_id,
        source_organization_id: crossHospitalForm.source_organization_id,
        resource_types: crossHospitalForm.resource_types,
        requested_duration_days: Number(crossHospitalForm.requested_duration_days),
        reason: crossHospitalForm.reason,
      }, token)
      setMessage('Cross-hospital exchange request sent for patient approval.')
      setCrossHospitalForm({ patient_id: '', source_organization_id: '', resource_types: ['Document'], requested_duration_days: 30, reason: '' })
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  async function submitRecordRequest(e) {
    e.preventDefault()
    setErr(''); setMessage('')
    try {
      await api.createRecordRequest(recordRequestForm, token)
      setMessage('Record-access request sent for patient approval.')
      setRecordRequestForm({ patient_id: '', organization_id: '', resource_types: ['Document'], requested_duration_days: 30, reason: '' })
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  async function cancelRecordRequest(requestId) {
    setErr(''); setMessage('')
    try {
      await api.cancelRecordRequest(requestId, token)
      setMessage('Record-access request cancelled.')
      await refresh()
    } catch (e) { setErr(e.message) }
  }

  async function reviewReport(requestId) {
    setErr('')
    setMessage('')
    setReviewingId(requestId)
    try {
      await api.recordClinicalReview(requestId, token)
      setMessage('Clinical review recorded.')
      await refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setReviewingId('')
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <p className="eyebrow">PATIENT CONNECTIONS</p><h2>Incoming care connections</h2>
        {careConnections.length === 0 ? <p className="muted">No patient care connections have been initiated.</p> : careConnections.map((connection) => <div className="report" key={connection.id}><strong>{connection.patient_name}</strong><span className="muted">{connection.organization_name} · {connection.status}</span><span>{connection.reason}</span>{connection.status === 'INITIATED' && <div className="registry-actions"><button className="btn-primary" onClick={() => respondConnection(connection, 'ACCEPTED')}>Accept</button><button className="btn-ghost" onClick={() => respondConnection(connection, 'DECLINED')}>Decline</button></div>}</div>)}
      </section>

      <section className="card">
        <p className="eyebrow">CROSS-HOSPITAL EXCHANGE</p><h2>Request records from another hospital</h2>
        <form onSubmit={submitCrossHospitalExchange} className="stacked-form">
          <label>Patient<select required value={crossHospitalForm.patient_id} onChange={(e) => setCrossHospitalForm((f) => ({ ...f, patient_id: e.target.value }))}><option value="">Choose patient</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name}</option>)}</select></label>
          <label>Source hospital<select required value={crossHospitalForm.source_organization_id} onChange={(e) => setCrossHospitalForm((f) => ({ ...f, source_organization_id: e.target.value }))}><option value="">Choose source organization</option>{registryOrganizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.display_name}</option>)}</select></label>
          <fieldset className="scope-fieldset"><legend>Requested record types</legend><div className="scope-list">{['Document', 'DiagnosticReport', 'Observation', 'ServiceRequest'].map((scope) => <label className="scope-option" key={scope}><input type="checkbox" checked={crossHospitalForm.resource_types.includes(scope)} onChange={(e) => setCrossHospitalForm((f) => ({ ...f, resource_types: e.target.checked ? [...f.resource_types, scope] : f.resource_types.filter((item) => item !== scope) }))} />{scope}</label>)}</div></fieldset>
          <label>Requested duration (days)<input type="number" min="1" max="30" required value={crossHospitalForm.requested_duration_days} onChange={(e) => setCrossHospitalForm((f) => ({ ...f, requested_duration_days: Number(e.target.value) }))} /></label>
          <label>Care reason<textarea rows="3" required minLength="3" maxLength="1000" value={crossHospitalForm.reason} onChange={(e) => setCrossHospitalForm((f) => ({ ...f, reason: e.target.value }))} /></label>
          <button className="btn-primary" type="submit" disabled={!crossHospitalForm.patient_id || !crossHospitalForm.source_organization_id || !crossHospitalForm.resource_types.length || !crossHospitalForm.reason}>Send patient approval request</button>
        </form>
        {crossHospitalExchanges.length > 0 && <div className="registry-list">{crossHospitalExchanges.map((exchange) => <div className="report" key={exchange.id}><strong>{exchange.requesting_organization_name} → {exchange.source_organization_name}</strong><span className="muted">{exchange.patient_name} · {exchange.status}</span><span>{exchange.resource_types.join(', ')} · {exchange.requested_duration_days} days</span>{exchange.status === 'APPROVED' && <>{exchange.resource_types.includes('Document') && <button className="btn-ghost" type="button" onClick={async () => { try { const documents = await api.crossHospitalExchangeDocuments(exchange.id, token); setMessage(documents.length ? `${documents.length} approved source document(s) available.` : 'No approved source documents are available.') } catch (e) { setErr(e.message) } }}>View approved source documents</button>}</>}</div>)}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">RECORD ACCESS</p><h2>Request specific patient records</h2>
        <form onSubmit={submitRecordRequest} className="stacked-form">
          <label>Patient<select required value={recordRequestForm.patient_id} onChange={(e) => setRecordRequestForm((f) => ({ ...f, patient_id: e.target.value }))}><option value="">Choose a patient who may be contacted</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name} · {patient.email}</option>)}</select></label>
          <label>Affiliated organization<select required value={recordRequestForm.organization_id} onChange={(e) => setRecordRequestForm((f) => ({ ...f, organization_id: e.target.value }))}><option value="">Choose organization</option>{providerAffiliations.filter((item) => item.status === 'ACTIVE').map((item) => <option key={item.organization_id} value={item.organization_id}>{item.organization_name}</option>)}</select></label>
          <fieldset className="scope-fieldset"><legend>Records requested</legend><div className="scope-list">{['Document', 'Patient', 'ServiceRequest', 'Specimen', 'Observation', 'DiagnosticReport'].map((scope) => <label className="scope-option" key={scope}><input type="checkbox" checked={recordRequestForm.resource_types.includes(scope)} onChange={(e) => setRecordRequestForm((f) => ({ ...f, resource_types: e.target.checked ? [...f.resource_types, scope] : f.resource_types.filter((item) => item !== scope) }))} />{scope}</label>)}</div></fieldset>
          <label>Requested duration (days)<input type="number" min="1" max="30" required value={recordRequestForm.requested_duration_days} onChange={(e) => setRecordRequestForm((f) => ({ ...f, requested_duration_days: Number(e.target.value) }))} /></label>
          <label>Care reason<textarea rows="3" required minLength="3" maxLength="1000" value={recordRequestForm.reason} onChange={(e) => setRecordRequestForm((f) => ({ ...f, reason: e.target.value }))} /></label>
          <button className="btn-primary" type="submit" disabled={!recordRequestForm.patient_id || !recordRequestForm.organization_id || !recordRequestForm.resource_types.length || !recordRequestForm.reason}>Send for patient approval</button>
        </form>
      </section>

      <section className="card">
        <p className="eyebrow">OUTGOING RECORD REQUESTS</p><h2>Patient decisions</h2>
        {recordRequests.length === 0 ? <p className="muted">No record-access requests sent.</p> : recordRequests.map((request) => <div className="report" key={request.id}><strong>{request.patient_name}</strong><span className="muted">{request.organization_name} · {request.status}</span><span>{request.resource_types.join(', ')} · {request.requested_duration_days} days</span><span>{request.reason}</span>{request.status === 'REQUESTED' && <button className="btn-ghost" onClick={() => cancelRecordRequest(request.id)}>Cancel request</button>}</div>)}
        {message && <div className="success" role="status">{message}</div>}
        {err && <div className="error" role="alert">{err}</div>}
      </section>
      <section className="card">
        <h2>Patients who granted access</h2>
        {patients.length === 0 && <p className="muted">No patient has granted you access yet.</p>}
        {patients.length > 0 && (
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Name</th><th>Email</th><th>Allowed records</th><th>Access expires</th></tr></thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id}>
                  <td>{p.full_name}</td>
                  <td>{p.email}</td>
                  <td>{p.resource_types.join(', ')}</td>
                  <td>{new Date(p.consent_expires_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </section>

      <section className="card">
        <h2>Request a lab test</h2>
        <form onSubmit={submitRequest} className="stacked-form">
          <label>Patient email
            <input required list="consented-patients" type="email" placeholder="Choose a patient who granted access" value={form.patient_email} onChange={(e) => setForm((f) => ({ ...f, patient_email: e.target.value }))} />
            <datalist id="consented-patients">{patients.map((patient) => <option key={patient.id} value={patient.email}>{patient.full_name}</option>)}</datalist>
          </label>
          <label>Laboratory
            <select required value={form.lab_email} onChange={(e) => setForm((f) => ({ ...f, lab_email: e.target.value }))}>
              <option value="" disabled>Select a laboratory</option>
              {laboratories.map((lab) => <option key={lab.id} value={lab.email}>{lab.name}</option>)}
            </select>
          </label>
          <label>Test (LOINC display name)
            <input required value={form.test_display} onChange={(e) => setForm((f) => ({ ...f, test_display: e.target.value }))} />
          </label>
          <label>Note
            <input value={form.note} onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))} />
          </label>
          <button className="btn-primary" type="submit" disabled={creatingRequest || laboratories.length === 0}>
            {creatingRequest ? 'Creating…' : 'Create lab request'}
          </button>
          {creatingRequest && <TransferStatus>Sending request</TransferStatus>}
        </form>
        {message && <div className="success">{message}</div>}
        {err && <div className="error">{err}</div>}
      </section>

      <section className="card">
        <h2>My requests</h2>
        {requests.length === 0 && <p className="muted">No requests yet.</p>}
        {requests.map((r) => (
          <div className="report" key={r.id}>
            <strong>{r.resource.code?.text}</strong>
            <span className="muted">Workflow: {r.workflow_status?.replaceAll('_', ' ').toLowerCase() || r.resource.status}</span>
            {r.workflow_status === 'FINALIZED' && (
              <button className="btn-ghost" disabled={reviewingId === r.id} onClick={() => reviewReport(r.id)}>
                {reviewingId === r.id ? 'Saving…' : 'Record clinical review'}
              </button>
            )}
                {reviewingId === r.id && <TransferStatus>Recording clinical review</TransferStatus>}
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Reports received</h2>
        {reports.length === 0 && <p className="muted">No reports yet.</p>}
        {reports.map((r) => (
          <div className="report" key={r.id}>
            <strong>{r.resource.conclusion}</strong>
            <span className="muted">Finalized report</span>
          </div>
        ))}
      </section>
    </div>
  )
}
