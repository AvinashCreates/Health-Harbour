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
  const [organizations, setOrganizations] = useState([])
  const [consents, setConsents] = useState([])
  const [history, setHistory] = useState([])
  const [recordRequests, setRecordRequests] = useState([])
  const [careConnections, setCareConnections] = useState([])
  const [crossHospitalExchanges, setCrossHospitalExchanges] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [clinicalReviews, setClinicalReviews] = useState([])
  const [recipientType, setRecipientType] = useState('physician')
  const [doctorEmail, setDoctorEmail] = useState('')
  const [organizationId, setOrganizationId] = useState('')
  const [duration, setDuration] = useState(30)
  const [resourceTypes, setResourceTypes] = useState(['Document'])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [revokingId, setRevokingId] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    const results = await Promise.allSettled([
      api.listPhysicians(token),
      api.consentOrganizations(token),
      api.myConsents(token),
      api.accessHistory(token),
      api.myPatientRecordRequests(token),
      api.myPatientCareConnections(token),
      api.myPatientCrossHospitalExchanges(token),
      api.myPatientPrescriptions(token),
      api.myPatientClinicalReviews(token),
    ])
    if (results[0].status === 'fulfilled') setPhysicians(results[0].value)
    if (results[1].status === 'fulfilled') setOrganizations(results[1].value)
    if (results[2].status === 'fulfilled') setConsents(results[2].value)
    if (results[3].status === 'fulfilled') setHistory(results[3].value)
    if (results[4].status === 'fulfilled') setRecordRequests(results[4].value)
    if (results[5].status === 'fulfilled') setCareConnections(results[5].value)
    if (results[6].status === 'fulfilled') setCrossHospitalExchanges(results[6].value)
    if (results[7].status === 'fulfilled') setPrescriptions(results[7].value)
    if (results[8].status === 'fulfilled') setClinicalReviews(results[8].value)
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
      const payload = {
        doctor_email: doctorEmail,
        duration_days: Number(duration),
        resource_types: resourceTypes,
        ...(recipientType === 'organization' ? { organization_id: organizationId } : {}),
      }
      await api.grantConsent(payload, token)
      const organizationName = organizations.find((item) => item.id === organizationId)?.name
      setMessage(`Treatment permission granted to ${recipientType === 'organization' ? `${organizationName} (${doctorEmail})` : doctorEmail}.`)
      setRecipientType('physician')
      setDoctorEmail('')
      setOrganizationId('')
      setDuration(30)
      setResourceTypes(['Document'])
      await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function decideCrossHospitalExchange(exchange, decision) {
    setError(''); setMessage('')
    setBusy(true)
    try {
      await api.decideCrossHospitalExchange(exchange.id, {
        decision,
        reason: decision === 'APPROVED'
          ? 'I approved this limited cross-hospital record exchange.'
          : decision === 'REVOKED'
            ? 'I revoked this cross-hospital permission.'
            : 'I rejected this cross-hospital record exchange.',
      }, token)
      setMessage(decision === 'APPROVED' ? 'Cross-hospital exchange approved.' : decision === 'REVOKED' ? 'Cross-hospital permission revoked.' : 'Cross-hospital exchange rejected.')
      await refresh()
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }

  async function decideRequest(request, decision) {
    setError(''); setMessage('')
    setBusy(true)
    try {
      await api.decideRecordRequest(request.id, {
        decision,
        response_reason: decision === 'APPROVED'
          ? 'I reviewed and approved this limited record-access request.'
          : 'I declined this record-access request.',
      }, token)
      setMessage(decision === 'APPROVED' ? 'Record access approved.' : 'Record access request declined.')
      await refresh()
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }

  async function revoke(consent) {
    if (!window.confirm('Revoke this permission now? The named physician will lose access immediately.')) return
    setError(''); setMessage('')
    setRevokingId(consent.id)
    try {
      await api.revokeConsent(consent.id, token)
      setMessage('Permission revoked.')
      await refresh()
    } catch (e) { setError(e.message) } finally { setRevokingId('') }
  }

  const physicianFor = (consent) => physicians.find((person) => person.id === consent.grantee_id)
  const selectedOrganization = organizations.find((organization) => organization.id === organizationId)
  const availablePhysicians = recipientType === 'organization'
    ? selectedOrganization?.practitioners || []
    : physicians
  const organizationFor = (consent) => organizations.find((item) => item.id === consent.organization_id)

  return (
    <div className="sharing-page">
      <section className="card sharing-intro">
        <p className="eyebrow">PATIENT-CONTROLLED ACCESS</p>
        <h2>Choose what a physician can access</h2>
        <p className="muted">Grant treatment access to a physician or to an organization with one named physician. Permissions cover selected record types for a limited period. Include <strong>Document</strong> to allow access to your files.</p>
      </section>
      <section className="card">
        <p className="eyebrow">NEW PERMISSION</p><h2>Grant access</h2>
        <form onSubmit={grant} className="sharing-form">
          <label>Share with<select value={recipientType} onChange={(e) => { setRecipientType(e.target.value); setDoctorEmail(''); setOrganizationId('') }}><option value="physician">A physician</option><option value="organization">A healthcare organization</option></select></label>
          {recipientType === 'organization' && <label>Organization<select required value={organizationId} onChange={(e) => { setOrganizationId(e.target.value); setDoctorEmail('') }}><option value="">Select an organization</option>{organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label>}
          <label>Named physician<select required value={doctorEmail} onChange={(e) => setDoctorEmail(e.target.value)}><option value="">Select a physician</option>{availablePhysicians.map((physician) => <option key={physician.id} value={physician.email}>{physician.name} · {physician.email}</option>)}</select></label>
          <label>Duration in days<input type="number" min={1} max={30} required value={duration} onChange={(e) => setDuration(e.target.value === '' ? '' : Number(e.target.value))} /></label>
          <fieldset className="scope-fieldset"><legend>Records this permission covers</legend><div className="scope-list">{RESOURCE_TYPES.map((type) => <label className="scope-option" key={type}><input type="checkbox" checked={resourceTypes.includes(type)} onChange={() => toggleScope(type)} />{type}{type === 'Document' && <span className="scope-hint"> · files</span>}</label>)}</div></fieldset>
          <button className="btn-primary" type="submit" disabled={busy || !doctorEmail || (recipientType === 'organization' && !organizationId) || !resourceTypes.length || duration < 1 || duration > 30}>{busy ? 'Saving permission…' : 'Grant permission'}</button>
          {busy && <TransferStatus>Saving access permission</TransferStatus>}
        </form>
        {availablePhysicians.length === 0 && !loading && <p className="muted">{recipientType === 'organization' ? 'No named physicians are available for this organization.' : 'No physicians are available to select right now.'}</p>}
        {message && <div className="success" role="status">{message}</div>}
        {error && <div className="error" role="alert">{error}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">CROSS-HOSPITAL EXCHANGE</p><h2>Hospital record requests</h2>
        {crossHospitalExchanges.length === 0 ? <p className="muted">No cross-hospital exchange requests are available.</p> : <div className="permission-list">{crossHospitalExchanges.map((exchange) => <article className="permission-row" key={exchange.id}>
          <div><strong>{exchange.requesting_organization_name} · {exchange.requesting_provider_name}</strong><small>Source hospital: {exchange.source_organization_name}</small><small>Purpose: {exchange.purpose}</small><small>Records: {(exchange.resource_types || []).join(', ')}</small><small>Duration: {exchange.requested_duration_days} days</small><small>Reason: {exchange.reason}</small></div>
          <div className="permission-status"><span className={`pill ${exchange.status === 'APPROVED' ? 'pill-active' : ''}`}>{exchange.status}</span>{exchange.status === 'REQUESTED' && <><button type="button" className="btn-primary" disabled={busy} onClick={() => decideCrossHospitalExchange(exchange, 'APPROVED')}>Approve exchange</button><button type="button" className="btn-ghost" disabled={busy} onClick={() => decideCrossHospitalExchange(exchange, 'REJECTED')}>Reject</button></>}{exchange.status === 'APPROVED' && <button type="button" className="btn-danger-ghost" disabled={busy} onClick={() => decideCrossHospitalExchange(exchange, 'REVOKED')}>Revoke</button>}</div>
        </article>)}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">PROVIDER REQUESTS</p><h2>Review record access requests</h2>
        {recordRequests.length === 0 ? <p className="muted">No provider record-access requests are waiting or recorded.</p> : <div className="permission-list">{recordRequests.map((request) => <article className="permission-row" key={request.id}>
          <div>
            <strong>{request.provider_name} · {request.organization_name}</strong>
            <small>Purpose: {request.purpose}</small>
            <small>Requested records: {(request.resource_types || []).join(', ')}</small>
            <small>Requested duration: {request.requested_duration_days} days</small>
            <small>Reason: {request.reason}</small>
          </div>
          <div className="permission-status"><span className={`pill ${request.status === 'APPROVED' ? 'pill-active' : ''}`}>{request.status}</span>{request.status === 'REQUESTED' && <><button type="button" className="btn-primary" disabled={busy} onClick={() => decideRequest(request, 'APPROVED')}>Approve limited access</button><button type="button" className="btn-ghost" disabled={busy} onClick={() => decideRequest(request, 'REJECTED')}>Reject</button></>}</div>
        </article>)}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">CARE CONNECTIONS</p><h2>Provider connection requests</h2>
        {careConnections.length === 0 ? <p className="muted">You have not initiated a provider connection.</p> : <div className="permission-list">{careConnections.map((connection) => <article className="permission-row" key={connection.id}><div><strong>{connection.provider_name} · {connection.organization_name}</strong><small>{connection.reason}</small></div><span className={`pill ${connection.status === 'ACCEPTED' ? 'pill-active' : ''}`}>{connection.status}</span></article>)}</div>}
      </section>

      <section className="card">
        <div className="card-heading-row"><div><p className="eyebrow">PERMISSION RECORD</p><h2>Current and past access</h2></div><button type="button" className="btn-ghost" onClick={refresh} disabled={loading}>Refresh</button></div>
        {loading ? <LoadingSkeleton cards={2} label="Loading sharing permissions" /> : consents.length === 0 ? <p className="muted">No sharing permissions have been recorded.</p> : <div className="permission-list">{consents.map((consent) => {
          const physician = physicianFor(consent)
          const active = Boolean(consent.is_active)
          return <article className="permission-row" key={consent.id}>
            <div><strong>{consent.organization_id ? `${organizationFor(consent)?.name || 'Organization'} · ` : ''}{physician?.name || `Physician ${String(consent.grantee_id || '').slice(0, 8)}`}</strong><span>{physician?.email || 'Physician account'}</span><small>Purpose: {consent.purpose || 'TREATMENT'}</small><small>Records: {(consent.resource_types || []).join(', ') || 'Not specified'}</small><small>Expires: {displayDate(consent.expires_at)}</small></div>
            <div className="permission-status"><span className={`pill ${active ? 'pill-active' : ''}`}>{active ? 'Active' : 'Revoked or expired'}</span>{active && <button className="btn-danger-ghost" type="button" disabled={Boolean(revokingId)} onClick={() => revoke(consent)}>{revokingId === consent.id ? 'Revoking…' : 'Revoke'}</button>}</div>
            {revokingId === consent.id && <TransferStatus>Revoking access</TransferStatus>}
          </article>
        })}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">PRESCRIPTIONS</p><h2>Your authorized prescriptions</h2>
        {prescriptions.length === 0 ? <p className="muted">No prescriptions are available for your account.</p> : <div className="permission-list">{prescriptions.map((prescription) => <article className="permission-row" key={prescription.id}><div><strong>{prescription.medication_name} · {prescription.dosage}</strong><small>Provider: {prescription.provider_name}</small><small>Frequency: {prescription.frequency}{prescription.duration ? ` · Duration: ${prescription.duration}` : ''}</small>{prescription.instructions && <small>Instructions: {prescription.instructions}</small>}</div><span className={`pill ${prescription.status === 'ACTIVE' ? 'pill-active' : ''}`}>{prescription.status}</span></article>)}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">CLINICAL REVIEWS</p><h2>Physician review history</h2>
        {clinicalReviews.length === 0 ? <p className="muted">No clinical reviews have been recorded.</p> : <div className="activity-list">{clinicalReviews.map((review) => <div className="activity-row" key={review.id}><strong>{review.provider_name} · {review.status}</strong><span>{review.organization_name}</span><span>{review.clinical_note || 'No clinical note supplied'}</span><small>{displayDate(review.reviewed_at)}</small></div>)}</div>}
      </section>

      <section className="card">
        <p className="eyebrow">RECENT ACTIVITY</p><h2>Record access history</h2>
        {history.length === 0 ? <p className="muted">No access events are available.</p> : <div className="activity-list">{history.slice(0, 10).map((entry, index) => <div className="activity-row" key={`${entry.accessed_at}-${entry.resource_id || index}`}><strong>{entry.actor_name || 'Care team'} <span className="muted">({entry.actor_role || 'account'})</span></strong><span>{entry.resource_type || 'Record'}{entry.purpose ? ` · ${entry.purpose}` : ''}</span><small>{displayDate(entry.accessed_at)}</small></div>)}</div>}
      </section>
    </div>
  )
}
