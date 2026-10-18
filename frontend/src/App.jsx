import { useCallback, useEffect, useState } from 'react'
import { Activity, Menu } from 'lucide-react'
import Sidebar from './components/Sidebar.jsx'
import ChatPanel from './components/ChatPanel.jsx'

async function api(path, options = {}) {
  const response = await fetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export default function App() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [apiOnline, setApiOnline] = useState(null)

  const refreshDocuments = useCallback(async () => {
    try {
      const [items] = await Promise.all([api('/api/documents'), api('/api/health')])
      setDocuments(items)
      setApiOnline(true)
    } catch {
      setApiOnline(false)
    }
  }, [])

  useEffect(() => { refreshDocuments() }, [refreshDocuments])

  async function uploadFiles(files) {
    setUploading(true)
    setUploadError('')
    try {
      const form = new FormData()
      files.forEach((file) => form.append('files', file))
      const result = await api('/api/documents/upload', { method: 'POST', body: form })
      await refreshDocuments()
      const added = result.documents.filter((document) => !document.duplicate).length
      const duplicates = result.documents.length - added
      if (duplicates) setUploadError(`${duplicates} duplicate ${duplicates === 1 ? 'file was' : 'files were'} already indexed.`)
      setMobileOpen(false)
    } catch (error) {
      setUploadError(error.message)
    } finally {
      setUploading(false)
    }
  }

  async function deleteDocument(id) {
    try {
      await api(`/api/documents/${id}`, { method: 'DELETE' })
      await refreshDocuments()
    } catch (error) {
      setUploadError(error.message)
    }
  }

  async function ask(question) {
    setBusy(true)
    try {
      return await api('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 }),
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <Sidebar documents={documents} onUpload={uploadFiles} onDelete={deleteDocument} uploading={uploading} error={uploadError} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="content-shell">
        <div className="mobile-brand"><button className="icon-button" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={19} /></button><strong>FILED<span>/</span></strong></div>
        <div className={`connection-banner ${apiOnline === false ? 'connection-offline' : ''}`}><Activity size={13} />{apiOnline === null ? 'CONNECTING TO LOCAL INDEX' : apiOnline ? 'LOCAL INDEX CONNECTED' : 'API OFFLINE · START FASTAPI ON PORT 8000'}</div>
        <ChatPanel documents={documents} onQuery={ask} busy={busy} mobileMenu={() => setMobileOpen(true)} />
      </div>
    </div>
  )
}