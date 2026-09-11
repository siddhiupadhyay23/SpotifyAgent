import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, ChevronDown, ChevronUp } from 'lucide-react'
import { IntentBadge } from '../components/ui'
import { cn } from '../lib/utils'

const CORPUS = [
  { id:'p001', intent:'playback_error',      plat:'android', sim:0.82, match:true,
    q:'Spotify keeps stopping every 30 seconds on my Android phone.',
    a:'Could you confirm your Android version and Spotify version? Does this happen on both WiFi and mobile data? /SC' },
  { id:'p002', intent:'playback_error',      plat:'android', sim:0.71, match:true,
    q:'App keeps pausing randomly on Android.',
    a:'Try clearing the Spotify cache: Settings → Apps → Spotify → Clear Cache, then restart. /SC' },
  { id:'p003', intent:'playlist_library',    plat:'unknown', sim:0.79, match:false,
    q:'All my liked songs disappeared after the latest update.',
    a:'Hey! Try logging out and back in — that usually resyncs your library. /SC' },
  { id:'p004', intent:'billing_charge',      plat:'unknown', sim:0.74, match:false,
    q:'I was charged for a premium family account I never signed up for.',
    a:"Hi! Can you DM us your account email? We'll look into the billing straight away. /SC" },
  { id:'p005', intent:'account_login',       plat:'unknown', sim:0.81, match:false,
    q:"Password reset email never arrives.",
    a:"Check your spam/junk folder first! If it's not there, try in a different browser. DM us if still stuck. /SC" },
  { id:'p006', intent:'device_platform',     plat:'alexa',   sim:0.68, match:true,
    q:"Alexa says 'account not found' when I try to play Spotify.",
    a:'Try unlinking and relinking Spotify in the Alexa app under Skills → Your Skills. /SC' },
  { id:'p007', intent:'offline_download',    plat:'unknown', sim:0.65, match:false,
    q:'Songs downloaded but not available when I go offline.',
    a:'Toggle offline mode off then back on in Settings, then re-download your playlists. /SC' },
  { id:'p008', intent:'app_crash_bug',       plat:'ios',     sim:0.72, match:true,
    q:'Spotify crashes every time I open it on my iPhone.',
    a:'Try force-closing the app, then reinstalling from the App Store. /SC' },
  { id:'p009', intent:'premium_subscription',plat:'unknown', sim:0.77, match:false,
    q:'Still showing as free after paying for premium.',
    a:"Check your Account page at spotify.com — make sure you're signed in to the right account. DM us if it still shows free. /SC" },
  { id:'p010', intent:'content_unavailable', plat:'unknown', sim:0.61, match:false,
    q:"An entire artist's catalogue disappeared from Spotify.",
    a:"Some content is removed due to licensing agreements. We can't restore content that artists have chosen to remove. /SC" },
]

export default function Evidence() {
  const [q,    setQ]   = useState('')
  const [int,  setInt] = useState('all')
  const [plat, setPlat] = useState('all')
  const [open, setOpen] = useState(null)

  const intents  = ['all', ...Array.from(new Set(CORPUS.map(r => r.intent)))]
  const plats    = ['all', 'android', 'ios', 'alexa', 'unknown']

  const rows = CORPUS.filter(r => {
    if (int  !== 'all' && r.intent !== int)  return false
    if (plat !== 'all' && r.plat   !== plat) return false
    if (q && !r.q.toLowerCase().includes(q.toLowerCase()) &&
             !r.a.toLowerCase().includes(q.toLowerCase())) return false
    return true
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="min-h-screen bg-dark p-6"
    >
      <div className="mb-6">
        <h1 className="text-20 font-bold text-dtxt tracking-tight mb-0.5">Evidence Browser</h1>
        <p className="text-12 text-dtxt3">Historical SpotifyCares corpus · 500-example retrieval sample</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dline
                        bg-dark2 flex-1 min-w-48 max-w-sm">
          <Search size={13} className="text-dtxt3 flex-shrink-0" />
          <input
            value={q} onChange={e => setQ(e.target.value)}
            placeholder="Search historical conversations…"
            className="text-13 bg-transparent outline-none flex-1 text-dtxt placeholder-dtxt3"
          />
        </div>
        {[['Intent', intents, int, setInt], ['Platform', plats, plat, setPlat]].map(([label, opts, val, setVal]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-11 text-dtxt3">{label}:</span>
            <select value={val} onChange={e => setVal(e.target.value)}
              className="text-12 border border-dline rounded-lg px-2 py-1.5 bg-dark2
                         text-dtxt focus:outline-none focus:border-accent-500/40">
              {opts.map(o => <option key={o} value={o}>{o === 'all' ? `All ${label.toLowerCase()}s` : o.replace(/_/g,' ')}</option>)}
            </select>
          </div>
        ))}
        <span className="text-11 text-dtxt3 ml-auto">{rows.length} result{rows.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Results */}
      <div className="space-y-2">
        {rows.map((ev, i) => (
          <motion.div
            key={ev.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className="bg-dark2 border border-dline rounded-xl overflow-hidden shadow-dark-card"
          >
            <button
              onClick={() => setOpen(open === ev.id ? null : ev.id)}
              className="w-full flex items-start gap-4 px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
            >
              {/* Similarity */}
              <div className="flex-shrink-0 text-center w-12">
                <p className={cn('text-20 font-black tabular-nums leading-none',
                  ev.sim >= 0.75 ? 'text-go' : ev.sim >= 0.60 ? 'text-hold' : 'text-dtxt3')}>
                  {ev.sim.toFixed(2)}
                </p>
                <p className="text-10 text-dtxt3 mt-0.5 uppercase tracking-caps">sim</p>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <IntentBadge intent={ev.intent} dark />
                  <span className={cn(
                    'text-10 px-2 py-px rounded border font-medium',
                    ev.match
                      ? 'bg-go/10 text-go border-go/25'
                      : 'bg-dark3 text-dtxt3 border-dline',
                  )}>
                    {ev.plat !== 'unknown' ? ev.plat : 'platform unknown'}
                    {ev.match && ' ✓'}
                  </span>
                </div>
                <p className="text-14 text-dtxt leading-snug truncate">{ev.q}</p>
              </div>

              {open === ev.id
                ? <ChevronUp size={14} className="text-dtxt3 flex-shrink-0 mt-1" />
                : <ChevronDown size={14} className="text-dtxt3 flex-shrink-0 mt-1" />}
            </button>

            {open === ev.id && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="border-t border-dline"
              >
                <div className="grid grid-cols-2 divide-x divide-dline">
                  <div className="px-5 py-4">
                    <p className="text-10 text-dtxt3 uppercase tracking-widest mb-2">Customer message</p>
                    <p className="text-13 text-dtxt leading-relaxed italic">"{ev.q}"</p>
                  </div>
                  <div className="px-5 py-4">
                    <p className="text-10 text-dtxt3 uppercase tracking-widest mb-2">Historical response</p>
                    <p className="text-13 text-dtxt2 leading-relaxed">{ev.a}</p>
                  </div>
                </div>
                <div className="px-5 py-2.5 bg-dark3 border-t border-dline flex gap-4 text-11 text-dtxt3">
                  <span>ID: {ev.id}</span>
                  <span>sim {ev.sim.toFixed(3)}</span>
                  <span>platform match: {ev.match ? 'yes ✓' : 'no'}</span>
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      <p className="mt-6 text-center text-12 text-dtxt3">
        Demo sample · full corpus (34,721 pairs) available via backend
      </p>
    </motion.div>
  )
}
