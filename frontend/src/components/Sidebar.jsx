import { useRef } from 'react'
import { FileText, FolderOpen, Plus, Search, Trash2, Upload, X } from 'lucide-react'

function formatDate(value) {
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(value))
}

export default function Sidebar({ documents, onUpload, onDelete, uploading, error, mobileOpen, onClose }) {
  const inputRef = useRef(null)

  function handleFiles(event) {
    const files = [...(event.target.files || [])]
    if (files.length) onUpload(files)
    event.target.value = ''
  }

  return (
    <>
      {mobileOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={onClose} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true"><span /></div>
          <div className="brand-name">FILED<span>/</span></div>
          <button className="icon-button sidebar-close" aria-label="Close menu" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="workspace-label">RESEARCH DESK <span className="live-dot" /></div>
        <button className="nav-item nav-active"><Search size={16} strokeWidth={1.8} /><span>Ask your filings</span><span className="nav-key">⌘ K</span></button>
        <div className="section-heading"><span>YOUR LIBRARY</span><span>{documents.length.toString().padStart(2, '0')}</span></div>

        <button className="upload-button" onClick={() => inputRef.current?.click()} disabled={uploading}>
          {uploading ? <span className="spinner" /> : <Plus size={17} />}
          <span>{uploading ? 'Adding files…' : 'Add documents'}</span>
          {!uploading && <Upload size={14} className="upload-trail" />}
        </button>
        <input ref={inputRef} type="file" accept=".pdf,.txt,application/pdf,text/plain" multiple hidden onChange={handleFiles} />
        {error && <p className="sidebar-error">{error}</p>}

        <div className="document-list">
          {documents.length === 0 ? (
            <div className="empty-library"><FolderOpen size={18} /><span>Your library is empty</span></div>
          ) : documents.map((document) => (
            <div className="document-row" key={document.id}>
              <FileText size={16} className="document-icon" />
              <div className="document-info">
                <span className="document-name" title={document.filename}>{document.filename}</span>
                <span className="document-meta">{document.file_type.toUpperCase()} · {document.chunk_count} passages · {formatDate(document.created_at)}</span>
              </div>
              <button className="delete-button" aria-label={`Remove ${document.filename}`} title="Remove document" onClick={() => onDelete(document.id)}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="privacy-icon"><span /></div>
          <div><strong>Private by default</strong><span>Documents stay on this machine</span></div>
        </div>
      </aside>
    </>
  )
}