import { useState } from 'react'
import { api } from '../api'

export default function Login({ onAuthed, oidc, authError }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [passwordVisible, setPasswordVisible] = useState(false)

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setError('')
    setPasswordVisible(false)
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = mode === 'login'
        ? await api.login({ email: form.email, password: form.password })
        : await api.register(form)
      onAuthed(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-layout">
        <section className="auth-story">
          <a className="brand brand-light" href="/">
            <span className="brand-mark" aria-hidden="true">+</span>
            <span>HealthHarbor <small>Care, connected</small></span>
          </a>
          <div className="story-copy">
            <span className="story-kicker">CONNECTED CARE, WITH YOUR PERMISSION</span>
            <h1>Better connected.<br />Patient controlled.</h1>
            <p>HealthHarbor helps patients, physicians, and laboratories exchange the right records through clear, time-limited permissions.</p>
            <div className="story-points">
              <span><b>01</b> You choose what to share</span>
              <span><b>02</b> Care teams follow a clear workflow</span>
            </div>
          </div>
          <div className="story-footer">A consent-aware healthcare exchange research prototype</div>
        </section>

        <section className="auth-card">
          <div className="auth-card-heading">
            <p className="eyebrow">{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</p>
            <h2>{mode === 'login' ? 'Sign in to your account' : 'Create a patient account'}</h2>
            <p className="auth-sub">{mode === 'login' ? 'Use your registered email to continue.' : 'Self-registration is for patients only. Staff accounts are created by an administrator.'}</p>
          </div>
          {oidc ? (
            <div className="auth-form">
              {authError && <div className="error" role="alert">{authError}</div>}
              <button className="btn-primary auth-submit" type="button" onClick={() => oidc.login()}>
                Sign in with HealthHarbor Identity
              </button>
              <button className="btn-ghost" type="button" onClick={() => oidc.register()}>
                Patient registration
              </button>
              <p className="muted">Staff sign-in is managed by your organization.</p>
            </div>
          ) : <>
          <div className="tabs" aria-label="Account access">
            <button type="button" aria-pressed={mode === 'login'} className={mode === 'login' ? 'tab active' : 'tab'} onClick={() => changeMode('login')}>Sign in</button>
            <button type="button" aria-pressed={mode === 'register'} className={mode === 'register' ? 'tab active' : 'tab'} onClick={() => changeMode('register')}>Patient registration</button>
          </div>

          <form onSubmit={submit} className="auth-form">
            {mode === 'register' && (
              <label>
                Full name
                <input autoComplete="name" required maxLength={120} value={form.full_name} onChange={(e) => update('full_name', e.target.value)} />
              </label>
            )}
            <label>
              Email address
              <input autoComplete="email" type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} />
            </label>
            <label>
              Password
              <span className="password-field">
                <input aria-label="Password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} type={passwordVisible ? 'text' : 'password'} required minLength={mode === 'login' ? 1 : 12} value={form.password} onChange={(e) => update('password', e.target.value)} />
                <button className="password-toggle" type="button" aria-label={passwordVisible ? 'Hide password' : 'Show password'} aria-pressed={passwordVisible} onClick={() => setPasswordVisible((visible) => !visible)}>{passwordVisible ? 'Hide' : 'Show'}</button>
              </span>
              {mode === 'register' && <small className="field-note">Use at least 12 characters.</small>}
            </label>
            {error && <div className="error" role="alert" aria-live="assertive">{error}</div>}
            <button className="btn-primary auth-submit" type="submit" disabled={busy}>
              {busy ? <><span className="spinner" aria-hidden="true" /> Please wait…</> : mode === 'login' ? 'Sign in' : 'Create patient account'}
            </button>
          </form>

          <div className="auth-assurance"><span aria-hidden="true">⌑</span> Access is checked by the service when you use the app.</div>
          </>}
        </section>
      </div>
    </div>
  )
}
