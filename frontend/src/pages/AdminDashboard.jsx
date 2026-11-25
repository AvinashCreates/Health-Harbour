import { useEffect, useState } from 'react'
import { api } from '../api'
import TransferStatus from '../components/TransferStatus'

export default function AdminDashboard({ token }) {
  const [log, setLog] = useState([])
  const [verify, setVerify] = useState(null)
  const [err, setErr] = useState('')
  const [message, setMessage] = useState('')
  const [creating, setCreating] = useState(false)
  const [assigning, setAssigning] = useState(false)
  const [membership, setMembership] = useState({ laboratory_email: '', technician_email: '' })
  const [account, setAccount] = useState({ full_name: '', email: '', password: '', identity_subject: '', role: 'doctor' })

  async function refresh() {
    try {
      setLog(await api.auditLog(token))
    } catch (e) { setErr(e.message) }
  }

  useEffect(() => { refresh() }, [])

  async function runVerify() {
    setErr('')
    try {
      setVerify(await api.auditVerify(token))
    } catch (e) { setErr(e.message) }
  }

  async function provisionUser(e) {
    e.preventDefault()
    setErr('')
    setMessage('')
    setCreating(true)
    try {
      const payload = import.meta.env.VITE_AUTH_PROVIDER === 'keycloak'
        ? { full_name: account.full_name, email: account.email, identity_subject: account.identity_subject, role: account.role }
        : account
      await api.provisionUser(payload, token)
      setMessage(`Account created for ${account.email}.`)
      setAccount({ full_name: '', email: '', password: '', identity_subject: '', role: 'doctor' })
    } catch (e) {
      setErr(e.message)
    } finally {
      setCreating(false)
    }
  }

  async function addTechnician(e) {
    e.preventDefault()
    setErr('')
    setMessage('')
    setAssigning(true)
    try {
      await api.addLabTechnician(membership, token)
      setMessage('Technician added to the laboratory team.')
      setMembership({ laboratory_email: '', technician_email: '' })
    } catch (e) {
      setErr(e.message)
    } finally {
      setAssigning(false)
    }
  }

  return (
    <div className="grid">
      <section className="card">
        <p className="eyebrow">ACCESS MANAGEMENT</p>
        <h2>Create a staff account</h2>
        <p className="muted">Public sign-up creates patient accounts only. Assign staff access here.</p>
        <form onSubmit={provisionUser} className="stacked-form">
          <label>Full name<input required minLength={2} maxLength={120} value={account.full_name} onChange={(e) => setAccount((a) => ({ ...a, full_name: e.target.value }))} /></label>
          <label>Email<input required type="email" value={account.email} onChange={(e) => setAccount((a) => ({ ...a, email: e.target.value }))} /></label>
          {import.meta.env.VITE_AUTH_PROVIDER === 'keycloak' ? (
            <label>Keycloak user ID (subject)<input required value={account.identity_subject} onChange={(e) => setAccount((a) => ({ ...a, identity_subject: e.target.value }))} /><small className="field-note">Create the user in Keycloak first, assign the matching role, then enter its user ID.</small></label>
          ) : (
            <label>Temporary password<input required type="password" minLength={12} value={account.password} onChange={(e) => setAccount((a) => ({ ...a, password: e.target.value }))} /></label>
          )}
          <label>Role
            <select value={account.role} onChange={(e) => setAccount((a) => ({ ...a, role: e.target.value }))}>
              <option value="doctor">Physician</option>
              <option value="lab">Laboratory</option>
              <option value="lab_supervisor">Laboratory supervisor</option>
              <option value="lab_technician">Laboratory technician</option>
            </select>
          </label>
          <button className="btn-primary" type="submit" disabled={creating}>{creating ? 'Creating…' : 'Create account'}</button>
          {creating && <TransferStatus>Provisioning staff account</TransferStatus>}
        </form>
      </section>

      <section className="card">
        <p className="eyebrow">LAB TEAM</p>
        <h2>Assign a technician</h2>
        <p className="muted">Only a technician assigned to a laboratory can process its requests.</p>
        <form onSubmit={addTechnician} className="stacked-form">
          <label>Laboratory account email<input required type="email" value={membership.laboratory_email} onChange={(e) => setMembership((m) => ({ ...m, laboratory_email: e.target.value }))} /></label>
          <label>Technician account email<input required type="email" value={membership.technician_email} onChange={(e) => setMembership((m) => ({ ...m, technician_email: e.target.value }))} /></label>
          <button className="btn-primary" type="submit" disabled={assigning}>{assigning ? 'Adding…' : 'Add to laboratory'}</button>
          {assigning && <TransferStatus>Updating laboratory membership</TransferStatus>}
        </form>
        {message && <div className="success" role="status">{message}</div>}
        {err && <div className="error" role="alert">{err}</div>}
      </section>

      <section className="card">
        <h2>
          Audit trail
          <button className="btn-ghost" onClick={runVerify}>Verify chain integrity</button>
        </h2>
        {verify && (
          <div className={verify.chain_valid ? 'success' : 'error'}>
            {verify.chain_valid
              ? 'Hash chain intact — no tampering detected.'
              : `Chain broken starting at entry #${verify.broken_at_id}.`}
          </div>
        )}
        {err && <div className="error">{err}</div>}
        <div className="table-wrap"><table className="table">
          <thead><tr><th>#</th><th>Event</th><th>When</th><th>Hash</th></tr></thead>
          <tbody>
            {log.map((e) => (
              <tr key={e.id}>
                <td>{e.id}</td>
                <td>{e.event_type}</td>
                <td>{new Date(e.created_at).toLocaleString()}</td>
                <td className="mono">{e.curr_hash.slice(0, 12)}…</td>
              </tr>
            ))}
            {log.length === 0 && <tr><td colSpan={4} className="muted">No events logged yet.</td></tr>}
          </tbody>
        </table></div>
      </section>
    </div>
  )
}
