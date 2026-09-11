import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Loader2, Copy, Check, CheckCircle2, AlertTriangle, Sparkles, User } from 'lucide-react'
import { cn } from '../lib/utils'
import { IntentBadge, DecisionBadge, ConfBar } from '../components/ui'

/* ── demo conversations ──────────────────────────────────────── */
const INBOX = [
  { id:'c01', name:'Alex M.',  time:'2m ago', preview:'Spotify keeps stopping on my Android…',
    intent:'playback_error', d:'AUTO_HANDLE', conf:0.97, platform:'android', unread:true,
    msg:'Spotify keeps stopping whenever I try to play music on my Android phone.',
    result:{
      intent:'playback_error', conf:0.97, platform:'android', risk:[],
      evidence:[
        {q:'Spotify keeps stopping on my Android every 30 seconds',a:'Could you confirm your Android version and Spotify version? Does this happen on both WiFi and 4G? /SC',sim:0.82,platform:'android',match:true},
        {q:'App keeps pausing randomly on Android',a:'Try clearing the Spotify cache: Settings → Apps → Spotify → Clear Cache, then restart. /SC',sim:0.71,platform:'android',match:true},
      ],
      reply:"Hi Alex! Could you confirm your Android version and Spotify version? It'd also help to know if this happens on both WiFi and mobile data. /SC",
      decision:'AUTO_HANDLE',
      reason:'Low-risk troubleshooting request. Strong platform-matched historical evidence.',
    },
  },
  { id:'c02', name:'Priya S.', time:'8m ago', preview:'Charged twice for premium this month…',
    intent:'billing_charge', d:'ESCALATE', conf:0.95, platform:'unknown', unread:true,
    msg:'I was charged twice for premium this month. This is unacceptable — I need a refund.',
    result:{
      intent:'billing_charge', conf:0.95, platform:'unknown', risk:['billing_dispute'],
      evidence:[
        {q:'Charged twice for premium subscription',a:"Hi! Can you DM us your account email? We'll look into the billing straight away. /SC",sim:0.74,platform:'unknown',match:false},
      ],
      reply:'We understand this is urgent. Please DM us your account details and a billing specialist will assist you immediately. /SC',
      decision:'ESCALATE',
      reason:'Billing dispute signal detected. Requires human specialist for account verification.',
    },
  },
  { id:'c03', name:'Omar K.',  time:'15m ago', preview:'Liked songs playlist disappeared…',
    intent:'playlist_library', d:'AUTO_HANDLE', conf:0.96, platform:'unknown', unread:false,
    msg:'My entire liked songs playlist just disappeared after the update.',
    result:{
      intent:'playlist_library', conf:0.96, platform:'unknown', risk:[],
      evidence:[
        {q:'All my liked songs disappeared after updating',a:'Hey! Try logging out and back in — that usually resyncs your library. /SC',sim:0.79,platform:'unknown',match:false},
      ],
      reply:"Hi Omar! Try logging out of Spotify and back in — this usually resyncs your library. If Liked Songs are still missing, please DM us your account email. /SC",
      decision:'AUTO_HANDLE',
      reason:'Clear playlist-recovery intent with matching historical resolution.',
    },
  },
  { id:'c04', name:'Sana R.',  time:'22m ago', preview:"Can't log in after password reset…",
    intent:'account_login', d:'AUTO_HANDLE', conf:0.97, platform:'unknown', unread:false,
    msg:"Can't log into my account. I tried resetting my password but the email never arrives.",
    result:{
      intent:'account_login', conf:0.97, platform:'unknown', risk:[],
      evidence:[
        {q:'Password reset email not arriving',a:"Check your spam folder! If it's not there, try in a different browser. DM us if still stuck. /SC",sim:0.81,platform:'unknown',match:false},
      ],
      reply:"Hi Sana! First check your spam/junk folder for the reset email. If it's not there, try requesting it in a different browser. Still stuck? DM us your account email. /SC",
      decision:'AUTO_HANDLE',
      reason:'Standard login recovery with strong matching historical resolution.',
    },
  },
]

/* ── copy button ─────────────────────────────────────────────── */
function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="flex items-center gap-1.5 text-11 text-dtxt3 hover:text-dtxt
                 transition-colors px-2 py-1 rounded hover:bg-white/[0.06]"
    >
      {copied ? <Check size={11} className="text-go" /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

/* ── pipeline step ───────────────────────────────────────────── */
function PipelineStep({ num, title, active, done, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className={cn(
          'w-5 h-5 rounded-full flex items-center justify-center text-10 font-bold flex-shrink-0 transition-colors',
          done   ? 'bg-go text-white' :
          active ? 'bg-accent-500 text-white animate-pulse-ring' :
                   'bg-dline text-dtxt3',
        )}>
          {done ? <Check size={10} strokeWidth={3} /> : num}
        </div>
        <p className={cn('text-11 font-semibold uppercase tracking-widest transition-colors',
          active || done ? 'text-dtxt' : 'text-dtxt3')}>{title}</p>
      </div>
      {children && <div className="ml-7">{children}</div>}
    </motion.div>
  )
}

/* ── inbox row ───────────────────────────────────────────────── */
function InboxRow({ conv, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-4 py-3 border-b border-dline transition-colors relative',
        active ? 'bg-accent-500/10' : 'hover:bg-white/[0.03]',
      )}
    >
      {active && (
        <motion.div
          layoutId="inbox-active"
          className="absolute left-0 inset-y-0 w-0.5 bg-accent-400"
          transition={{ type: 'spring', stiffness: 600, damping: 40 }}
        />
      )}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          {conv.unread && <span className="w-1.5 h-1.5 rounded-full bg-accent-400 flex-shrink-0" />}
          <p className={cn('text-13', conv.unread ? 'font-semibold text-dtxt' : 'font-medium text-dtxt2')}>
            {conv.name}
          </p>
        </div>
        <span className="text-11 text-dtxt3">{conv.time}</span>
      </div>
      <p className="text-12 text-dtxt3 truncate mb-2">{conv.preview}</p>
      <div className="flex gap-1.5">
        <IntentBadge intent={conv.intent} dark />
        <DecisionBadge decision={conv.d} dark />
      </div>
    </button>
  )
}

/* ── main ────────────────────────────────────────────────────── */
export default function Agent() {
  const [sel, setSel] = useState(INBOX[0])

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="flex h-screen bg-dark"
    >
      {/* COL 1 — inbox */}
      <div className="w-64 flex-shrink-0 flex flex-col border-r border-dline">
        <div className="px-4 py-4 border-b border-dline">
          <p className="text-14 font-bold text-dtxt">AI Agent</p>
          <p className="text-11 text-dtxt3 mt-0.5">
            {INBOX.filter(c => c.unread).length} pending · {INBOX.length} total
          </p>
        </div>
        <div className="flex-1 overflow-y-auto dark-scroll">
          {INBOX.map(c => (
            <InboxRow key={c.id} conv={c} active={sel.id === c.id} onClick={() => setSel(c)} />
          ))}
        </div>
        <div className="px-4 py-2.5 border-t border-dline">
          <p className="text-11 text-dtxt3">Demo — connect backend for live inbox</p>
        </div>
      </div>

      {/* COL 2 — conversation */}
      <div className="flex-1 min-w-0 flex flex-col border-r border-dline">
        <AnimatePresence mode="wait">
          <motion.div
            key={sel.id}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="flex-1 flex flex-col h-full"
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-dline flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-dark3 border border-dline
                              flex items-center justify-center flex-shrink-0">
                <User size={14} className="text-dtxt3" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-14 font-semibold text-dtxt">{sel.name}</p>
                <p className="text-11 text-dtxt3">Customer · Spotify · {sel.time}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 text-11 text-go">
                  <span className="w-1.5 h-1.5 rounded-full bg-go" />
                  Active
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto dark-scroll px-5 py-5 space-y-4">
              {/* Customer message */}
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-full bg-dark3 border border-dline
                                flex items-center justify-center text-11 font-bold text-dtxt3 flex-shrink-0 mt-0.5">
                  {sel.name[0]}
                </div>
                <div className="max-w-[80%]">
                  <div className="bg-dark3 border border-dline rounded-xl px-4 py-3
                                  text-14 text-dtxt leading-relaxed shadow-dark-card">
                    {sel.msg}
                  </div>
                  <div className="flex items-center gap-3 mt-2 px-1">
                    <IntentBadge intent={sel.intent} dark />
                    {sel.platform !== 'unknown' && (
                      <span className="text-11 text-dtxt3 capitalize">{sel.platform}</span>
                    )}
                    <span className="text-11 text-dtxt3">Incoming</span>
                  </div>
                </div>
              </div>

              {/* AI suggested reply */}
              <div className="flex gap-3 items-start flex-row-reverse">
                <div className="w-7 h-7 rounded-lg bg-accent-500/20 border border-accent-500/30
                                flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles size={13} className="text-accent-400" />
                </div>
                <div className="max-w-[80%]">
                  <div className="relative bg-dark2 border border-accent-500/25 rounded-xl
                                  overflow-hidden shadow-dark-card">
                    {/* Top accent line */}
                    <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
                                    from-transparent via-accent-500/50 to-transparent" />
                    <div className="px-4 pt-3 pb-1">
                      <p className="text-10 text-accent-400 font-semibold uppercase tracking-widest mb-2">
                        AI Suggested Response
                      </p>
                      <p className="text-14 text-dtxt leading-relaxed">{sel.result.reply}</p>
                    </div>
                    <div className="flex items-center justify-between px-4 py-2.5 border-t border-dline">
                      <p className="text-11 text-dtxt3">Evidence-grounded · ready to send</p>
                      <CopyBtn text={sel.result.reply} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Compose */}
            <div className="flex-shrink-0 px-5 py-3 border-t border-dline">
              <div className="flex gap-2">
                <input
                  placeholder="Edit the AI reply or write your own…"
                  defaultValue={sel.result.reply}
                  key={sel.id}
                  className="flex-1 text-13 bg-dark3 border border-dline rounded-lg px-3 py-2
                             text-dtxt placeholder-dtxt3 focus:outline-none
                             focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/20
                             transition"
                />
                <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent-500
                                   text-white text-13 font-semibold hover:bg-accent-600 transition">
                  <Send size={13} /> Send
                </button>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* COL 3 — AI Resolution */}
      <div className="w-80 flex-shrink-0 flex flex-col bg-dark2">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-dline flex-shrink-0">
          <Sparkles size={13} className="text-accent-400" />
          <p className="text-13 font-bold text-dtxt">AI Resolution</p>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={sel.id + '-r'}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
            className="flex-1 overflow-y-auto dark-scroll px-5 py-5 space-y-6"
          >
            {/* Step 1 — Understand */}
            <PipelineStep num="1" title="Understand" done active={false} delay={0.05}>
              <div className="space-y-3 bg-dark3 border border-dline rounded-lg p-3.5">
                <div>
                  <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Intent</p>
                  <IntentBadge intent={sel.result.intent} dark />
                </div>
                {sel.result.platform !== 'unknown' && (
                  <div>
                    <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Platform</p>
                    <span className="text-13 font-medium text-dtxt capitalize">{sel.result.platform}</span>
                  </div>
                )}
                <div>
                  <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Confidence</p>
                  <ConfBar value={sel.result.conf} dark />
                </div>
                {sel.result.risk.length > 0 && (
                  <div>
                    <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Risk Signals</p>
                    {sel.result.risk.map(r => (
                      <span key={r} className="inline-block text-10 px-2 py-px rounded
                                               bg-stop/15 text-stop border border-stop/25 font-medium">
                        {r.replace(/_/g,' ')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </PipelineStep>

            {/* Connector */}
            <div className="flex items-center gap-3 -my-2">
              <div className="ml-2 w-px h-6 bg-dline" />
            </div>

            {/* Step 2 — Evidence */}
            <PipelineStep num="2" title="Historical Evidence" done active={false} delay={0.1}>
              <div className="space-y-2.5">
                {sel.result.evidence.map((ev, i) => (
                  <div key={i} className="border border-dline rounded-lg overflow-hidden">
                    <div className="px-3 py-2.5 bg-dark3">
                      <div className="flex items-center justify-between mb-1.5">
                        <p className="text-10 text-dtxt3 uppercase tracking-caps">Match {i + 1}</p>
                        <div className="flex items-center gap-2">
                          {ev.match && (
                            <span className="text-10 text-go font-medium">{ev.platform} ✓</span>
                          )}
                          <span className="text-10 text-dtxt3 tabular-nums">sim {ev.sim.toFixed(2)}</span>
                        </div>
                      </div>
                      <p className="text-12 text-dtxt2 italic leading-relaxed">"{ev.q}"</p>
                    </div>
                    <div className="px-3 py-2.5">
                      <p className="text-10 text-dtxt3 mb-1 uppercase tracking-caps">Historical response</p>
                      <p className="text-12 text-dtxt2 leading-relaxed">{ev.a}</p>
                    </div>
                  </div>
                ))}
              </div>
            </PipelineStep>

            <div className="ml-2 w-px h-6 bg-dline" />

            {/* Step 3 — Generated */}
            <PipelineStep num="3" title="Generated Response" done active={false} delay={0.15}>
              <div className="border border-accent-500/25 rounded-lg bg-accent-500/5 px-3.5 py-3">
                <p className="text-12 text-dtxt2 leading-relaxed">{sel.result.reply}</p>
                <p className="text-10 text-dtxt3 mt-2">Evidence-grounded</p>
              </div>
            </PipelineStep>

            <div className="ml-2 w-px h-6 bg-dline" />

            {/* Step 4 — Decision */}
            <PipelineStep num="4" title="Decision" done active={false} delay={0.2}>
              <div className={cn(
                'rounded-lg border px-4 py-3.5',
                sel.result.decision === 'ESCALATE'
                  ? 'bg-stop/10 border-stop/25'
                  : 'bg-go/10 border-go/25',
              )}>
                <div className="flex items-center gap-2 mb-2">
                  {sel.result.decision === 'ESCALATE'
                    ? <AlertTriangle size={14} className="text-stop" />
                    : <CheckCircle2  size={14} className="text-go"  />}
                  <p className={cn('text-13 font-bold',
                    sel.result.decision === 'ESCALATE' ? 'text-stop' : 'text-go')}>
                    {sel.result.decision === 'ESCALATE' ? 'Human Review Required' : 'Auto-Handle'}
                  </p>
                </div>
                <p className="text-12 text-dtxt2 leading-relaxed">{sel.result.reason}</p>
              </div>
            </PipelineStep>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
