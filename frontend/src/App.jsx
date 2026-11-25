import { useEffect, useState } from 'react'
import { api } from './api'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Files from './pages/Files'
import SharingAccess from './pages/SharingAccess'
import DoctorDashboard from './pages/DoctorDashboard'
import LabDashboard from './pages/LabDashboard'
import AdminDashboard from './pages/AdminDashboard'
import { keycloak, keycloakEnabled } from './keycloak'
import LoadingSkeleton from './components/LoadingSkeleton'

const ROLE_LABELS = {
  patient: 'Patient',
  doctor: 'Physician',
  lab: 'Laboratory',
  lab_supervisor: 'Lab supervisor',
  lab_technician: 'Lab technician',
  admin: 'Administrator',
}

const HOME_DESCRIPTIONS = {
  patient: 'Your records and sharing permissions, in one clear view.',
  doctor: 'A focused view of authorized patients, requests, and reports.',
  lab: 'A clear overview of your assigned laboratory work.',
  lab_supervisor: 'A clear overview of your laboratory queue and review steps.',
  lab_technician: 'A focused view of specimens and work assigned to you.',
  admin: 'Service operations, account administration, and audit health.',
}

const SECTION_DESCRIPTIONS = {
  files: 'Private clinical records, shared only when the required access is active.',
  sharing: 'Choose who can access selected records and for how long.',
  work: 'Move requests through the appropriate care or laboratory steps.',
  admin: 'Manage service accounts and review audit integrity.',
}

export default function App() {
  const [token, setToken] = useState(() => keycloakEnabled ? null : sessionStorage.getItem('hx_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(keycloakEnabled || Boolean(token))
  const [authError, setAuthError] = useState('')
  const [section, setSection] = useState('overview')

  useEffect(() => {
    if (keycloakEnabled) return
    if (!token) {
      setLoading(false)
      return
    }
    api.me(token)
      .then(setUser)
      .catch(() => handleLogout())
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!keycloakEnabled) return
    let active = true
    let refreshTimer
    keycloak.init({ onLoad: 'check-sso', pkceMethod: 'S256', checkLoginIframe: false })
      .then(async (authenticated) => {
        if (!active || !authenticated) return
        const accessToken = keycloak.token
        if (!accessToken) throw new Error('Keycloak did not return an access token')
        let profile
        try {
          profile = await api.me(accessToken)
        } catch {
          profile = await api.provisionOidcPatient(accessToken)
        }
        if (active) {
          setToken(accessToken)
          setUser(profile)
        }
        refreshTimer = window.setInterval(async () => {
          try {
            if (await keycloak.updateToken(60)) setToken(keycloak.token)
          } catch {
            setAuthError('Your identity session expired. Please sign in again.')
            handleLogout()
          }
        }, 30000)
      })
      .catch((error) => {
        if (active) setAuthError(error.message || 'Unable to connect to the identity provider')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
      window.clearInterval(refreshTimer)
    }
  }, [])

  function handleAuthed({ access_token, user }) {
    sessionStorage.setItem('hx_token', access_token)
    setToken(access_token)
    setUser(user)
    setSection('overview')
  }

  function handleLogout() {
    if (keycloakEnabled) {
      setToken(null)
      setUser(null)
      keycloak.logout({ redirectUri: window.location.origin })
      return
    }
    sessionStorage.removeItem('hx_token')
    setToken(null)
    setUser(null)
    setSection('overview')
  }

  if (loading) return <main className="app-loading"><LoadingSkeleton cards={3} label="Loading your secure workspace" /></main>
  if (!token || !user) return <Login onAuthed={handleAuthed} oidc={keycloakEnabled ? keycloak : null} authError={authError} />

  const roleLabel = ROLE_LABELS[user.role] || 'Workspace'
  const isLab = ['lab', 'lab_supervisor', 'lab_technician'].includes(user.role)
  const isAdmin = user.role === 'admin'
  const greetingName = (user.full_name || '').replace(/^Dr\.?\s+/i, '').trim().split(/\s+/)[0] || 'there'
  const navItems = [
    { id: 'overview', label: 'Overview' },
    ...(!isAdmin ? [{ id: 'files', label: 'Files' }] : []),
    ...(user.role === 'patient' ? [{ id: 'sharing', label: 'Sharing & access' }] : []),
    ...(user.role === 'doctor' || isLab ? [{ id: 'work', label: isLab ? 'Lab workflow' : 'Care workflow' }] : []),
    ...(isAdmin ? [{ id: 'admin', label: 'Admin tools' }] : []),
  ]
  const activeSection = navItems.some((item) => item.id === section) ? section : 'overview'

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="HealthHarbor home">
          <span className="brand-mark" aria-hidden="true">H</span>
          <span>HealthHarbor <small>Care, connected</small></span>
        </a>
        <div className="who">
          <span className="secure-label"><span className="status-dot" /> Secure session</span>
          <span className={`role-badge role-${user.role}`}>{roleLabel}</span>
          <span className="who-name">{user.full_name}</span>
          <button className="btn-ghost" onClick={handleLogout}>Sign out</button>
        </div>
      </header>
      <main className="content">
        <section className="workspace-heading">
          <div>
            <p className="eyebrow">{roleLabel} portal</p>
            <h1>{activeSection === 'overview' ? `Good to see you, ${greetingName}` : navItems.find((item) => item.id === activeSection)?.label}</h1>
            <p className="workspace-subtitle">{activeSection === 'overview' ? HOME_DESCRIPTIONS[user.role] || 'Your healthcare exchange workspace.' : SECTION_DESCRIPTIONS[activeSection] || 'The information and actions available to your account.'}</p>
          </div>
          <div className="privacy-note"><span className="privacy-icon" aria-hidden="true">i</span><span><strong>Access is role-aware</strong><small>Permissions are checked by the service.</small></span></div>
        </section>
        <nav className="section-nav" aria-label="Workspace sections">
          {navItems.map((item) => <button key={item.id} type="button" className={`section-link ${activeSection === item.id ? 'active' : ''}`} aria-current={activeSection === item.id ? 'page' : undefined} onClick={() => setSection(item.id)}>{item.label}</button>)}
        </nav>
        <div key={activeSection} className="section-content">
          {activeSection === 'overview' && <Overview token={token} user={user} onNavigate={setSection} />}
          {activeSection === 'files' && <Files token={token} user={user} />}
          {activeSection === 'sharing' && <SharingAccess token={token} />}
          {activeSection === 'work' && (user.role === 'doctor' ? <DoctorDashboard token={token} /> : isLab ? <LabDashboard token={token} user={user} /> : null)}
          {activeSection === 'admin' && isAdmin && <AdminDashboard token={token} />}
        </div>
      </main>
      <footer className="site-footer">HealthHarbor <span>·</span> Secure healthcare exchange prototype</footer>
    </div>
  )
}
