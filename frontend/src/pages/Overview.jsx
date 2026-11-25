import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'

const WORKFLOW_LABELS = {
  REQUESTED: 'Requested',
  ACCEPTED: 'Accepted',
  ASSIGNED: 'Assigned',
  SPECIMEN_REGISTERED: 'Specimen',
  PROCESSING: 'Processing',
  RESULTS_SUBMITTED: 'Awaiting review',
  FINALIZED: 'Finalized',
  PHYSICIAN_REVIEWED: 'Reviewed',
}

const ROLE_GUIDES = {
  patient: {
    title: 'You decide what is shared',
    description: 'Your records stay yours. A clinician sees only the resources you authorize, for the period you choose.',
    steps: [
      ['Add records', 'Keep reports and care documents together in your private file center.'],
      ['Choose access', 'Select a physician, the information they may use, and an expiry of up to 30 days.'],
      ['Change your mind', 'Review access history and revoke permission whenever you need to.'],
    ],
  },
  doctor: {
    title: 'Coordinate care with permission',
    description: 'Use only patients with active access, then follow each laboratory request through clinical review.',
    steps: [
      ['Confirm access', 'The patient list reflects active grants and their selected record scopes.'],
      ['Request a test', 'Create a laboratory request for an authorized patient and a selected laboratory.'],
      ['Review results', 'Track the workflow and record your review after the laboratory finalizes results.'],
    ],
  },
  lab: {
    title: 'Process requests in sequence',
    description: 'Your queue contains work assigned to your laboratory or to your technician account.',
    steps: [
      ['Accept and assign', 'A lab reviewer accepts a request and assigns a member of the laboratory team.'],
      ['Process the specimen', 'The assigned technician registers the specimen, records results, and submits for review.'],
      ['Finalize securely', 'A laboratory reviewer finalizes the report for the requesting physician.'],
    ],
  },
  admin: {
    title: 'Support the service, not clinical access',
    description: 'Administrative tools focus on staff, laboratory membership, and audit integrity—not patient records.',
    steps: [
      ['Provision staff', 'Create the appropriate non-patient account or link its managed identity.'],
      ['Connect lab teams', 'Associate technicians with their laboratory before work can be assigned.'],
      ['Review audit health', 'Inspect event volume and verify the local tamper-evident audit chain.'],
    ],
  },
}

function Metric({ label, value, note, mark }) {
  return (
    <article className="metric-card">
      <span className="metric-mark" aria-hidden="true">{mark}</span>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  )
}

function ActivityChart({ title, description, items, emptyLabel }) {
  const max = Math.max(...items.map((item) => item.value), 1)
  const width = 560
  const baseY = 166
  const chartHeight = 126
  const slot = width / Math.max(items.length, 1)
  const barWidth = Math.min(42, slot * 0.48)

  return (
    <section className="card chart-card" aria-label={title}>
      <div className="card-heading-row">
        <div>
          <p className="eyebrow">AT A GLANCE</p>
          <h2>{title}</h2>
        </div>
        <span className="chart-period">Current account</span>
      </div>
      <p className="chart-description">{description}</p>
      {items.length === 0 ? <p className="chart-empty">{emptyLabel}</p> : (
        <div className="chart-scroll">
          <svg className="activity-chart" viewBox={`0 0 ${width} 220`} role="img" aria-label={`${title}: ${items.map((item) => `${item.label} ${item.value}`).join(', ')}`}>
            {[0, 1, 2, 3].map((line) => {
              const y = 40 + line * 42
              return <line key={line} className="chart-gridline" x1="20" x2={width - 10} y1={y} y2={y} />
            })}
            {items.map((item, index) => {
              const height = Math.max(item.value === 0 ? 2 : 8, (item.value / max) * chartHeight)
              const x = slot * index + (slot - barWidth) / 2
              const y = baseY - height
              const chartLabel = item.label.length > 13 ? `${item.label.slice(0, 12)}…` : item.label
              return (
                <g key={item.label}>
                  <title>{`${item.label}: ${item.value}`}</title>
                  <text className="chart-value" x={x + barWidth / 2} y={Math.max(y - 9, 23)} textAnchor="middle">{item.value}</text>
                  <rect className="chart-bar" x={x} y={y} width={barWidth} height={height} rx="7" />
                  <text className="chart-label" x={x + barWidth / 2} y="188" textAnchor="middle">{chartLabel}</text>
                </g>
              )
            })}
          </svg>
        </div>
      )}
      <p className="chart-footnote">Counts summarize data currently returned for your account. They do not imply a trend.</p>
    </section>
  )
}

function HowItWorks({ guide }) {
  return (
    <section className="card how-card">
      <div className="card-heading-row">
        <div>
          <p className="eyebrow">A SIMPLE, CONTROLLED FLOW</p>
          <h2>{guide.title}</h2>
        </div>
        <span className="how-symbol" aria-hidden="true">↗</span>
      </div>
      <p className="how-description">{guide.description}</p>
      <div className="how-steps">
        {guide.steps.map(([title, detail], index) => (
          <article className="how-step" key={title}>
            <span className="step-number">{String(index + 1).padStart(2, '0')}</span>
            <div><h3>{title}</h3><p>{detail}</p></div>
          </article>
        ))}
      </div>
    </section>
  )
}

function countStatuses(requests = []) {
  const counts = {}
  for (const request of requests) {
    const status = request.workflow_status || 'UNKNOWN'
    counts[status] = (counts[status] || 0) + 1
  }
  return counts
}

export default function Overview({ token, user, onNavigate }) {
  const [data, setData] = useState({})
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    const jobs = user.role === 'patient'
      ? [['files', () => api.listFiles(token)], ['consents', () => api.myConsents(token)], ['reports', () => api.listDiagnosticReports(token)]]
      : user.role === 'doctor'
        ? [['patients', () => api.accessiblePatients(token)], ['requests', () => api.listServiceRequests(token)], ['reports', () => api.listDiagnosticReports(token)]]
        : ['lab', 'lab_supervisor', 'lab_technician'].includes(user.role)
          ? [['requests', () => api.listServiceRequests(token)]]
          : [['audit', () => api.auditLog(token)], ['integrity', () => api.auditVerify(token)]]

    Promise.all(jobs.map(async ([key, load]) => {
      try { return [key, await load(), null] } catch (error) { return [key, null, error.message] }
    })).then((results) => {
      if (!active) return
      setData(Object.fromEntries(results.filter(([, value]) => value !== null).map(([key, value]) => [key, value])))
      setErrors(results.filter(([, , error]) => error).map(([, , error]) => error))
    }).finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [token, user.role])

  const statusCounts = useMemo(() => countStatuses(data.requests), [data.requests])
  const isPatient = user.role === 'patient'
  const isDoctor = user.role === 'doctor'
  const isLab = ['lab', 'lab_supervisor', 'lab_technician'].includes(user.role)
  const isAdmin = user.role === 'admin'
  const guide = ROLE_GUIDES[isPatient ? 'patient' : isDoctor ? 'doctor' : isLab ? 'lab' : 'admin']
  const activeConsents = data.consents?.filter((item) => item.is_active) || []

  let chartItems = []
  let chartTitle = ''
  let chartDescription = ''
  if (isPatient) {
    chartItems = [
      { label: 'Files', value: data.files?.length || 0 },
      { label: 'Access', value: activeConsents.length },
      { label: 'Reports', value: data.reports?.length || 0 },
    ]
    chartTitle = 'Your health record at a glance'
    chartDescription = 'A simple count of files, active sharing permissions, and diagnostic reports visible in your account.'
  } else if (isDoctor || isLab) {
    chartItems = Object.entries(statusCounts).map(([status, value]) => ({
      label: WORKFLOW_LABELS[status] || status.replaceAll('_', ' ').toLowerCase(),
      value,
    }))
    chartTitle = isDoctor ? 'Care requests by stage' : 'Laboratory work by stage'
    chartDescription = isDoctor
      ? 'See how requests visible to you are moving through the laboratory workflow.'
      : 'See the current distribution of requests in your laboratory or assigned technician queue.'
  } else {
    const counts = new Map()
    for (const event of data.audit || []) counts.set(event.event_type, (counts.get(event.event_type) || 0) + 1)
    chartItems = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([label, value]) => ({
      label: label.replaceAll('_', ' ').toLowerCase(),
      value,
    }))
    chartTitle = 'Recent audit activity'
    chartDescription = 'The most common event types in the audit records currently available to administrators.'
  }

  return (
    <div className="overview-stack">
      {errors.length > 0 && <div className="error" role="alert">Some workspace information could not be loaded. {errors[0]}</div>}
      {loading ? <LoadingSkeleton cards={3} label="Loading your latest activity" /> : (
        <>
          <section className="metric-grid" aria-label="Workspace summary">
            {isPatient && <>
              <Metric mark="▤" label="Files in your record" value={data.files?.length ?? '—'} note="Private unless you grant access" />
              <Metric mark="⌑" label="Active permissions" value={activeConsents.length} note="You can review or revoke these" />
              <Metric mark="＋" label="Diagnostic reports" value={data.reports?.length ?? '—'} note="Available to your account" />
            </>}
            {isDoctor && <>
              <Metric mark="◎" label="Patients with access" value={data.patients?.length ?? '—'} note="Based on active permissions" />
              <Metric mark="↗" label="Lab requests" value={data.requests?.length ?? '—'} note="Visible to your account" />
              <Metric mark="▤" label="Reports received" value={data.reports?.length ?? '—'} note="Available for clinical review" />
            </>}
            {isLab && <>
              <Metric mark="↗" label="Requests in your queue" value={data.requests?.length ?? '—'} note="Visible to your laboratory role" />
              <Metric mark="◷" label="In progress" value={(statusCounts.ASSIGNED || 0) + (statusCounts.SPECIMEN_REGISTERED || 0) + (statusCounts.PROCESSING || 0)} note="Assigned through processing" />
              <Metric mark="✓" label="Awaiting review" value={statusCounts.RESULTS_SUBMITTED || 0} note="Submitted for lab review" />
            </>}
            {isAdmin && <>
              <Metric mark="≡" label="Audit events" value={data.audit?.length ?? '—'} note="Events returned by the audit service" />
              <Metric mark="◌" label="Event types" value={chartItems.length} note="Types in the recent activity view" />
              <Metric
                mark={data.integrity?.chain_valid ? '✓' : data.integrity ? '!' : '…'}
                label="Audit integrity"
                value={data.integrity?.chain_valid ? 'Verified' : data.integrity ? 'Attention' : '—'}
                note={data.integrity?.chain_valid
                  ? 'Hash chain intact'
                  : data.integrity?.broken_at_id
                    ? `Integrity break at entry #${data.integrity.broken_at_id}`
                    : 'Verification status unavailable'}
              />
            </>}
          </section>

          <section className="overview-grid">
            <ActivityChart
              title={chartTitle}
              description={chartDescription}
              items={chartItems}
              emptyLabel={isAdmin ? 'Audit events will appear here as activity is recorded.' : 'No activity is available to chart yet.'}
            />
            <HowItWorks guide={guide} />
          </section>

          {(isDoctor || isLab) && (
            <section className="card overview-card">
              <div className="card-heading-row">
                <div><p className="eyebrow">NEXT STEP</p><h2>{isDoctor ? 'Continue care coordination' : 'Continue laboratory work'}</h2></div>
                <button className="btn-primary" onClick={() => onNavigate('work')}>{isDoctor ? 'Open care workflow' : 'Open lab workflow'}</button>
              </div>
              <p className="muted">{isDoctor ? 'Create a consent-authorized lab request or review a finalized report.' : 'Open your queue to accept, process, or review the next assigned request.'}</p>
            </section>
          )}

          {isPatient && (
            <section className="card overview-card patient-actions">
              <div><p className="eyebrow">YOUR NEXT STEP</p><h2>Keep your health information organized</h2><p className="muted">Add records or manage which physicians can access selected information.</p></div>
              <div className="action-row">
                <button className="btn-primary" onClick={() => onNavigate('files')}>Open file center</button>
                <button className="btn-ghost" onClick={() => onNavigate('sharing')}>Manage sharing</button>
              </div>
            </section>
          )}

          {isAdmin && (
            <section className="card overview-card">
              <div className="card-heading-row"><div><p className="eyebrow">ADMINISTRATION</p><h2>Focused tools for service operations</h2></div><button className="btn-primary" onClick={() => onNavigate('admin')}>Open admin tools</button></div>
              <p className="muted">Provision staff, manage laboratory team membership, inspect events, and verify audit integrity. Clinical records are not available in the admin workspace.</p>
            </section>
          )}
        </>
      )}
    </div>
  )
}
