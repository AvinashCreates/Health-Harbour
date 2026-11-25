import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import LoadingSkeleton from '../components/LoadingSkeleton'
import TransferStatus from '../components/TransferStatus'

function formatSize(bytes) {
  if (!Number.isFinite(Number(bytes)) || Number(bytes) < 0) return '—'
  const size = Number(bytes)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

export default function Files({ token, user }) {
  const isPhysician = user.role === 'doctor'
  const isLabRole = ['lab', 'lab_supervisor', 'lab_technician'].includes(user.role)
  const [files, setFiles] = useState([])
  const [documentPatients, setDocumentPatients] = useState([])
  const [assignedRequests, setAssignedRequests] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const fileInputRef = useRef(null)
  const [category, setCategory] = useState('clinical-record')
  const [patientId, setPatientId] = useState('')
  const [serviceRequestId, setServiceRequestId] = useState('')
  const [loading, setLoading] = useState(true)
  const [choicesLoading, setChoicesLoading] = useState(isPhysician || isLabRole)
  const [choicesError, setChoicesError] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [listError, setListError] = useState('')
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    setListError('')
    try { setFiles(await api.listFiles(token)) } catch (e) { setListError(e.message) } finally { setLoading(false) }
  }, [token])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    if (!preview?.url) return undefined
    return () => URL.revokeObjectURL(preview.url)
  }, [preview?.url])

  useEffect(() => {
    if (!preview) return undefined
    function closeOnEscape(event) {
      if (event.key === 'Escape') setPreview(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [preview])

  useEffect(() => {
    if (!isPhysician && !isLabRole) return
    let active = true
    const loadChoices = async () => {
      setChoicesLoading(true)
      setChoicesError('')
      try {
        if (isPhysician) {
          const patients = await api.listDocumentPatients(token)
          if (active) setDocumentPatients(patients)
        }
        if (isLabRole) {
          const requests = await api.listServiceRequests(token)
          if (active) setAssignedRequests(requests)
        }
      } catch (e) {
        if (active) setChoicesError(e.message)
      } finally {
        if (active) setChoicesLoading(false)
      }
    }
    loadChoices()
    return () => { active = false }
  }, [token, isPhysician, isLabRole])

  async function upload(e) {
    e.preventDefault()
    if (!selectedFile) return
    if (isPhysician && !patientId) {
      setError('Select a patient with active Document permission.')
      return
    }
    if (isLabRole && !serviceRequestId) {
      setError('Select an assigned service request to link this upload.')
      return
    }
    setBusy(true); setError(''); setMessage('')
    try {
      await api.uploadFile(selectedFile, {
        category,
        ...(isPhysician && patientId ? { patient_id: patientId } : {}),
        ...(serviceRequestId ? { service_request_id: serviceRequestId } : {}),
      }, token)
      setMessage('File uploaded.')
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setCategory('clinical-record'); setPatientId(''); setServiceRequestId('')
      await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function download(file) {
    setError('')
    try {
      const blob = await api.downloadFile(file.id, token)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = file.filename || 'health-record'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(e.message) }
  }

  async function viewFile(file) {
    setPreview({ file, kind: 'loading' })
    try {
      const blob = await api.downloadFile(file.id, token)
      const mediaType = (blob.type || file.media_type || '').split(';')[0].toLowerCase()
      const extension = file.filename?.split('.').pop()?.toLowerCase()
      const kind = mediaType === 'application/pdf' || extension === 'pdf'
        ? 'pdf'
        : mediaType.startsWith('image/') || ['jpg', 'jpeg', 'png'].includes(extension)
          ? 'image'
          : mediaType.startsWith('text/') || ['txt', 'csv'].includes(extension)
            ? 'text'
            : 'unsupported'
      const text = kind === 'text' ? (await blob.text()).replace(/^\uFEFF/, '') : ''
      setPreview({ file, kind, text, url: URL.createObjectURL(blob) })
    } catch (e) {
      setPreview({ file, kind: 'error', error: e.message })
    }
  }

  async function remove(file) {
    if (!window.confirm(`Delete “${file.filename}”? This cannot be undone.`)) return
    setError(''); setMessage('')
    try {
      await api.deleteFile(file.id, token)
      setMessage('File deleted.')
      await refresh()
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="file-page">
      <section className="card file-intro">
        <div><p className="eyebrow">FILE CENTER</p><h2>Health records, in one place</h2><p className="muted">Files shown here are returned by the service for your account. Physicians need an active patient-granted <strong>Document</strong> permission to view or download patient files.</p></div>
      </section>

      <section className="card">
        <div className="card-heading-row"><div><p className="eyebrow">ADD A RECORD</p><h2>Upload a file</h2></div></div>
        <form className="upload-form" onSubmit={upload}>
          <label className="upload-input">Choose a file<input ref={fileInputRef} required type="file" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} /></label>
          <label>Category<select value={category} onChange={(e) => setCategory(e.target.value)}><option value="clinical-record">Clinical record</option><option value="diagnostic-report">Diagnostic report</option><option value="imaging">Imaging</option><option value="other">Other</option></select></label>
          {isPhysician && <label>Patient with Document permission<select required value={patientId} onChange={(e) => setPatientId(e.target.value)} disabled={choicesLoading || Boolean(choicesError)}><option value="">Select a patient</option>{documentPatients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name || patient.name || 'Patient'}{patient.email ? ` · ${patient.email}` : ''}</option>)}</select></label>}
          {isLabRole && <label>Assigned service request<select required value={serviceRequestId} onChange={(e) => setServiceRequestId(e.target.value)} disabled={choicesLoading || Boolean(choicesError)}><option value="">Select a request</option>{assignedRequests.map((request) => <option key={request.id} value={request.id}>{request.resource?.code?.text || 'Service request'} · {request.workflow_status?.replaceAll('_', ' ').toLowerCase() || request.resource?.status || 'Current'}</option>)}</select></label>}
          {choicesLoading && <p className="muted" role="status">Loading upload options…</p>}
          {choicesError && <p className="error" role="alert">Could not load upload options. {choicesError}</p>}
          {isPhysician && !choicesLoading && !choicesError && documentPatients.length === 0 && <p className="muted">No patients with active Document permission are available for upload.</p>}
          {isLabRole && !choicesLoading && !choicesError && assignedRequests.length === 0 && <p className="muted">No assigned service requests are available for workflow-linked uploads.</p>}
          <button className="btn-primary" type="submit" disabled={!selectedFile || busy || choicesLoading || Boolean(choicesError) || (isPhysician && !patientId) || (isLabRole && !serviceRequestId)}>{busy ? 'Uploading…' : 'Upload file'}</button>
          {busy && <TransferStatus>Uploading record</TransferStatus>}
        </form>
        <p className="muted file-note">The service validates who may upload and who may receive each file. Uploading does not itself grant another person access.</p>
        {message && <div className="success" role="status">{message}</div>}
        {error && <div className="error" role="alert">{error}</div>}
      </section>

      <section className="card">
        <div className="card-heading-row"><div><p className="eyebrow">AVAILABLE RECORDS</p><h2>Files</h2></div><button type="button" className="btn-ghost" onClick={refresh} disabled={loading}>Refresh list</button></div>
        {loading ? <LoadingSkeleton cards={2} label="Loading available records" /> : listError ? <div className="error" role="alert">Could not load the file list. {listError}</div> : files.length === 0 ? <div className="empty-state"><strong>No files are available yet</strong><p className="muted">{user.role === 'patient' ? 'Upload a record above to get started. A physician will only see patient files when the required Document permission is active.' : 'The service has not returned files for this account. Patient files require active Document permission.'}</p></div> : (
          <div className="file-list">
            {files.map((file) => <article className="file-row" key={file.id}>
              <div className="file-icon" aria-hidden="true">▤</div>
              <div className="file-meta"><strong>{file.filename}</strong><span>{file.category || 'Clinical record'} · {formatSize(file.size_bytes)} · {formatDate(file.created_at)}</span><small>{file.patient_name ? `Patient: ${file.patient_name}` : `Uploaded by ${file.uploaded_by_name || 'care team'}`}{file.workflow_status ? ` · ${file.workflow_status.replaceAll('_', ' ').toLowerCase()}` : ''}</small></div>
              <div className="file-actions"><button className="btn-ghost" type="button" onClick={() => viewFile(file)} disabled={Boolean(preview?.kind === 'loading')}>View</button><button className="btn-ghost" type="button" onClick={() => download(file)}>Download</button>{user.role === 'patient' && file.can_delete && <button className="btn-danger-ghost" type="button" onClick={() => remove(file)}>Delete</button>}</div>
            </article>)}
          </div>
        )}
      </section>
      {preview && <div className="file-preview-backdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setPreview(null)
      }}>
        <section className="file-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="file-preview-title">
          <header className="file-preview-header">
            <div>
              <p className="eyebrow">RECORD PREVIEW</p>
              <h2 id="file-preview-title">{preview.file.filename}</h2>
            </div>
            <button type="button" className="btn-ghost" onClick={() => setPreview(null)} aria-label="Close file preview">Close</button>
          </header>
          <dl className="file-preview-details">
            <div><dt>Category</dt><dd>{preview.file.category || 'Clinical record'}</dd></div>
            <div><dt>File size</dt><dd>{formatSize(preview.file.size_bytes)}</dd></div>
            <div><dt>Added</dt><dd>{formatDate(preview.file.created_at)}</dd></div>
            <div><dt>Uploaded by</dt><dd>{preview.file.uploaded_by_name || 'Care team'}</dd></div>
            {preview.file.patient_name && <div><dt>Patient</dt><dd>{preview.file.patient_name}</dd></div>}
          </dl>
          <div className="file-preview-content">
            {preview.kind === 'loading' && <p className="muted" role="status">Loading file preview…</p>}
            {preview.kind === 'error' && <p className="error" role="alert">Could not load this file. {preview.error}</p>}
            {preview.kind === 'pdf' && <iframe className="file-preview-pdf" src={preview.url} title={`Preview of ${preview.file.filename}`} />}
            {preview.kind === 'image' && <img className="file-preview-image" src={preview.url} alt={`Preview of ${preview.file.filename}`} />}
            {preview.kind === 'text' && <pre className="file-preview-text">{preview.text || 'This file is empty.'}</pre>}
            {preview.kind === 'unsupported' && <div className="empty-state"><strong>Preview is not available for this file type</strong><p className="muted">Download the file to open it with a compatible application.</p></div>}
          </div>
          <footer className="file-preview-footer">
            <button type="button" className="btn-ghost" onClick={() => download(preview.file)}>Download file</button>
            <button type="button" className="btn-primary" onClick={() => setPreview(null)}>Done</button>
          </footer>
        </section>
      </div>}
    </div>
  )
}
