import { useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'
import TransferStatus from '../components/TransferStatus'

export default function PatientDashboard({ token, user }) {
  const consentResourceTypes = ['Patient', 'ServiceRequest', 'Specimen', 'Observation', 'DiagnosticReport', 'Document']
  const [patientResource, setPatientResource] = useState(null)
  const [physicians, setPhysicians] = useState([])
  const [organizations, setOrganizations] = useState([])
  const [consents, setConsents] = useState([])
  const [reports, setReports] = useState([])
  const [accessHistory, setAccessHistory] = useState([])
  const [grantForm, setGrantForm] = useState({
    recipient_type: 'physician',
    doctor_email: '',
    organization_id: '',
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
      const [patient, doctors, orgs, myConsents, myReports, history] = await Promise.all([
        api.getPatient(user.id, token),
        api.listPhysicians(token),
        api.consentOrganizations(token),
        api.myConsents(token),
        api.listDiagnosticReports(token),
        api.accessHistory(token),
      ])
      setPatientResource(patient)
      setPhysicians(doctors)
      setOrganizations(orgs)
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
      const { recipient_type, ...grantPayload } = grantForm
      if (recipient_type === 'physician') delete grantPayload.organization_id
      await api.grantConsent(grantPayload, token)
      const recipient = recipient_type === 'organization'
        ? `${organizations.find((item) => item.id === grantForm.organization_id)?.name || 'organization'} (${grantForm.doctor_email})`
        : grantForm.doctor_email
      setMessage(`Treatment access granted to ${recipient}`)
      setGrantForm({
        recipient_type: 'physician',
        doctor_email: '',
        organization_id: '',
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
    if (!window.confirm('Revoke this consent now? The named physician will lose access immediately.')) return
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

  const selectedOrganization = organizations.find((item) => item.id === grantForm.organization_id)
  const availablePhysicians = grantForm.recipient_type === 'organization'
    ? selectedOrganization?.practitioners || []
    : physicians

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
          <label className="field-grow">Share with
            <select value={grantForm.recipient_type} onChange={(e) => setGrantForm((f) => ({
              ...f,
              recipient_type: e.target.value,
              doctor_email: '',
              organization_id: '',
            }))}>
              <option value="physician">A physician</option>
              <option value="organization">A healthcare organization</option>
            </select>
          </label>
          {grantForm.recipient_type === 'organization' && (
            <label className="field-grow">Choose an organization
              <select required value={grantForm.organization_id} onChange={(e) => setGrantForm((f) => ({
                ...f,
                organization_id: e.target.value,
                doctor_email: '',
              }))}>
                <option value="">Select an organization</option>
                {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
              </select>
            </label>
          )}
          <label className="field-grow">Named physician
            <select required value={grantForm.doctor_email} onChange={(e) => setGrantForm((f) => ({ ...f, doctor_email: e.target.value }))}>
              <option value="">Select a physician</option>
              {availablePhysicians.map((physician) => <option key={physician.id} value={physician.email}>{physician.name} · {physician.email}</option>)}
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
          <span className="muted">Access is limited to treatment, the selected record types, and up to 30 days. Organization access requires a named physician who is an active member.</span>
        </form>
        {message && <div className="success">{message}</div>}
        {err && <div className="error">{err}</div>}

        <h3>Active &amp; past consents</h3>
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Recipient</th><th>Purpose</th><th>Allowed records</th><th>Expires</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {consents.map((c) => (
              <tr key={c.id}>
                <td>{c.organization_id ? `${organizations.find((organization) => organization.id === c.organization_id)?.name || 'Organization'} · ` : ''}{physicians.find((physician) => physician.id === c.grantee_id)?.name || `Physician ${c.grantee_id.slice(0, 8)}`}</td>
                <td>{c.purpose || 'TREATMENT'}</td>
                <td>{c.resource_types.join(', ')}</td>
                <td>{new Date(c.expires_at).toLocaleString()}</td>
                <td>{c.is_active ? <span className="pill pill-active">active</span> : <span className="pill">inactive</span>}</td>
                <td>{c.is_active && <button className="btn-ghost" onClick={() => revoke(c.id)}>Revoke</button>}</td>
              </tr>
            ))}
            {consents.length === 0 && <tr><td colSpan={6} className="muted">No consent records yet.</td></tr>}
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
