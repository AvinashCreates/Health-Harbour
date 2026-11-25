import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'
import TransferStatus from '../components/TransferStatus'

const RESOURCE_TYPES = ['Document', 'Patient', 'ServiceRequest', 'Specimen', 'Observation', 'DiagnosticReport']

function displayDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

export default function SharingAccess({ token }) {
  const [physicians, setPhysicians] = useState([])
  const [consents, setConsents] = useState([])
  const [history, setHistory] = useState([])
  const [doctorEmail, setDoctorEmail] = useState('')
  const [duration, setDuration] = useState(30)
  const [resourceTypes, setResourceTypes] = useState(['Document'])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [revokingId, setRevokingId] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    const results = await Promise.allSettled([api.listPhysicians(token), api.myConsents(token), api.accessHistory(token)])
    if (results[0].status === 'fulfilled') setPhysicians(results[0].value)
    if (results[1].status === 'fulfilled') setConsents(results[1].value)
    if (results[2].status === 'fulfilled') setHistory(results[2].value)
    const failed = results.find((result) => result.status === 'rejected')
    if (failed) setError(failed.reason?.message || 'Some access information could not be loaded.')
    setLoading(false)
  }, [token])

  useEffect(() => { refresh() }, [refresh])

  function toggleScope(scope) {
    setResourceTypes((current) => current.includes(scope) ? current.filter((value) => value !== scope) : [...current, scope])
  }

  async function grant(e) {
    e.preventDefault()
    setError(''); setMessage(''); setBusy(true)
    try {
      await api.grantConsent({ doctor_email: doctorEmail, duration_days: Number(duration), resource_types: resourceTypes }, token)
      setMessage(`Access permission granted to ${doctorEmail}.`)
      setDoctorEmail('')
      setDuration(30)
      setResourceTypes(['Document'])
      await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function revoke(consent) {
    if (!window.confirm('Revoke this physician’s permission?')) return
    setError(''); setMessage('')
    setRevokingId(consent.id)
    try {
      await api.revokeConsent(consent.id, token)
      setMessage('Permission revoked.')
      await refresh()
    } catch (e) { setError(e.message) } finally { setRevokingId('') }
  }

  const physicianFor = (consent) => physicians.find((person) => person.id === consent.grantee_id)

  return (
    <div className="sharing-page">
      <section className="card sharing-intro">
        <p className="eyebrow">PATIENT-CONTROLLED ACCESS</p>
        <h2>Choose what a physician can access</h2>
        <p className="muted">Grant a physician permission for selected record types and a limited period. Include <strong>Document</strong> to allow access to your files. You can review or revoke active permissions here.</p>
      </section>
      <section className="card">
        <p className="eyebrow">NEW PERMISSION</p><h2>Grant access</h2>
        <form onSubmit={grant} className="sharing-form">
          <label>Physician<select required value={doctorEmail} onChange={(e) => setDoctorEmail(e.target.value)}><option value="">Select a physician</option>{physicians.map((physician) => <option key={physician.id} value={physician.email}>{physician.name} · {physician.email}</option>)}</select></label>
          <label>Duration in days<input type="number" min={1} max={30} required value={duration} onChange={(e) => setDuration(e.target.value === '' ? '' : Number(e.target.value))} /></label>
          <fieldset className="scope-fieldset"><legend>Records this permission covers</legend><div className="scope-list">{RESOURCE_TYPES.map((type) => <label className="scope-option" key={type}><input type="checkbox" checked={resourceTypes.includes(type)} onChange={() => toggleScope(type)} />{type}{type === 'Document' && <span className="scope-hint"> · files</span>}</label>)}</div></fieldset>
          <button className="btn-primary" type="submit" disabled={busy || !doctorEmail || !resourceTypes.length || duration < 1 || duration > 30}>{busy ? 'Saving permission…' : 'Grant permission'}</button>
          {busy && <TransferStatus>Saving access permission</TransferStatus>}
        </form>
        {physicians.length === 0 && !loading && <p className="muted">No physicians are available to select right now.</p>}
        {message && <div className="success" role="status">{message}</div>}
        {error && <div className="error" role="alert">{error}</div>}
      </section>

      <section className="card">
        <div className="card-heading-row"><div><p className="eyebrow">PERMISSION RECORD</p><h2>Current and past access</h2></div><button type="button" className="btn-ghost" onClick={refresh} disabled={loading}>Refresh</button></div>
        {loading ? <LoadingSkeleton cards={2} label="Loading sharing permissions" /> : consents.length === 0 ? <p className="muted">No sharing permissions have been recorded.</p> : <div className="permission-list">{consents.map((consent) => {
          const physician = physicianFor(consent)
          const active = Boolean(consent.is_active)
          return <article className="permission-row" key={consent.id}>
            <div><strong>{physician?.name || `Physician ${String(consent.grantee_id || '').slice(0, 8)}`}</strong><span>{physician?.email || 'Physician account'}</span><small>Records: {(consent.resource_types || []).join(', ') || 'Not specified'}</small><small>Expires: {displayDate(consent.expires_at)}</small></div>
            <div className="permission-status"><span className={`pill ${active ? 'pill-active' : ''}`}>{active ? 'Active' : 'Revoked or expired'}</span>{active && <button className="btn-danger-ghost" type="button" disabled={Boolean(revokingId)} onClick={() => revoke(consent)}>{revokingId === consent.id ? 'Revoking…' : 'Revoke'}</button>}</div>
            {revokingId === consent.id && <TransferStatus>Revoking access</TransferStatus>}
          </article>
        })}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">RECENT ACTIVITY</p><h2>Record access history</h2>
        {history.length === 0 ? <p className="muted">No access events are available.</p> : <div className="activity-list">{history.slice(0, 10).map((entry, index) => <div className="activity-row" key={`${entry.accessed_at}-${entry.resource_id || index}`}><strong>{entry.actor_name || 'Care team'} <span className="muted">({entry.actor_role || 'account'})</span></strong><span>{entry.resource_type || 'Record'}{entry.purpose ? ` · ${entry.purpose}` : ''}</span><small>{displayDate(entry.accessed_at)}</small></div>)}</div>}
      </section>
    </div>
  )
}
