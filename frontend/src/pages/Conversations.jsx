import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronRight } from 'lucide-react'
import { IntentBadge, DecisionBadge } from '../components/ui'
import { cn } from '../lib/utils'

const ROWS = [
  { id:'g0001', name:'Alex M.',  msg:'Spotify keeps stopping on my Android phone.',       intent:'playback_error',       d:'AUTO_HANDLE', conf:0.97, plat:'android', t:'Dec 3' },
  { id:'g0012', name:'Priya S.', msg:'I was charged twice for premium this month.',       intent:'billing_charge',        d:'ESCALATE',    conf:0.95, plat:'—',       t:'Dec 3' },
  { id:'g0023', name:'Omar K.',  msg:'My liked songs playlist disappeared after update.', intent:'playlist_library',      d:'AUTO_HANDLE', conf:0.96, plat:'—',       t:'Dec 2' },
  { id:'g0034', name:'Sana R.',  msg:"Can't log in, password reset email doesn't arrive.",intent:'account_login',         d:'AUTO_HANDLE', conf:0.97, plat:'—',       t:'Dec 2' },
  { id:'g0045', name:'Yuki T.',  msg:'Album not available in my country.',                intent:'content_unavailable',   d:'AUTO_HANDLE', conf:0.88, plat:'—',       t:'Dec 1' },
  { id:'g0056', name:'Arjun P.', msg:'Spotify crashes on startup on my iPhone.',          intent:'app_crash_bug',         d:'AUTO_HANDLE', conf:0.84, plat:'ios',     t:'Nov 30'},
  { id:'g0067', name:'Dana L.',  msg:'Downloaded songs not available in offline mode.',   intent:'offline_download',      d:'AUTO_HANDLE', conf:0.93, plat:'—',       t:'Nov 30'},
  { id:'g0078', name:'Nia F.',   msg:"Alexa won't play my Spotify playlist.",             intent:'device_platform',       d:'AUTO_HANDLE', conf:0.91, plat:'alexa',   t:'Nov 29'},
  { id:'g0089', name:'Leo B.',   msg:'Subscription showing as free after paying.',        intent:'premium_subscription',  d:'AUTO_HANDLE', conf:0.94, plat:'—',       t:'Nov 29'},
  { id:'g0090', name:'Mia C.',   msg:'Songs keep buffering on mobile data.',              intent:'playback_error',        d:'AUTO_HANDLE', conf:0.91, plat:'android', t:'Nov 28'},
]

export default function Conversations() {
  const [q, setQ]   = useState('')
  const [sel, setSel] = useState(null)

  const rows = ROWS.filter(r =>
    !q || r.name.toLowerCase().includes(q.toLowerCase()) ||
          r.msg.toLowerCase().includes(q.toLowerCase())
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="min-h-screen bg-dark p-5 max-w-7xl mx-auto"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-20 font-bold text-dtxt tracking-tight mb-0.5">Conversations</h1>
          <p className="text-12 text-dtxt3">200 evaluated golden-set examples · demo data</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dline
                        bg-dark2 w-56">
          <Search size={13} className="text-dtxt3 flex-shrink-0" />
          <input
            value={q} onChange={e => setQ(e.target.value)}
            placeholder="Search…"
            className="text-13 bg-transparent outline-none flex-1 text-dtxt placeholder-dtxt3"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-dark2 border border-dline rounded-xl overflow-hidden shadow-dark-card">
        {/* Header row */}
        <div className="grid grid-cols-[28px_2fr_1fr_80px_100px_64px_28px]
                        gap-3 px-5 py-3 border-b border-dline
                        text-10 text-dtxt3 font-semibold uppercase tracking-widest">
          <span />
          <span>Customer</span>
          <span>Intent</span>
          <span className="text-right">Conf.</span>
          <span>Decision</span>
          <span className="text-right">Date</span>
          <span />
        </div>

        <div className="divide-y divide-dline">
          {rows.map((row, i) => (
            <>
              <motion.div
                key={row.id}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => setSel(sel === row.id ? null : row.id)}
                className={cn(
                  'grid grid-cols-[28px_2fr_1fr_80px_100px_64px_28px]',
                  'gap-3 px-5 py-3.5 items-center cursor-pointer transition-colors',
                  sel === row.id ? 'bg-accent-500/5' : 'hover:bg-white/[0.02]',
                )}
              >
                <div className={cn('w-6 h-6 rounded-full flex items-center justify-center',
                  'text-11 font-bold flex-shrink-0',
                  'bg-dark3 border border-dline text-dtxt2')}>
                  {row.name[0]}
                </div>
                <div className="min-w-0">
                  <p className="text-13 font-semibold text-dtxt">{row.name}</p>
                  <p className="text-12 text-dtxt3 truncate">{row.msg}</p>
                </div>
                <IntentBadge intent={row.intent} dark />
                <div className="text-right">
                  <span className={cn('text-12 font-bold tabular-nums',
                    row.conf >= 0.85 ? 'text-go' : row.conf >= 0.65 ? 'text-hold' : 'text-stop')}>
                    {Math.round(row.conf * 100)}%
                  </span>
                </div>
                <DecisionBadge decision={row.d} dark />
                <span className="text-11 text-dtxt3 text-right">{row.t}</span>
                <ChevronRight size={12} className={cn('text-dtxt3 transition-transform',
                  sel === row.id && 'rotate-90')} />
              </motion.div>

              <AnimatePresence>
                {sel === row.id && (
                  <motion.div
                    key={row.id + '-exp'}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden border-t border-dline bg-dark3"
                  >
                    <div className="px-14 py-4 grid grid-cols-3 gap-6">
                      <div>
                        <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Full message</p>
                        <p className="text-13 text-dtxt2 leading-relaxed">{row.msg}</p>
                      </div>
                      <div>
                        <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Platform</p>
                        <p className="text-13 text-dtxt2 capitalize">{row.plat}</p>
                      </div>
                      <div>
                        <p className="text-10 text-dtxt3 uppercase tracking-widest mb-1.5">Conversation ID</p>
                        <p className="text-13 text-dtxt2 font-mono">{row.id}</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          ))}
        </div>

        <div className="px-5 py-3 border-t border-dline flex justify-between items-center">
          <p className="text-11 text-dtxt3">Showing {rows.length} of {ROWS.length} examples</p>
          <p className="text-11 text-dtxt3">Connect backend for all 200 results</p>
        </div>
      </div>
    </motion.div>
  )
}
