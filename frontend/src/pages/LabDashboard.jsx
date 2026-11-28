import { useEffect, useState } from 'react'
import { api } from '../api'
import TransferStatus from '../components/TransferStatus'

const STATUS_LABELS = {
  REQUESTED: 'New request',
  ACCEPTED: 'Accepted',
  ASSIGNED: 'Assigned',
  SPECIMEN_REGISTERED: 'Specimen registered',
  PROCESSING: 'Processing',
  RESULTS_SUBMITTED: 'Awaiting review',
  FINALIZED: 'Finalized',
  PHYSICIAN_REVIEWED: 'Physician reviewed',
}

export default function LabDashboard({ token, user }) {
  const [requests, setRequests] = useState([])
  const [technicians, setTechnicians] = useState({})
  const [selected, setSelected] = useState(null)
  const [obsValue, setObsValue] = useState('')
  const [obsUnit, setObsUnit] = useState('mg/dL')
  const [conclusion, setConclusion] = useState('')
  const [message, setMessage] = useState('')
  const [err, setErr] = useState('')
  const [busyId, setBusyId] = useState('')
  const [loading, setLoading] = useState(true)
  const [amendReportId, setAmendReportId] = useState('')
  const [amendConclusion, setAmendConclusion] = useState('')
  const [amendReason, setAmendReason] = useState('')
  const isTechnician = user.role === 'lab_technician'

  async function refresh() {
    setLoading(true)
    setErr('')
    try {
      setRequests(await api.listServiceRequests(token))
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [token])

  async function runAction(request, action) {
    setErr('')
    setMessage('')
    setBusyId(request.id)
    try {
      if (action === 'accept') await api.acceptServiceRequest(request.id, token)
      if (action === 'assign') await api.assignTechnician(request.id, technicians[request.id], token)
      if (action === 'specimen') await api.registerSpecimen(request.id, {}, token)
      if (action === 'processing') await api.startProcessing(request.id, token)
      if (action === 'finalize') await api.finalizeReport(request.id, token)
      setMessage('Workflow updated.')
      await refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusyId('')
    }
  }

  async function amendReport(e) {
    e.preventDefault()
    if (!amendReportId) return
    setErr(''); setMessage('')
    setBusyId(amendReportId)
    try {
      await api.amendDiagnosticReport(amendReportId, { conclusion: amendConclusion, reason: amendReason }, token)
      setMessage('Diagnostic report amended.')
      setAmendReportId('')
      setAmendConclusion('')
      setAmendReason('')
      await refresh()
    } catch (e) { setErr(e.message) } finally { setBusyId('') }
  }

  async function submitResults(e) {
    e.preventDefault()
    if (!selected) return
    setErr('')
    setMessage('')
    setBusyId(selected.id)
    try {
      const coding = selected.resource.code.coding[0]
      await api.createDiagnosticReport({
        service_request_id: selected.id,
        observations: [{
          code: coding.code,
          display: coding.display,
          value: Number(obsValue),
          unit: obsUnit,
        }],
        conclusion,
      }, token)
      setMessage('Results submitted for laboratory review.')
      setSelected(null)
      setObsValue('')
      setConclusion('')
      await refresh()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusyId('')
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <p className="eyebrow">{isTechnician ? 'ASSIGNED WORK' : 'LABORATORY QUEUE'}</p>
        <h2>{isTechnician ? 'Your assigned work' : 'Requests assigned to your laboratory'}</h2>
        {loading && <p className="muted" role="status">Loading laboratory requests…</p>}
        {!loading && !err && requests.length === 0 && (
          <div className="empty-state" role="status">
            <strong>Nothing needs your attention right now</strong>
            <p className="muted">New requests assigned to your laboratory will appear here.</p>
          </div>
        )}
        {requests.map((request) => {
          const status = request.workflow_status
          const busy = busyId === request.id
          return (
            <article className="workflow-item" key={request.id}>
              <div className="workflow-item-heading">
                <div>
                  <strong>{request.resource.code?.text || 'Laboratory test'}</strong>
                  <span className="muted">Request {request.resource.id}</span>
                </div>
                <span className="pill">{STATUS_LABELS[status] || status}</span>
              </div>
              <div className="workflow-steps" aria-label={`Current status: ${STATUS_LABELS[status] || status}`}>
                {['REQUESTED', 'ACCEPTED', 'ASSIGNED', 'SPECIMEN_REGISTERED', 'PROCESSING', 'RESULTS_SUBMITTED', 'FINALIZED'].map((step) => (
                  <span className={STATUS_LABELS[step] && Object.keys(STATUS_LABELS).indexOf(step) <= Object.keys(STATUS_LABELS).indexOf(status) ? 'workflow-step complete' : 'workflow-step'} key={step} />
                ))}
              </div>
              {busy && <TransferStatus>Updating laboratory workflow</TransferStatus>}

              {!isTechnician && status === 'REQUESTED' && (
                <button className="btn-primary" disabled={busy} onClick={() => runAction(request, 'accept')}>{busy ? 'Saving…' : 'Accept request'}</button>
              )}
              {!isTechnician && status === 'ACCEPTED' && (
                <div className="assign-row">
                  <label>
                    Technician email
                    <input type="email" placeholder="tech@lab.example" value={technicians[request.id] || ''} onChange={(e) => setTechnicians((items) => ({ ...items, [request.id]: e.target.value }))} />
                  </label>
                  <button className="btn-primary" disabled={busy || !technicians[request.id]} onClick={() => runAction(request, 'assign')}>{busy ? 'Saving…' : 'Assign work'}</button>
                </div>
              )}
              {isTechnician && status === 'ASSIGNED' && (
                <button className="btn-primary" disabled={busy} onClick={() => runAction(request, 'specimen')}>{busy ? 'Saving…' : 'Register specimen'}</button>
              )}
              {isTechnician && status === 'SPECIMEN_REGISTERED' && (
                <button className="btn-primary" disabled={busy} onClick={() => runAction(request, 'processing')}>{busy ? 'Saving…' : 'Start processing'}</button>
              )}
              {isTechnician && status === 'PROCESSING' && (
                <button className="btn-primary" onClick={() => { setSelected(request); setErr(''); setMessage('') }}>Enter results</button>
              )}
              {!isTechnician && status === 'RESULTS_SUBMITTED' && (
                <button className="btn-primary" disabled={busy} onClick={() => runAction(request, 'finalize')}>{busy ? 'Saving…' : 'Review and finalize'}</button>
              )}
              {['FINALIZED', 'PHYSICIAN_REVIEWED'].includes(status) && request.report_id && <><p className="muted">The report is finalized and ready for the requesting physician.</p><button className="btn-ghost" disabled={busy} onClick={() => { setAmendReportId(request.report_id); setAmendConclusion(''); setAmendReason('') }}>Amend report</button></>}
            </article>
          )
        })}
        {message && <div className="success" role="status">{message}</div>}
        {err && <div className="error" role="alert">{err}</div>}
      </section>

      {amendReportId && (
        <section className="card">
          <p className="eyebrow">REPORT AMENDMENT</p>
          <h2>Amend finalized report</h2>
          <form onSubmit={amendReport} className="stacked-form">
            <label>Amended conclusion<input required maxLength={2000} value={amendConclusion} onChange={(e) => setAmendConclusion(e.target.value)} /></label>
            <label>Reason for amendment<input required minLength={3} maxLength={1000} value={amendReason} onChange={(e) => setAmendReason(e.target.value)} /></label>
            <div className="action-row"><button className="btn-primary" type="submit" disabled={Boolean(busyId)}>{busyId ? 'Saving…' : 'Submit amendment'}</button><button className="btn-ghost" type="button" onClick={() => setAmendReportId('')}>Cancel</button></div>
          </form>
        </section>
      )}

      {selected && (
        <section className="card">
          <p className="eyebrow">RESULT ENTRY</p>
          <h2>{selected.resource.code?.text}</h2>
          <form onSubmit={submitResults} className="stacked-form">
            <label>Measured value
              <input required type="number" step="any" value={obsValue} onChange={(e) => setObsValue(e.target.value)} />
            </label>
            <label>Unit
              <input required maxLength={40} value={obsUnit} onChange={(e) => setObsUnit(e.target.value)} />
            </label>
            <label>Clinical conclusion
              <input required maxLength={2000} value={conclusion} onChange={(e) => setConclusion(e.target.value)} />
            </label>
            <div className="action-row">
              <button className="btn-primary" type="submit" disabled={busyId === selected.id}>{busyId === selected.id ? 'Submitting…' : 'Submit for review'}</button>
              <button className="btn-ghost" type="button" onClick={() => setSelected(null)}>Cancel</button>
            </div>
            {busyId === selected.id && <TransferStatus>Sending results for review</TransferStatus>}
          </form>
        </section>
      )}
    </div>
  )
}
