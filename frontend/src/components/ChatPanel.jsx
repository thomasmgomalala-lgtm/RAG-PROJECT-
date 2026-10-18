import { useEffect, useRef, useState } from 'react'
import { ArrowUp, BookOpen, ChevronDown, FileText, Menu, RotateCcw, Sparkles } from 'lucide-react'

const prompts = [
  { label: 'Financial trend', question: 'How did revenue and operating income change year over year?' },
  { label: 'Liquidity', question: 'What are the company’s main liquidity sources and capital commitments?' },
  { label: 'Risk factors', question: 'What risks does Tesla disclose around autonomous driving?' },
]

export default function ChatPanel({ documents, onQuery, busy, mobileMenu }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  useEffect(() => {
    function onKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  async function submit(value = question) {
    const cleanQuestion = value.trim()
    if (!cleanQuestion || busy) return
    setError('')
    setQuestion('')
    setMessages((current) => [...current, { id: crypto.randomUUID(), question: cleanQuestion, pending: true }])
    try {
      const response = await onQuery(cleanQuestion)
      setMessages((current) => current.map((message) => message.pending ? { ...message, pending: false, response } : message))
    } catch (queryError) {
      setMessages((current) => current.filter((message) => !message.pending))
      setError(queryError.message || 'Could not reach the research API.')
    }
  }

  function reset() {
    setMessages([])
    setError('')
    inputRef.current?.focus()
  }

  return (
    <main className="main-panel">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="Open library" onClick={mobileMenu}><Menu size={19} /></button>
        <div className="breadcrumb">WORKSPACE <span>/</span> <strong>RESEARCH</strong></div>
        <div className="topbar-right"><span className="status-indicator" /> LOCAL INDEX <span className="topbar-divider" /> <button className="icon-button reset-button" onClick={reset} aria-label="Clear conversation" title="Clear conversation"><RotateCcw size={15} /></button></div>
      </header>

      <section className={`conversation ${messages.length ? 'conversation-active' : ''}`}>
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="eyebrow"><span className="eyebrow-line" /> DOCUMENT INTELLIGENCE / 01</div>
            <h1>Read between<br /><em>the filings.</em></h1>
            <p className="welcome-copy">Welcome. Ask a question across your reports and follow each answer back to its source.</p>

            <div className="prompt-grid">
              {prompts.map((prompt, index) => (
                <button className="prompt-card" key={prompt.label} onClick={() => submit(prompt.question)} disabled={busy || documents.length === 0}>
                  <span className="prompt-index">0{index + 1}</span>
                  <span className="prompt-label">{prompt.label}</span>
                  <span className="prompt-question">{prompt.question}</span>
                  <ArrowUp size={15} className="prompt-arrow" />
                </button>
              ))}
            </div>
            <div className="library-state">
              <div className="state-rule" />
              <span>{documents.length ? `${documents.length} ${documents.length === 1 ? 'document' : 'documents'} indexed` : 'Add a filing to start your research'}</span>
              <div className="state-rule" />
            </div>
          </div>
        ) : (
          <div className="thread">
            {messages.map((message) => <Message key={message.id} message={message} onAskAgain={() => inputRef.current?.focus()} />)}
            {busy && <div className="thinking"><span className="thinking-mark"><Sparkles size={15} /></span><span>Searching your filings</span><i /><i /><i /></div>}
            <div ref={bottomRef} />
          </div>
        )}
      </section>

      {error && <div className="query-error">{error}</div>}
      <footer className="composer-wrap">
        <form className="composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
          <textarea
            ref={inputRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }}
            placeholder={documents.length ? 'Ask something specific about your filings…' : 'Upload a filing to begin asking questions'}
            rows={1}
            disabled={!documents.length || busy}
            aria-label="Ask a question about your documents"
          />
          <div className="composer-controls"><span><kbd>↵</kbd> ask <span className="control-separator">·</span> <kbd>⇧ ↵</kbd> new line</span><button className="send-button" type="submit" disabled={!question.trim() || !documents.length || busy} aria-label="Send question"><ArrowUp size={18} /></button></div>
        </form>
        <p className="disclaimer"><BookOpen size={12} /> Answers use retrieved passages and your configured model; verify important claims against the cited source.</p>
      </footer>
    </main>
  )
}

function Message({ message, onAskAgain }) {
  const hasCitations = Boolean(message.response?.citations?.length)

  return (
    <article className="message">
      <div className="question-line"><div className="question-avatar">Y</div><p>{message.question}</p></div>
      {message.pending ? <div className="thinking"><span className="thinking-mark"><Sparkles size={15} /></span><span>Searching your filings</span><i /><i /><i /></div> : (
        <div className="answer-block">
          <div className="answer-heading"><span className="answer-mark"><Sparkles size={14} /></span><span>RESEARCH NOTE</span><span className="provider-tag">{message.response.provider}</span></div>
          <p className="answer-copy">
            {hasCitations
              ? message.response.answer
              : "Welcome. I couldn't find a matching passage for that question."}
          </p>
          <div className="source-heading"><span>SUPPORTING PASSAGES</span><span>{message.response.citations.length.toString().padStart(2, '0')}</span></div>
          {hasCitations ? message.response.citations.map((citation, index) => (
            <details className="citation" key={`${citation.document_id}-${index}`} open={index === 0}>
              <summary><FileText size={15} /><span className="citation-file">{citation.filename}</span><span className="citation-page">{citation.page ? `PAGE ${citation.page}` : 'TEXT'} · {Math.round(citation.score * 100)}% MATCH</span><ChevronDown size={14} className="citation-chevron" /></summary>
              <p>{citation.excerpt}</p>
            </details>
          )) : (
            <div className="no-source-state">
              <p className="no-sources">Try a different question about the indexed filings.</p>
              <button className="retry-question" type="button" onClick={onAskAgain}>Ask another question <ArrowUp size={14} /></button>
            </div>
          )}
        </div>
      )}
    </article>
  )
}