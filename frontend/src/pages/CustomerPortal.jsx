import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowLeft, Bot, CheckCircle2, CircleHelp, Clock3, Loader2,
  MessageCircleMore, Plus, Send, ShieldCheck, Sparkles, UserRound,
} from 'lucide-react'
import { cn } from '../lib/utils'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const CUSTOMER_SESSION_KEY = 'spotifyagent.customer-session'

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
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function conversationTitle(conversation) {
  const firstCustomerMessage = conversation.messages?.find(message => message.sender === 'customer')
  return firstCustomerMessage?.content || conversation.last_message || 'New support request'
}

function statusLabel(status) {
  if (status === 'resolved') return 'Resolved'
  if (status === 'escalated') return 'Human attention required'
  return 'Open'
}

function StatusBadge({ status }) {
  const styles = status === 'resolved'
    ? 'bg-stone-100 text-ink3'
    : status === 'escalated'
      ? 'bg-red-100 text-stop-text'
      : 'bg-green-100 text-go-text'
  return <span className={cn('rounded-full px-2 py-0.5 text-10 font-semibold', styles)}>{statusLabel(status)}</span>
}

function ConversationRow({ conversation, selected, onClick }) {
  const isOpen = conversation.status === 'open'
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border p-3.5 text-left transition focus:outline-none focus:ring-2 focus:ring-green-500/30',
        selected ? 'border-green-500 bg-green-50 shadow-card' : 'border-rule bg-white hover:border-rule-2 hover:shadow-card',
      )}
    >
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <span className={cn('flex items-center gap-1.5 text-11 font-semibold', isOpen ? 'text-go-text' : 'text-ink3')}>
          <span className={cn('h-1.5 w-1.5 rounded-full', isOpen ? 'bg-go' : 'bg-ink3')} />
          {statusLabel(conversation.status)}
        </span>
        <span className="shrink-0 text-11 text-ink3">{formatTime(conversation.last_message_at || conversation.updated_at)}</span>
      </div>
      <p className="truncate text-13 font-semibold text-ink">{conversationTitle(conversation)}</p>
      <p className="mt-1 truncate text-12 text-ink3">{conversation.last_message || 'Tell us how we can help.'}</p>
    </button>
  )
}

function CustomerLogin({ onContinue }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    const cleanName = name.trim()
    const cleanEmail = email.trim()
    if (!cleanName || !cleanEmail || submitting) return
    setSubmitting(true); setError('')
    try {
      const suffix = globalThis.crypto?.randomUUID?.().replaceAll('-', '') || `${Date.now()}${Math.random().toString(16).slice(2)}`
      const user = await api('/users', { method: 'POST', body: JSON.stringify({ id: `portal_${suffix}`, name: cleanName, email: cleanEmail, role: 'customer' }) })
      window.localStorage.setItem(CUSTOMER_SESSION_KEY, JSON.stringify(user))
      onContinue(user)
    } catch (err) { setError(`Unable to start your support session: ${err.message}`) } finally { setSubmitting(false) }
  }

  return <div className="min-h-screen bg-canvas px-5 py-12"><div className="mx-auto max-w-md rounded-2xl border border-rule bg-white p-7 shadow-lift"><div className="mb-6 flex items-center gap-2"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-green-600 text-white"><Sparkles size={17} /></div><div><p className="text-17 font-bold tracking-tight">Spotify Support</p><p className="text-11 text-ink3">Start your private support session</p></div></div><form onSubmit={submit} className="space-y-4"><div><label htmlFor="customer-name" className="mb-1.5 block text-12 font-semibold text-ink">Your name</label><input id="customer-name" value={name} onChange={event => setName(event.target.value)} autoComplete="name" required className="w-full rounded-lg border border-rule px-3 py-2.5 text-14 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-600/15" placeholder="Jane Doe" /></div><div><label htmlFor="customer-email" className="mb-1.5 block text-12 font-semibold text-ink">Email address</label><input id="customer-email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" type="email" required className="w-full rounded-lg border border-rule px-3 py-2.5 text-14 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-600/15" placeholder="jane@example.com" /></div>{error && <p role="alert" className="rounded-lg bg-stop-bg px-3 py-2 text-12 text-stop-text">{error}</p>}<button type="submit" disabled={!name.trim() || !email.trim() || submitting} className="flex w-full items-center justify-center gap-2 rounded-lg bg-go px-4 py-3 text-13 font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50">{submitting && <Loader2 className="animate-spin" size={14} />} Continue to support</button></form></div></div>
}

function EmptyState({ onNew }) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center px-6 py-12 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-green-100 text-go">
        <MessageCircleMore size={22} />
      </div>
      <h2 className="text-20 font-bold tracking-tight text-ink">How can we help?</h2>
      <p className="mt-2 text-14 leading-relaxed text-ink3">Start a conversation and the Spotify support assistant will help you find a resolution.</p>
      <button onClick={onNew} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-go px-4 py-2.5 text-13 font-semibold text-white transition hover:bg-green-700">
        <Plus size={15} /> New support request
      </button>
    </div>
  )
}

export default function CustomerPortal() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(window.localStorage.getItem(CUSTOMER_SESSION_KEY) || 'null') } catch { return null }
  })
  const [conversations, setConversations] = useState([])
  const [active, setActive] = useState(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const messagesEndRef = useRef(null)

  const refreshConversations = useCallback(async () => {
    if (!user) return []
    const list = await api(`/users/${encodeURIComponent(user.id)}/conversations`)
    setConversations(list)
    return list
  }, [user])

  const selectConversation = useCallback(async (conversationId) => {
    setError('')
    try {
      const conversation = await api(`/conversations/${encodeURIComponent(conversationId)}`)
      setActive(conversation)
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    if (!user) { setLoading(false); return undefined }
    async function initialise() {
      try {
        let loadedUser
        try {
          loadedUser = await api(`/users/${encodeURIComponent(user.id)}`)
        } catch (err) {
          if (!err.message.includes('not found')) throw err
          loadedUser = await api('/users', { method: 'POST', body: JSON.stringify(user) })
        }
        const list = await api(`/users/${encodeURIComponent(user.id)}/conversations`)
        if (cancelled) return
        setUser(current => current?.id === loadedUser.id ? current : loadedUser)
        setConversations(list)
        if (list[0]) await selectConversation(list[0].id)
      } catch (err) {
        if (!cancelled) setError(`Unable to load your support conversations: ${err.message}`)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    initialise()
    return () => { cancelled = true }
  }, [selectConversation, user?.id])

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [active?.messages?.length])

  async function startConversation() {
    setError('')
    try {
      const conversation = await api('/conversations', {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, status: 'open' }),
      })
      setConversations(current => [conversation, ...current])
      setActive({ ...conversation, messages: [], agent_decisions: [] })
      setDraft('')
    } catch (err) {
      setError(`Unable to start a support request: ${err.message}`)
    }
  }

  function switchCustomer() {
    window.localStorage.removeItem(CUSTOMER_SESSION_KEY)
    setUser(null); setConversations([]); setActive(null); setError(''); setDraft('')
  }

  if (!user) return <CustomerLogin onContinue={setUser} />

  async function sendMessage(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || !active || sending) return
    setSending(true)
    setError('')
    try {
      await api(`/conversations/${encodeURIComponent(active.id)}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content, sender: 'customer' }),
      })
      setDraft('')
      const [conversation, list] = await Promise.all([
        api(`/conversations/${encodeURIComponent(active.id)}`),
        refreshConversations(),
      ])
      setActive(conversation)
      setConversations(list)
    } catch (err) {
      setError(`Your message wasn't sent: ${err.message}`)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-rule bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2 text-13 font-semibold text-ink3 transition hover:text-ink">
            <ArrowLeft size={15} /> Support home
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-600 text-white"><Sparkles size={15} /></div>
            <span className="text-14 font-bold tracking-tight text-ink">Spotify Support</span>
          </div>
            <div className="flex items-center gap-2 text-right">
              <div className="hidden sm:block"><p className="text-12 font-semibold text-ink">{user?.name || 'Loading…'}</p><p className="text-10 text-ink3">Customer portal</p></div>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-11 font-bold text-white">{(user?.name || 'S').charAt(0).toUpperCase()}</div>
            </div>
        </div>
      </header>

      <main className="mx-auto grid min-h-[calc(100vh-64px)] max-w-6xl grid-cols-1 bg-white shadow-card lg:grid-cols-[292px_1fr]">
        <aside className="border-b border-rule bg-[#fbfbfa] p-4 lg:border-b-0 lg:border-r">
          <div className="mb-4 flex items-center justify-between"><div><h1 className="text-17 font-bold tracking-tight">Your conversations</h1><button onClick={switchCustomer} className="mt-0.5 text-11 text-ink3 underline-offset-2 hover:text-ink hover:underline">Use a different customer</button></div><button onClick={startConversation} aria-label="New support request" className="rounded-lg bg-go p-2 text-white transition hover:bg-green-700"><Plus size={16} /></button></div>
          <div className="flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-2 lg:overflow-visible">
            {loading ? <p className="p-3 text-12 text-ink3">Loading conversations…</p> : conversations.length ? conversations.map(conversation => <div className="min-w-[230px] lg:min-w-0" key={conversation.id}><ConversationRow conversation={conversation} selected={active?.id === conversation.id} onClick={() => selectConversation(conversation.id)} /></div>) : <p className="p-3 text-12 text-ink3">No conversations yet.</p>}
          </div>
        </aside>

        <section className="flex min-h-[620px] flex-col">
          {error && <div role="alert" className="m-4 rounded-lg border border-red-200 bg-stop-bg px-3 py-2 text-12 text-stop-text">{error}</div>}
          {loading ? <div className="flex flex-1 items-center justify-center text-ink3"><Loader2 className="mr-2 animate-spin" size={18} /> Loading your support history</div> : !active ? <EmptyState onNew={startConversation} /> : <>
            <div className="flex items-center justify-between border-b border-rule px-5 py-4"><div><div className="flex items-center gap-2"><h2 className="text-15 font-bold">Support request</h2><StatusBadge status={active.status} /></div><p className="mt-0.5 text-11 text-ink3">We’ll keep this conversation here for you.</p></div><CircleHelp size={18} className="text-ink3" /></div>
            <div className="flex-1 space-y-5 overflow-y-auto bg-[#fcfcfb] px-5 py-6">
              {active.messages.length === 0 ? <div className="mx-auto max-w-sm pt-12 text-center"><Bot className="mx-auto mb-3 text-go" size={28} /><p className="text-15 font-semibold">Tell us what’s happening</p><p className="mt-1 text-12 leading-relaxed text-ink3">Add as much detail as you can, such as your device, what you expected, and what happened.</p></div> : active.messages.map(message => <div key={message.id} className={cn('flex gap-2.5', message.sender === 'customer' ? 'justify-end' : 'justify-start')}><div className={cn('flex max-w-[82%] gap-2.5', message.sender === 'customer' && 'flex-row-reverse')}><div className={cn('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full', message.sender === 'customer' ? 'bg-ink text-white' : message.sender === 'admin' ? 'bg-violet-100 text-violet-700' : 'bg-green-100 text-go')} >{message.sender === 'customer' ? <UserRound size={13} /> : message.sender === 'admin' ? <ShieldCheck size={14} /> : <Bot size={14} />}</div><div><div className={cn('rounded-2xl px-4 py-3 text-14 leading-relaxed', message.sender === 'customer' ? 'rounded-tr-sm bg-ink text-white' : message.sender === 'admin' ? 'rounded-tl-sm border border-violet-200 bg-violet-50 text-violet-950 shadow-card' : 'rounded-tl-sm border border-rule bg-white text-ink shadow-card')}>{message.content}</div><p className={cn('mt-1 text-10 text-ink3', message.sender === 'customer' && 'text-right')}>{message.sender === 'customer' ? 'You' : message.sender === 'admin' ? 'Spotify Support specialist' : 'Spotify Support AI'} · {formatTime(message.created_at)}</p></div></div></div>)}
              <div ref={messagesEndRef} />
            </div>
            {active.status !== 'resolved' ? <form onSubmit={sendMessage} className="border-t border-rule bg-white p-4"><label htmlFor="support-message" className="sr-only">Message to Spotify Support</label><div className="flex items-end gap-2 rounded-xl border border-rule bg-white p-2 focus-within:border-green-500 focus-within:ring-2 focus-within:ring-green-500/15"><textarea id="support-message" value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} rows={2} placeholder="Describe your issue…" className="min-h-[44px] flex-1 resize-none bg-transparent px-2 py-1 text-14 outline-none placeholder:text-ink3" disabled={sending} /><button type="submit" disabled={!draft.trim() || sending} className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-go text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-40">{sending ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}</button></div><p className="mt-2 flex items-center gap-1.5 text-10 text-ink3"><Clock3 size={11} /> The assistant usually replies immediately. Complex or sensitive issues are routed to a specialist.</p></form> : <div className="border-t border-rule bg-white p-4 text-center text-12 text-ink3"><CheckCircle2 className="mr-1 inline text-go" size={14} /> This request is resolved. Start a new conversation if you need more help.</div>}
          </>}
        </section>
      </main>
    </div>
  )
}
