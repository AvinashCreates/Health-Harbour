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

  async function refresh() {
    try {
      const [p, l, r, d] = await Promise.all([
        api.accessiblePatients(token),
        api.listLaboratories(token),
        api.listServiceRequests(token),
        api.listDiagnosticReports(token),
      ])
      setPatients(p); setLaboratories(l); setRequests(r); setReports(d)
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
