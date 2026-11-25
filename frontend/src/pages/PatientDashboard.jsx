import { useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'
import TransferStatus from '../components/TransferStatus'

export default function PatientDashboard({ token, user }) {
  const consentResourceTypes = ['Patient', 'ServiceRequest', 'Specimen', 'Observation', 'DiagnosticReport']
  const [patientResource, setPatientResource] = useState(null)
  const [physicians, setPhysicians] = useState([])
  const [consents, setConsents] = useState([])
  const [reports, setReports] = useState([])
  const [accessHistory, setAccessHistory] = useState([])
  const [grantForm, setGrantForm] = useState({
    doctor_email: '',
    duration_days: 30,
    resource_types: ['Patient', 'ServiceRequest', 'Observation', 'DiagnosticReport'],
  })
  const [message, setMessage] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  async function refresh() {
    setLoading(true)
    try {
      const [patient, doctors, myConsents, myReports, history] = await Promise.all([
        api.getPatient(user.id, token),
        api.listPhysicians(token),
        api.myConsents(token),
        api.listDiagnosticReports(token),
        api.accessHistory(token),
      ])
      setPatientResource(patient)
      setPhysicians(doctors)
      setConsents(myConsents)
      setReports(myReports)
      setAccessHistory(history)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function grant(e) {
    e.preventDefault()
    setErr(''); setMessage('')
    setSubmitting(true)
    try {
      await api.grantConsent(grantForm, token)
      setMessage(`Access granted to ${grantForm.doctor_email}`)
      setGrantForm({
        doctor_email: '',
        duration_days: 30,
        resource_types: ['Patient', 'ServiceRequest', 'Observation', 'DiagnosticReport'],
      })
      refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function revoke(id) {
    setErr('')
    if (!window.confirm('Revoke this doctor’s access now? They will lose access to these records immediately.')) return
    try {
      await api.revokeConsent(id, token)
      refresh()
    } catch (e) {
      setErr(e.message)
    }
  }

  function toggleResourceType(resourceType) {
    setGrantForm((form) => ({
      ...form,
      resource_types: form.resource_types.includes(resourceType)
        ? form.resource_types.filter((item) => item !== resourceType)
        : [...form.resource_types, resourceType],
    }))
  }

  return (
    <div className="grid">
      {loading && !patientResource ? <LoadingSkeleton cards={3} label="Loading patient workspace" /> : <section className="card">
        <h2>My FHIR record</h2>
        {loading && !patientResource ? <p className="muted">Loading your record…</p> : patientResource ? (
          <div className="profile-summary">
            <span className="profile-avatar">{(patientResource.name?.[0]?.text || user.full_name).slice(0, 1).toUpperCase()}</span>
            <div><strong>{patientResource.name?.[0]?.text || user.full_name}</strong><span>Patient record · {patientResource.active ? 'Active' : 'Inactive'}</span><small>Record ID {patientResource.id}</small></div>
          </div>
        ) : <p className="muted">Your profile could not be loaded.</p>}
      </section>}

      <section className="card">
        <h2>Choose what to share</h2>
        <form onSubmit={grant} className="inline-form">
          <label className="field-grow">Choose a physician
            <select required value={grantForm.doctor_email} onChange={(e) => setGrantForm((f) => ({ ...f, doctor_email: e.target.value }))}>
              <option value="">Select a physician</option>
              {physicians.map((physician) => <option key={physician.id} value={physician.email}>{physician.name} · {physician.email}</option>)}
            </select>
          </label>
          <input
            aria-label="Access duration in days" type="number" min={1} max={30} value={grantForm.duration_days}
            onChange={(e) => setGrantForm((f) => ({ ...f, duration_days: Number(e.target.value) }))}
          />
          <button className="btn-primary" type="submit" disabled={submitting || grantForm.resource_types.length === 0}>{submitting ? 'Saving…' : 'Grant access'}</button>
          {submitting && <TransferStatus>Saving access permission</TransferStatus>}
          <div className="scope-list" role="group" aria-label="Allowed record types">
            {consentResourceTypes.map((resourceType) => (
              <label className="scope-option" key={resourceType}>
                <input
                  type="checkbox"
                  checked={grantForm.resource_types.includes(resourceType)}
                  onChange={() => toggleResourceType(resourceType)}
                />
                {resourceType}
              </label>
            ))}
          </div>
          <span className="muted">Choose specific records and an access period (up to 30 days).</span>
        </form>
        {message && <div className="success">{message}</div>}
        {err && <div className="error">{err}</div>}

        <h3>Active &amp; past consents</h3>
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Physician</th><th>Allowed records</th><th>Expires</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {consents.map((c) => (
              <tr key={c.id}>
                <td>{physicians.find((physician) => physician.id === c.grantee_id)?.name || `Physician ${c.grantee_id.slice(0, 8)}`}</td>
                <td>{c.resource_types.join(', ')}</td>
                <td>{new Date(c.expires_at).toLocaleString()}</td>
                <td>{c.is_active ? <span className="pill pill-active">active</span> : <span className="pill">inactive</span>}</td>
                <td>{c.is_active && <button className="btn-ghost" onClick={() => revoke(c.id)}>Revoke</button>}</td>
              </tr>
            ))}
            {consents.length === 0 && <tr><td colSpan={5} className="muted">No consent records yet.</td></tr>}
          </tbody>
        </table></div>
      </section>

      <section className="card">
        <h2>My diagnostic reports</h2>
        {reports.length === 0 && <p className="muted">No reports yet.</p>}
        {reports.map((r) => (
          <div className="report" key={r.id}>
            <strong>{r.resource.conclusion}</strong>
            <span className="muted">{new Date(r.created_at).toLocaleString()}</span>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Record access history</h2>
        {accessHistory.length === 0 && <p className="muted">No record access has been recorded.</p>}
        {accessHistory.map((entry, index) => (
          <div className="report" key={`${entry.accessed_at}-${entry.resource_id || index}`}>
            <strong>{entry.actor_name} ({entry.actor_role})</strong>
            <span>{entry.resource_type}{entry.resource_id ? ` · ${entry.resource_id}` : ''}</span>
            <span className="muted">Purpose: {entry.purpose}</span>
            <span className="muted">{new Date(entry.accessed_at).toLocaleString()}</span>
          </div>
        ))}
      </section>
    </div>
  )
}
