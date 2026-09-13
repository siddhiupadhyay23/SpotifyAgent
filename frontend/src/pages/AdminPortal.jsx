import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Bot, CheckCircle2, ChevronDown, Clock3, Loader2, MessageSquareText, RefreshCw, Send, ShieldCheck, UserRound } from 'lucide-react'
import { cn } from '../lib/utils'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const ADMIN_SESSION_KEY = 'spotifyagent.admin-session'

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

function formatTime(value) {
  if (!value) return 'No messages yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  if (date.toDateString() === now.toDateString()) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function StatusBadge({ status, escalation = false }) {
  if (status === 'resolved') return <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-10 font-semibold text-ink3"><CheckCircle2 size={11} /> Resolved</span>
  if (status === 'escalated' || escalation) return <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-10 font-semibold text-stop-text"><AlertTriangle size={11} /> Needs attention</span>
  return <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-10 font-semibold text-go-text"><span className="h-1.5 w-1.5 rounded-full bg-go" /> Open</span>
}

function InboxRow({ item, selected, onClick }) {
  return <button onClick={onClick} className={cn('w-full border-b border-dline px-4 py-3.5 text-left transition', selected ? 'bg-accent-500/10' : 'hover:bg-white/[0.035]')}>
    <div className="mb-1.5 flex items-center justify-between gap-2"><p className="truncate text-13 font-semibold text-dtxt">{item.customer_name}</p><span className="shrink-0 text-10 text-dtxt3">{formatTime(item.updated_at)}</span></div>
    <p className="mb-2 truncate text-11 text-dtxt3">{item.customer_email}</p>
    <p className="truncate text-12 text-dtxt2">{item.last_message || 'No messages yet'}</p>
    <div className="mt-2.5 flex items-center justify-between"><StatusBadge status={item.status} escalation={item.has_escalation} /><span className="text-10 text-dtxt3">{item.message_count} {item.message_count === 1 ? 'message' : 'messages'}</span></div>
  </button>
}

function DecisionPanel({ decision }) {
  const [expanded, setExpanded] = useState(false)
  if (!decision) return null
  const evidence = Array.isArray(decision.retrieval_evidence) ? decision.retrieval_evidence : []
  const escalated = decision.decision === 'ESCALATE'
  return <div className={cn('mt-2 overflow-hidden rounded-lg border', escalated ? 'border-stop/30 bg-stop/5' : 'border-accent-500/20 bg-accent-500/5')}>
    <button onClick={() => setExpanded(value => !value)} className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"><span className={cn('flex items-center gap-1.5 text-10 font-bold uppercase tracking-caps', escalated ? 'text-stop' : 'text-accent-400')}><Bot size={12} /> AI decision · {escalated ? 'Escalate' : 'Auto-handle'}</span><ChevronDown className={cn('text-dtxt3 transition-transform', expanded && 'rotate-180')} size={14} /></button>
    {expanded && <div className="space-y-3 border-t border-dline px-3 py-3 text-11"><div className="grid grid-cols-3 gap-3"><div><p className="text-dtxt3">Intent</p><p className="mt-0.5 font-semibold text-dtxt">{decision.intent?.replaceAll('_', ' ')}</p></div><div><p className="text-dtxt3">Confidence</p><p className="mt-0.5 font-semibold text-dtxt">{Math.round((decision.confidence || 0) * 100)}%</p></div><div><p className="text-dtxt3">Platform</p><p className="mt-0.5 font-semibold capitalize text-dtxt">{decision.platform || 'Unknown'}</p></div></div><div><p className="text-dtxt3">Escalation reason</p><p className="mt-0.5 leading-relaxed text-dtxt2">{decision.escalation_reason || 'No escalation required.'}</p></div>{evidence.length > 0 && <div><p className="mb-1.5 text-dtxt3">Retrieved evidence</p><div className="space-y-1.5">{evidence.slice(0, 3).map((item, index) => <div key={index} className="rounded bg-black/10 p-2"><p className="text-dtxt2">{item.customer_msg}</p><p className="mt-1 text-dtxt3">Similarity {Math.round((item.score || 0) * 100)}% · {item.platform || 'unknown platform'}</p></div>)}</div></div>}</div>}
  </div>
}

function EmptyInbox() { return <div className="flex flex-1 flex-col items-center justify-center px-8 text-center"><MessageSquareText size={28} className="mb-3 text-dtxt3" /><h2 className="text-15 font-bold text-dtxt">No conversations here</h2><p className="mt-1 max-w-xs text-12 leading-relaxed text-dtxt3">New customer conversations will appear here automatically.</p></div> }

function AdminLogin({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function login(event) {
    event.preventDefault()
    if (submitting || !email.trim() || !password) return
    setSubmitting(true); setError('')
    try {
      const admin = await api('/admin/login', { method: 'POST', body: JSON.stringify({ email: email.trim(), password }) })
      window.localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(admin))
      onLogin(admin)
    } catch (err) { setError(err.message) } finally { setSubmitting(false) }
  }

  return <main className="flex min-h-screen items-center justify-center bg-dark px-5 text-dtxt"><section className="w-full max-w-md rounded-2xl border border-dline bg-dark2 p-7 shadow-dark-card"><Link to="/" className="mb-7 inline-flex items-center gap-1.5 text-12 font-semibold text-dtxt3 hover:text-dtxt"><ArrowLeft size={14} /> Back to role selection</Link><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-500/20 text-accent-400"><ShieldCheck size={21} /></div><h1 className="mt-5 text-24 font-bold tracking-tight">Support Admin</h1><p className="mt-2 text-13 leading-relaxed text-dtxt2">Sign in to review customer conversations and take over escalated requests.</p><form onSubmit={login} className="mt-6 space-y-4"><div><label htmlFor="admin-email" className="mb-1.5 block text-12 font-semibold text-dtxt2">Email</label><input id="admin-email" value={email} onChange={event => setEmail(event.target.value)} type="email" autoComplete="username" required className="w-full rounded-lg border border-dline bg-dark3 px-3 py-2.5 text-13 text-dtxt outline-none focus:border-accent-500" /></div><div><label htmlFor="admin-password" className="mb-1.5 block text-12 font-semibold text-dtxt2">Password</label><input id="admin-password" value={password} onChange={event => setPassword(event.target.value)} type="password" autoComplete="current-password" required className="w-full rounded-lg border border-dline bg-dark3 px-3 py-2.5 text-13 text-dtxt outline-none focus:border-accent-500" /></div>{error && <p role="alert" className="rounded-lg border border-stop/30 bg-stop/10 px-3 py-2 text-12 text-stop">{error}</p>}<button type="submit" disabled={!email.trim() || !password || submitting} className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500 px-4 py-3 text-13 font-semibold text-white hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-50">{submitting && <Loader2 className="animate-spin" size={14} />} Sign in</button></form><p className="mt-3 text-center text-10 text-dtxt3">Use the credentials configured for this local demo.</p></section></main>
}

export default function AdminPortal() {
  const navigate = useNavigate()
  const [admin, setAdmin] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(ADMIN_SESSION_KEY) || 'null')
      return saved?.access_token ? saved : null
    } catch { return null }
  })
  const [inbox, setInbox] = useState([])
  const [active, setActive] = useState(null)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const endRef = useRef(null)
  const activeIdRef = useRef(null)
  const authHeaders = admin?.access_token ? { Authorization: `Bearer ${admin.access_token}` } : {}

  useEffect(() => { activeIdRef.current = active?.id || null }, [active?.id])

  const loadInbox = useCallback(async () => {
    const data = await api('/admin/conversations', { headers: authHeaders })
    setInbox(data)
    return data
  }, [authHeaders.Authorization])

  const loadConversation = useCallback(async (id) => {
    const conversation = await api(`/conversations/${encodeURIComponent(id)}`, { headers: authHeaders })
    setActive(conversation)
    return conversation
  }, [authHeaders.Authorization])

  const refresh = useCallback(async (includeActive = true) => {
    try {
      const data = await loadInbox()
      if (includeActive && activeIdRef.current) await loadConversation(activeIdRef.current)
      return data
    } catch (err) { setError(err.message); return [] }
  }, [loadConversation, loadInbox])

  useEffect(() => {
    let cancelled = false
    if (!admin) { setLoading(false); return undefined }
    async function initialise() {
      try {
        const data = await api('/admin/conversations', { headers: authHeaders })
        if (cancelled) return
        setInbox(data)
        if (data[0]) await loadConversation(data[0].id)
      } catch (err) { if (!cancelled) setError(`Unable to load the support workspace: ${err.message}`) }
      finally { if (!cancelled) setLoading(false) }
    }
    initialise()
    const poll = window.setInterval(() => refresh(true), 10000)
    return () => { cancelled = true; window.clearInterval(poll) }
  }, [admin?.access_token, loadConversation, refresh])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [active?.messages?.length])

  const filtered = useMemo(() => inbox.filter(item => {
    if (filter === 'attention') return item.status === 'escalated' || (item.has_escalation && item.status !== 'resolved')
    if (filter === 'open') return item.status === 'open'
    if (filter === 'resolved') return item.status === 'resolved'
    return true
  }), [filter, inbox])

  async function selectConversation(id) { setError(''); try { await loadConversation(id) } catch (err) { setError(err.message) } }

  async function sendAdminMessage(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || !active || sending) return
    setSending(true); setError('')
    try {
      await api(`/conversations/${encodeURIComponent(active.id)}/admin-messages`, { method: 'POST', headers: authHeaders, body: JSON.stringify({ content }) })
      setDraft(''); await refresh(true)
    } catch (err) { setError(`Reply could not be sent: ${err.message}`) } finally { setSending(false) }
  }

  async function setStatus(status) {
    if (!active) return
    try { await api(`/conversations/${encodeURIComponent(active.id)}/status`, { method: 'PATCH', headers: authHeaders, body: JSON.stringify({ status }) }); await refresh(true) }
    catch (err) { setError(`Status could not be updated: ${err.message}`) }
  }

  function logout() {
    if (admin?.access_token) void api('/auth/logout', { method: 'POST', headers: authHeaders }).catch(() => {})
    window.localStorage.removeItem(ADMIN_SESSION_KEY)
    setAdmin(null); setInbox([]); setActive(null); setError(''); setDraft(''); setLoading(false)
    navigate('/')
  }

  if (!admin) return <AdminLogin onLogin={setAdmin} />

  return <div className="flex min-h-screen flex-col overflow-x-hidden bg-dark text-dtxt lg:h-screen lg:min-w-[920px] lg:flex-row lg:overflow-hidden">
    <aside className="flex w-full shrink-0 flex-col border-b border-dline bg-[#0d0d10] lg:w-64 lg:border-b-0 lg:border-r"><div className="border-b border-dline px-5 py-5"><div className="flex items-center gap-2"><div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-500"><ShieldCheck size={15} /></div><div><p className="text-14 font-bold">SpotifyAgent</p><p className="text-10 uppercase tracking-widest text-dtxt3">Admin support</p></div></div></div><div className="flex-1 px-3 py-4"><p className="mb-2 px-2 text-10 font-semibold uppercase tracking-widest text-dtxt3">Workspace</p><div className="rounded-md border border-accent-500/20 bg-accent-500/10 px-3 py-2 text-12 font-semibold text-accent-400">Support inbox</div></div><div className="border-t border-dline p-4"><div className="flex items-center gap-2"><div className="flex h-7 w-7 items-center justify-center rounded-full bg-dark3"><UserRound size={13} className="text-dtxt2" /></div><div className="min-w-0"><p className="truncate text-11 font-semibold">{admin?.name || 'Loading…'}</p><p className="text-10 text-dtxt3">Admin · local demo</p></div></div><button onClick={logout} className="mt-4 flex items-center gap-1.5 text-11 text-dtxt3 hover:text-dtxt"><ArrowLeft size={12} /> Log out to role selection</button></div></aside>
    <section className="flex max-h-[360px] w-full shrink-0 flex-col border-b border-dline bg-dark2 lg:max-h-none lg:w-80 lg:border-b-0 lg:border-r"><div className="border-b border-dline px-4 py-4"><div className="flex items-center justify-between"><div><h1 className="text-15 font-bold">Support inbox</h1><p className="mt-0.5 text-11 text-dtxt3">Real customer conversations</p></div><button onClick={() => refresh(true)} aria-label="Refresh inbox" className="rounded-md p-2 text-dtxt3 transition hover:bg-white/[0.06] hover:text-dtxt"><RefreshCw size={14} /></button></div><div className="mt-4 flex gap-1 overflow-x-auto">{[['all', 'All'], ['attention', 'Needs attention'], ['open', 'Open'], ['resolved', 'Resolved']].map(([value, label]) => <button key={value} onClick={() => setFilter(value)} className={cn('whitespace-nowrap rounded-md px-2 py-1.5 text-10 font-semibold transition', filter === value ? 'bg-white/[0.1] text-dtxt' : 'text-dtxt3 hover:text-dtxt')}>{label}</button>)}</div></div><div className="flex-1 overflow-y-auto dark-scroll">{loading ? <div className="flex justify-center py-8 text-dtxt3"><Loader2 className="animate-spin" size={18} /></div> : filtered.length ? filtered.map(item => <InboxRow key={item.id} item={item} selected={active?.id === item.id} onClick={() => selectConversation(item.id)} />) : <EmptyInbox />}</div></section>
    <main className="flex min-h-[520px] min-w-0 flex-1 flex-col bg-dark lg:min-h-0">{error && <div role="alert" className="m-4 rounded-lg border border-stop/30 bg-stop/10 px-3 py-2 text-12 text-stop">{error}</div>}{!active && !loading ? <EmptyInbox /> : active && <><header className="flex items-center justify-between border-b border-dline px-6 py-4"><div><div className="flex items-center gap-2"><h2 className="text-15 font-bold">{inbox.find(item => item.id === active.id)?.customer_name || 'Customer'}</h2><StatusBadge status={active.status} escalation={active.status === 'escalated'} /></div><p className="mt-0.5 text-11 text-dtxt3">{inbox.find(item => item.id === active.id)?.customer_email || active.user_id} · {active.id}</p></div><div className="flex gap-2">{active.status === 'resolved' ? <button onClick={() => setStatus('open')} className="rounded-lg border border-dline px-3 py-2 text-11 font-semibold text-dtxt2 hover:bg-white/[0.06]">Reopen</button> : <button onClick={() => setStatus('resolved')} className="rounded-lg bg-go px-3 py-2 text-11 font-semibold text-white hover:bg-green-700">Resolve</button>}</div></header>{active.status === 'escalated' && <div className="flex items-center gap-2 border-b border-stop/25 bg-stop/10 px-6 py-2.5 text-12 font-semibold text-stop"><AlertTriangle size={14} /> Human attention required — this conversation was escalated by the AI.</div>}<div className="flex-1 overflow-y-auto dark-scroll px-6 py-6"><div className="mx-auto max-w-3xl space-y-5">{active.messages.map(message => <div key={message.id} className={cn('flex gap-3', message.sender === 'customer' ? 'justify-start' : 'justify-end')}><div className={cn('flex max-w-[82%] gap-2.5', message.sender !== 'customer' && 'flex-row-reverse')}><div className={cn('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full', message.sender === 'customer' ? 'bg-dark3 text-dtxt2' : message.sender === 'admin' ? 'bg-violet-500/20 text-violet-300' : 'bg-accent-500/20 text-accent-400')}>{message.sender === 'customer' ? <UserRound size={13} /> : message.sender === 'admin' ? <ShieldCheck size={13} /> : <Bot size={14} />}</div><div><div className={cn('rounded-xl px-4 py-3 text-13 leading-relaxed', message.sender === 'customer' ? 'rounded-tl-sm border border-dline bg-dark3 text-dtxt' : message.sender === 'admin' ? 'rounded-tr-sm bg-violet-600 text-white' : 'rounded-tr-sm border border-accent-500/25 bg-accent-500/10 text-dtxt')}>{message.content}</div><p className={cn('mt-1 text-10 text-dtxt3', message.sender !== 'customer' && 'text-right')}>{message.sender === 'customer' ? 'Customer' : message.sender === 'admin' ? 'You · Admin' : 'SpotifyAgent'} · {formatTime(message.created_at)}</p>{message.decision && <DecisionPanel decision={message.decision} />}</div></div></div>)}<div ref={endRef} /></div></div>{active.status !== 'resolved' ? <form onSubmit={sendAdminMessage} className="border-t border-dline bg-dark2 p-4"><div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-dline bg-dark3 p-2 focus-within:border-accent-500/50"><textarea value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} rows={2} placeholder="Write a human support reply…" disabled={sending} className="min-h-[44px] flex-1 resize-none bg-transparent px-2 py-1 text-13 text-dtxt outline-none placeholder:text-dtxt3" /><button type="submit" disabled={!draft.trim() || sending} className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500 text-white hover:bg-accent-600 disabled:opacity-40">{sending ? <Loader2 className="animate-spin" size={15} /> : <Send size={15} />}</button></div><p className="mx-auto mt-2 flex max-w-3xl items-center gap-1.5 text-10 text-dtxt3"><Clock3 size={11} /> Human replies are saved directly and do not run the AI pipeline.</p></form> : <div className="border-t border-dline bg-dark2 p-4 text-center text-11 text-dtxt3"><CheckCircle2 className="mr-1 inline text-go" size={13} /> Resolved. Reopen this conversation to send another reply.</div>}</>}</main>
  </div>
}
