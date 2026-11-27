import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

const EMPTY_ORGANIZATION = {
  legal_name: '',
  display_name: '',
  organization_type: 'HOSPITAL',
  registration_authority: '',
  registration_identifier: '',
  city: '',
  country: '',
  contact_email: '',
  contact_phone: '',
  administrative_contact_name: '',
  administrative_contact_email: '',
  evidence_references: '',
}

const EMPTY_PROVIDER = {
  professional_name: '',
  registration_authority: '',
  registration_number: '',
  qualifications: '',
  specialization: '',
  public_profile: '',
  public_contact_email: '',
  evidence_references: '',
}

function splitList(value) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function statusLabel(status = '') {
  return status.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase())
}

function Status({ value }) {
  return <span className={`registry-status registry-status-${value?.toLowerCase() || 'unknown'}`}>{statusLabel(value)}</span>
}

function Empty({ children }) {
  return <p className="registry-empty">{children}</p>
}

export default function RegistryWorkspace({ token, user }) {
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [organizations, setOrganizations] = useState([])
  const [providers, setProviders] = useState([])
  const [organizationApplications, setOrganizationApplications] = useState([])
  const [providerApplications, setProviderApplications] = useState([])
  const [adminAffiliations, setAdminAffiliations] = useState([])
  const [histories, setHistories] = useState({})
  const [providerProfile, setProviderProfile] = useState(null)
  const [affiliations, setAffiliations] = useState([])
  const [managedOrganizations, setManagedOrganizations] = useState([])
  const [teams, setTeams] = useState({})
  const [organizationForm, setOrganizationForm] = useState(EMPTY_ORGANIZATION)
  const [providerForm, setProviderForm] = useState(EMPTY_PROVIDER)
  const [connectionReason, setConnectionReason] = useState('I would like to establish a care connection.')
  const [connectionSelection, setConnectionSelection] = useState({})

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    const jobs = await Promise.allSettled([
      api.registryOrganizations(token),
      api.registryProviders(token),
      api.myOrganizationApplications(token),
      api.myProviderApplications(token),
      api.myProviderProfile(token),
      api.myProviderAffiliations(token),
      api.managedOrganizations(token),
      ...(user.role === 'admin'
        ? [api.adminOrganizationApplications(token), api.adminProviderApplications(token), api.adminAffiliations(token)]
        : []),
    ])
    const [orgDirectory, providerDirectory, ownOrgApplications, ownProviderApplications, ownProfile, ownAffiliations, managed, adminOrgs, adminProviders, adminMemberships] = jobs
    const value = (result, fallback) => result.status === 'fulfilled' ? result.value : fallback
    setOrganizations(value(orgDirectory, []))
    setProviders(value(providerDirectory, []))
    setOrganizationApplications(value(ownOrgApplications, []))
    setProviderApplications(value(ownProviderApplications, []))
    setProviderProfile(value(ownProfile, null))
    setAffiliations(value(ownAffiliations, []))
    setManagedOrganizations(value(managed, []))
    if (ownProfile.status === 'fulfilled' && ownProfile.value) {
      const profile = ownProfile.value
      setProviderForm((current) => ({
        ...current,
        professional_name: profile.professional_name || current.professional_name,
        registration_authority: profile.registration_authority || current.registration_authority,
        registration_number: profile.registration_number || current.registration_number,
        qualifications: profile.qualifications?.join(', ') || current.qualifications,
        specialization: profile.specialization || current.specialization,
        public_profile: profile.public_profile || current.public_profile,
        public_contact_email: profile.public_contact_email || current.public_contact_email,
      }))
    }

    if (user.role === 'admin') {
      setOrganizationApplications(value(adminOrgs, []))
      setProviderApplications(value(adminProviders, []))
      setAdminAffiliations(value(adminMemberships, []))
    }

    const activeOrganizations = value(managed, []).filter((organization) => organization.status === 'APPROVED')
    const teamResults = await Promise.all(activeOrganizations.map(async (organization) => {
      const results = await Promise.allSettled([
        api.organizationAffiliations(organization.id, token),
        api.providerCandidates(organization.id, token),
      ])
      return [organization.id, {
        affiliations: value(results[0], []),
        candidates: value(results[1], []),
        error: results.filter((result) => result.status === 'rejected').map((result) => result.reason.message).join(' '),
      }]
    }))
    setTeams(Object.fromEntries(teamResults))

    const requiredResults = [
      orgDirectory,
      providerDirectory,
      ownOrgApplications,
      ownProviderApplications,
      ownAffiliations,
      managed,
      ...(user.role === 'admin' ? [adminOrgs, adminProviders, adminMemberships] : []),
    ]
    const failed = requiredResults.filter((result) => result.status === 'rejected')
    if (ownProfile.status === 'rejected' && ownProfile.reason.message !== 'No provider application exists') {
      failed.push(ownProfile)
    }
    const teamErrors = teamResults.map(([, team]) => team.error).filter(Boolean)
    if (teamErrors.length) failed.push({ reason: { message: teamErrors.join(' ') } })
    if (failed.length) setError(failed.map((result) => result.reason.message).join(' '))
    setLoading(false)
  }, [token, user.role])

  useEffect(() => { refresh() }, [refresh])

  async function perform(label, action, successMessage) {
    setBusy(label)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(successMessage)
      await refresh()
      return true
    } catch (requestError) {
      setError(requestError.message)
      return false
    } finally {
      setBusy('')
    }
  }

  async function submitOrganization(event) {
    event.preventDefault()
    const payload = {
      legal_name: organizationForm.legal_name,
      display_name: organizationForm.display_name,
      organization_type: organizationForm.organization_type,
      registration_authority: organizationForm.registration_authority || null,
      registration_identifier: organizationForm.registration_identifier || null,
      address: Object.fromEntries([
        ['city', organizationForm.city],
        ['country', organizationForm.country],
      ].filter(([, value]) => value.trim())),
      contact_email: organizationForm.contact_email || null,
      contact_phone: organizationForm.contact_phone || null,
      administrative_contact_name: organizationForm.administrative_contact_name,
      administrative_contact_email: organizationForm.administrative_contact_email,
      evidence_references: splitList(organizationForm.evidence_references),
    }
    if (await perform('organization-application', () => api.submitOrganizationApplication(payload, token), 'Organization application submitted for review.')) {
      setOrganizationForm(EMPTY_ORGANIZATION)
    }
  }

  async function submitProvider(event) {
    event.preventDefault()
    const payload = {
      professional_name: providerForm.professional_name,
      registration_authority: providerForm.registration_authority,
      registration_number: providerForm.registration_number,
      qualifications: splitList(providerForm.qualifications),
      specialization: providerForm.specialization || null,
      public_profile: providerForm.public_profile || null,
      public_contact_email: providerForm.public_contact_email || null,
      evidence_references: splitList(providerForm.evidence_references),
    }
    await perform('provider-application', () => api.submitProviderApplication(payload, token), 'Provider application submitted for manual review.')
  }

  async function decideOrganization(application, decision) {
    await perform(`org-${application.id}`, () => api.decideOrganizationApplication(
      application.id,
      { decision, reason: `Platform administrator recorded ${statusLabel(decision).toLowerCase()} after manual review.` },
      token,
    ), `Organization ${statusLabel(decision).toLowerCase()}.`)
  }

  async function decideProvider(application, decision) {
    await perform(`provider-${application.id}`, () => api.decideProviderApplication(
      application.id,
      { decision, reason: `Platform administrator recorded ${statusLabel(decision).toLowerCase()} after manual review.` },
      token,
    ), `Provider ${statusLabel(decision).toLowerCase()}.`)
  }

  async function initiateConnection(provider) {
    const organizationId = connectionSelection[provider.id]
    if (!organizationId) {
      setError('Choose a healthcare organization for this care connection.')
      return
    }
    await perform(`connection-${provider.id}`, () => api.initiateCareConnection({
      provider_id: provider.id,
      organization_id: organizationId,
      reason: connectionReason,
    }, token), 'Care connection initiated.')
  }

  async function respond(affiliation, decision) {
    await perform(`response-${affiliation.id}`, () => api.respondToAffiliation(
      affiliation.id,
      { decision, reason: decision === 'ACCEPTED' ? 'Provider accepted the organization invitation.' : 'Provider declined the organization invitation.' },
      token,
    ), `Invitation ${decision === 'ACCEPTED' ? 'accepted' : 'declined'}.`)
  }

  async function invite(organization, providerId) {
    if (!providerId) return
    await perform(`invite-${organization.id}`, () => api.inviteProvider(
      organization.id,
      { provider_id: providerId, organization_role: 'PROVIDER', invitation_message: 'Please review this organization affiliation invitation.' },
      token,
    ), 'Provider invitation sent.')
  }

  async function decideAffiliation(organization, affiliation, decision) {
    await perform(`affiliation-${affiliation.id}`, () => api.decideAffiliation(
      organization.id,
      affiliation.id,
      { decision, reason: `Organization administrator recorded ${statusLabel(decision).toLowerCase()}.` },
      token,
    ), `Affiliation ${statusLabel(decision).toLowerCase()}.`)
  }

  async function toggleHistory(key, loadHistory) {
    if (histories[key]) {
      setHistories((current) => ({ ...current, [key]: null }))
      return
    }
    setBusy(key)
    setError('')
    try {
      const history = await loadHistory()
      setHistories((current) => ({ ...current, [key]: history }))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy('')
    }
  }

  const isAdmin = user.role === 'admin'
  const canApply = !isAdmin
  const hasProviderApplication = providerApplications.length > 0
  const hasOrganizationApplication = organizationApplications.length > 0

  return (
    <div className="registry-workspace">
      {error && <div className="error" role="alert">{error}</div>}
      {message && <div className="success" role="status">{message}</div>}
      {loading ? <section className="card"><p className="muted">Loading the verified care network…</p></section> : (
        <>
          <section className="registry-intro card">
            <div>
              <p className="eyebrow">TRUSTED CARE NETWORK</p>
              <h2>Verified organizations and professionals</h2>
              <p className="muted">Directory profiles are shown only when organization approval, professional verification, and active affiliation requirements are met.</p>
            </div>
            <div className="registry-counts" aria-label="Directory totals">
              <span><strong>{organizations.length}</strong> organizations</span>
              <span><strong>{providers.length}</strong> providers</span>
            </div>
          </section>

          <div className="registry-directory-grid">
            <section className="card">
              <div className="card-heading-row"><div><p className="eyebrow">ORGANIZATIONS</p><h2>Participating care teams</h2></div></div>
              {organizations.length ? <div className="registry-list">
                {organizations.map((organization) => (
                  <article className="registry-item" key={organization.id}>
                    <div><h3>{organization.display_name}</h3><p>{organization.legal_name}</p></div>
                    <Status value={organization.organization_type} />
                    <p>{[organization.address?.city, organization.address?.country].filter(Boolean).join(', ') || 'Location not listed'}</p>
                    {organization.contact_email && <a href={`mailto:${organization.contact_email}`}>{organization.contact_email}</a>}
                  </article>
                ))}
              </div> : <Empty>No approved organizations are listed yet.</Empty>}
            </section>
            <section className="card">
              <div className="card-heading-row"><div><p className="eyebrow">PROFESSIONALS</p><h2>Verified providers</h2></div></div>
              {providers.length ? <div className="registry-list">
                {providers.map((provider) => (
                  <article className="registry-item" key={provider.id}>
                    <div><h3>{provider.professional_name}</h3><p>{provider.specialization || 'Healthcare professional'}</p></div>
                    <p>{provider.qualifications.join(' · ')}</p>
                    <p className="registry-registration">Registration: {provider.registration_authority} · {provider.registration_number}</p>
                    {provider.public_profile && <p>{provider.public_profile}</p>}
                    <div className="registry-tags">{provider.organizations.map((organization) => <span key={organization.id}>{organization.display_name}</span>)}</div>
                    {provider.public_contact_email && <a href={`mailto:${provider.public_contact_email}`}>{provider.public_contact_email}</a>}
                    {user.role === 'patient' && <div className="registry-actions">
                      <label>Organization<select value={connectionSelection[provider.id] || ''} onChange={(event) => setConnectionSelection((current) => ({ ...current, [provider.id]: event.target.value }))}><option value="">Choose organization</option>{provider.organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.display_name}</option>)}</select></label>
                      <label>Reason<input value={connectionReason} maxLength={1000} onChange={(event) => setConnectionReason(event.target.value)} /></label>
                      <button type="button" className="btn-primary" disabled={busy === `connection-${provider.id}`} onClick={() => initiateConnection(provider)}>Initiate care connection</button>
                    </div>}
                  </article>
                ))}
              </div> : <Empty>No currently affiliated verified providers are listed.</Empty>}
            </section>
          </div>

          {canApply && <div className="registry-directory-grid">
            <section className="card">
              <p className="eyebrow">ORGANIZATION ONBOARDING</p>
              <h2>Apply to join the network</h2>
              <p className="muted">Applications are reviewed by a platform administrator. Submission does not itself grant exchange access.</p>
              {hasOrganizationApplication && <div className="registry-status-list">
                {organizationApplications.map((application) => <div key={application.id}><strong>{application.display_name}</strong><Status value={application.status} />{application.decision_reason && <p>{application.decision_reason}</p>}</div>)}
              </div>}
              {(!hasOrganizationApplication || organizationApplications[0]?.status === 'REJECTED') && (
                <form className="registry-form" onSubmit={submitOrganization}>
                  <label>Legal name<input required minLength={2} maxLength={200} value={organizationForm.legal_name} onChange={(event) => setOrganizationForm({ ...organizationForm, legal_name: event.target.value })} /></label>
                  <label>Display name<input required minLength={2} maxLength={160} value={organizationForm.display_name} onChange={(event) => setOrganizationForm({ ...organizationForm, display_name: event.target.value })} /></label>
                  <label>Organization type<select value={organizationForm.organization_type} onChange={(event) => setOrganizationForm({ ...organizationForm, organization_type: event.target.value })}><option value="HOSPITAL">Hospital</option><option value="CLINIC">Clinic</option><option value="DIAGNOSTIC_LABORATORY">Diagnostic laboratory</option><option value="OTHER">Other</option></select></label>
                  <label>Registration authority<input maxLength={160} value={organizationForm.registration_authority} onChange={(event) => setOrganizationForm({ ...organizationForm, registration_authority: event.target.value })} /></label>
                  <label>Registration identifier<input maxLength={160} value={organizationForm.registration_identifier} onChange={(event) => setOrganizationForm({ ...organizationForm, registration_identifier: event.target.value })} /></label>
                  <div className="registry-form-row"><label>City<input maxLength={100} value={organizationForm.city} onChange={(event) => setOrganizationForm({ ...organizationForm, city: event.target.value })} /></label><label>Country<input maxLength={100} value={organizationForm.country} onChange={(event) => setOrganizationForm({ ...organizationForm, country: event.target.value })} /></label></div>
                  <label>Public contact email<input type="email" value={organizationForm.contact_email} onChange={(event) => setOrganizationForm({ ...organizationForm, contact_email: event.target.value })} /></label>
                  <label>Contact phone<input maxLength={40} value={organizationForm.contact_phone} onChange={(event) => setOrganizationForm({ ...organizationForm, contact_phone: event.target.value })} /></label>
                  <label>Administrative contact name<input required minLength={2} maxLength={120} value={organizationForm.administrative_contact_name} onChange={(event) => setOrganizationForm({ ...organizationForm, administrative_contact_name: event.target.value })} /></label>
                  <label>Administrative contact email<input required type="email" value={organizationForm.administrative_contact_email} onChange={(event) => setOrganizationForm({ ...organizationForm, administrative_contact_email: event.target.value })} /></label>
                  <label>Evidence reference IDs, comma separated<input placeholder="opaque-reference-1, opaque-reference-2" value={organizationForm.evidence_references} onChange={(event) => setOrganizationForm({ ...organizationForm, evidence_references: event.target.value })} /><small className="field-note">Use internal reference IDs only, not URLs or file paths.</small></label>
                  <button className="btn-primary" disabled={busy === 'organization-application'}>{busy === 'organization-application' ? 'Submitting…' : 'Submit organization application'}</button>
                </form>
              )}
            </section>

            <section className="card">
              <p className="eyebrow">PROVIDER VERIFICATION</p>
              <h2>Professional profile</h2>
              <p className="muted">Your account role alone does not establish professional verification. A platform administrator reviews your registration details.</p>
              {providerProfile && <div className="registry-profile-state"><Status value={providerProfile.status} />{providerProfile.decision_reason && <p>{providerProfile.decision_reason}</p>}</div>}
              {providerApplications.map((application) => <div className="registry-status-list" key={application.id}><div><strong>Application status</strong><Status value={application.status} /></div>{application.decision_reason && <p>{application.decision_reason}</p>}</div>)}
              {(!hasProviderApplication || providerApplications[0]?.status === 'REJECTED') && (
                <form className="registry-form" onSubmit={submitProvider}>
                  <label>Professional name<input required minLength={2} maxLength={160} value={providerForm.professional_name} onChange={(event) => setProviderForm({ ...providerForm, professional_name: event.target.value })} /></label>
                  <label>Registration authority<input required minLength={2} maxLength={160} value={providerForm.registration_authority} onChange={(event) => setProviderForm({ ...providerForm, registration_authority: event.target.value })} /></label>
                  <label>Registration number<input required minLength={2} maxLength={120} value={providerForm.registration_number} onChange={(event) => setProviderForm({ ...providerForm, registration_number: event.target.value })} /></label>
                  <label>Qualifications, comma separated<input required placeholder="Degree or qualification" value={providerForm.qualifications} onChange={(event) => setProviderForm({ ...providerForm, qualifications: event.target.value })} /></label>
                  <label>Specialization<input maxLength={120} value={providerForm.specialization} onChange={(event) => setProviderForm({ ...providerForm, specialization: event.target.value })} /></label>
                  <label>Public profile<textarea maxLength={1000} rows="3" value={providerForm.public_profile} onChange={(event) => setProviderForm({ ...providerForm, public_profile: event.target.value })} /></label>
                  <label>Public contact email<input type="email" value={providerForm.public_contact_email} onChange={(event) => setProviderForm({ ...providerForm, public_contact_email: event.target.value })} /></label>
                  <label>Evidence reference IDs, comma separated<input placeholder="opaque-reference-1, opaque-reference-2" value={providerForm.evidence_references} onChange={(event) => setProviderForm({ ...providerForm, evidence_references: event.target.value })} /><small className="field-note">Use internal reference IDs only, not URLs or file paths.</small></label>
                  <button className="btn-primary" disabled={busy === 'provider-application'}>{busy === 'provider-application' ? 'Submitting…' : 'Submit for verification'}</button>
                </form>
              )}
            </section>
          </div>}

          {affiliations.length > 0 && <section className="card">
            <p className="eyebrow">PROVIDER AFFILIATIONS</p><h2>Organization invitations and membership</h2>
            <div className="registry-list">
              {affiliations.map((affiliation) => <article className="registry-item registry-affiliation" key={affiliation.id}>
                <div><h3>{affiliation.organization_name}</h3><Status value={affiliation.status} /></div>
                {affiliation.invitation_message && <p>{affiliation.invitation_message}</p>}
                {affiliation.decision_reason && <p>{affiliation.decision_reason}</p>}
                {affiliation.status === 'INVITED' && <div className="registry-actions"><button className="btn-primary" disabled={busy === `response-${affiliation.id}`} onClick={() => respond(affiliation, 'ACCEPTED')}>Accept</button><button className="btn-ghost" disabled={busy === `response-${affiliation.id}`} onClick={() => respond(affiliation, 'REJECTED')}>Decline</button></div>}
              </article>)}
            </div>
          </section>}

          {managedOrganizations.length > 0 && <section className="card">
            <p className="eyebrow">ORGANIZATION ADMINISTRATION</p><h2>Your organization teams</h2>
            <div className="registry-orgs">
              {managedOrganizations.map((organization) => {
                const team = teams[organization.id] || { affiliations: [], candidates: [], error: '' }
                return <article className="registry-org-card" key={organization.id}>
                  <div className="card-heading-row"><div><h3>{organization.display_name}</h3><p>{organization.legal_name}</p></div><Status value={organization.status} /></div>
                  {team.error && <div className="error" role="alert">{team.error}</div>}
                  {organization.status === 'APPROVED'
                    ? <form className="registry-invite-form" onSubmit={(event) => { event.preventDefault(); invite(organization, event.currentTarget.elements.provider_id.value) }}>
                      <label>Invite verified provider<select name="provider_id" defaultValue=""><option value="">Choose provider</option>{team.candidates.map((provider) => <option key={provider.id} value={provider.id}>{provider.professional_name}{provider.specialization ? ` · ${provider.specialization}` : ''}</option>)}</select></label>
                      <button className="btn-primary" disabled={!team.candidates.length || busy === `invite-${organization.id}`}>{team.candidates.length ? 'Send invitation' : 'No providers available'}</button>
                    </form>
                    : <p>Organization administration is unavailable while this organization is {statusLabel(organization.status).toLowerCase()}.</p>}
                  <div className="registry-list">
                    {team.affiliations.map((affiliation) => <article className="registry-item" key={affiliation.id}>
                      <div><h3>{affiliation.professional_name}</h3><Status value={affiliation.status} /></div>
                      {affiliation.decision_reason && <p>{affiliation.decision_reason}</p>}
                      <div className="registry-actions">
                        {(affiliation.status === 'PENDING' || affiliation.status === 'SUSPENDED') && <button className="btn-primary" onClick={() => decideAffiliation(organization, affiliation, 'APPROVED')}>{affiliation.status === 'SUSPENDED' ? 'Reactivate' : 'Approve'}</button>}
                        {(affiliation.status === 'PENDING' || affiliation.status === 'INVITED') && <button className="btn-ghost" onClick={() => decideAffiliation(organization, affiliation, 'REJECTED')}>Reject</button>}
                        {affiliation.status === 'ACTIVE' && <><button className="btn-ghost" onClick={() => decideAffiliation(organization, affiliation, 'SUSPENDED')}>Suspend</button><button className="btn-ghost" onClick={() => decideAffiliation(organization, affiliation, 'ENDED')}>End affiliation</button></>}
                        {affiliation.status === 'SUSPENDED' && <button className="btn-ghost" onClick={() => decideAffiliation(organization, affiliation, 'ENDED')}>End affiliation</button>}
                      </div>
                    </article>)}
                    {!team.affiliations.length && <Empty>No provider affiliations yet.</Empty>}
                  </div>
                </article>
              })}
            </div>
          </section>}

          {isAdmin && <div className="registry-directory-grid">
            <section className="card">
              <p className="eyebrow">PLATFORM REVIEW</p><h2>Organization applications</h2>
              <div className="registry-list">
                {organizationApplications.map((application) => <article className="registry-item" key={application.id}>
                  <div><h3>{application.display_name}</h3><Status value={application.status} /></div>
                  <p>{application.legal_name} · {statusLabel(application.organization_type)}</p>
                  <p>Registration: {application.registration_authority || 'Not provided'} · {application.registration_identifier || 'Not provided'}</p>
                  <p>Applicant contact: {application.administrative_contact_name} · {application.administrative_contact_email}</p>
                  <p>Evidence references: {application.evidence_references.join(', ') || 'None supplied'}</p>
                  {application.decision_reason && <p>{application.decision_reason}</p>}
                  <div className="registry-actions">
                    {['PENDING', 'UNDER_REVIEW'].includes(application.status) && <>{application.status === 'PENDING' && <button className="btn-ghost" onClick={() => decideOrganization(application, 'UNDER_REVIEW')}>Mark in review</button>}<button className="btn-primary" onClick={() => decideOrganization(application, 'APPROVED')}>Approve</button><button className="btn-ghost" onClick={() => decideOrganization(application, 'REJECTED')}>Reject</button></>}
                    {application.status === 'APPROVED' && <button className="btn-ghost" onClick={() => decideOrganization(application, 'SUSPENDED')}>Suspend organization</button>}
                    {application.status === 'SUSPENDED' && <button className="btn-primary" onClick={() => decideOrganization(application, 'REINSTATED')}>Reinstate organization</button>}
                    <button className="btn-ghost" disabled={busy === `history-org-${application.id}`} onClick={() => toggleHistory(`history-org-${application.id}`, () => api.organizationReviewHistory(application.organization_id, token))}>Review history</button>
                  </div>
                  {histories[`history-org-${application.id}`] && <div className="registry-history">{histories[`history-org-${application.id}`].map((event) => <p key={event.id}><strong>{statusLabel(event.decision)}</strong> · {event.reason} · {new Date(event.created_at).toLocaleString()}</p>)}</div>}
                </article>)}
                {!organizationApplications.length && <Empty>No organization applications await review.</Empty>}
              </div>
            </section>
            <section className="card">
              <p className="eyebrow">PROFESSIONAL REVIEW</p><h2>Provider applications</h2>
              <div className="registry-list">
                {providerApplications.map((application) => <article className="registry-item" key={application.id}>
                  <div><h3>{application.professional_name}</h3><Status value={application.status} /></div>
                  <p>{application.qualifications.join(' · ')}{application.specialization ? ` · ${application.specialization}` : ''}</p>
                  <p>Registration: {application.registration_authority || 'Not provided'} · {application.registration_number || 'Not provided'}</p>
                  <p>Evidence references: {(application.evidence_references || []).join(', ') || 'None supplied'}</p>
                  {application.decision_reason && <p>{application.decision_reason}</p>}
                  <div className="registry-actions">
                    {['PENDING', 'UNDER_REVIEW'].includes(application.status) && <>{application.status === 'PENDING' && <button className="btn-ghost" onClick={() => decideProvider(application, 'UNDER_REVIEW')}>Mark in review</button>}<button className="btn-primary" onClick={() => decideProvider(application, 'APPROVED')}>Verify</button><button className="btn-ghost" onClick={() => decideProvider(application, 'REJECTED')}>Reject</button></>}
                    {application.status === 'VERIFIED' && <button className="btn-ghost" onClick={() => decideProvider(application, 'SUSPENDED')}>Suspend provider</button>}
                    {application.status === 'SUSPENDED' && <button className="btn-primary" onClick={() => decideProvider(application, 'REINSTATED')}>Reinstate provider</button>}
                    <button className="btn-ghost" disabled={busy === `history-provider-${application.id}`} onClick={() => toggleHistory(`history-provider-${application.id}`, () => api.providerReviewHistory(application.provider_id, token))}>Review history</button>
                  </div>
                  {histories[`history-provider-${application.id}`] && <div className="registry-history">{histories[`history-provider-${application.id}`].map((event) => <p key={event.id}><strong>{statusLabel(event.decision)}</strong> · {event.reason} · {new Date(event.created_at).toLocaleString()}</p>)}</div>}
                </article>)}
                {!providerApplications.length && <Empty>No provider applications await review.</Empty>}
              </div>
            </section>
          </div>}
          {isAdmin && <section className="card">
            <p className="eyebrow">MEMBERSHIP OVERSIGHT</p><h2>Organization affiliations</h2>
            <div className="registry-list">
              {adminAffiliations.map((affiliation) => <article className="registry-item" key={affiliation.id}>
                <div><h3>{affiliation.professional_name} · {affiliation.organization_name}</h3><Status value={affiliation.status} /></div>
                <p>Organization role: {statusLabel(affiliation.organization_role)}</p>
                {affiliation.decision_reason && <p>{affiliation.decision_reason}</p>}
              </article>)}
              {!adminAffiliations.length && <Empty>No organization affiliations have been recorded.</Empty>}
            </div>
          </section>}
        </>
      )}
    </div>
  )
}
