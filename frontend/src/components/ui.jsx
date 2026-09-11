import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle } from 'lucide-react'
import { cn } from '../lib/utils'

/* ── Intent badge ─────────────────────────────────────────────── */
const INTENT_MAP = {
  playback_error:       ['bg-blue-50   text-blue-700   border-blue-200',   'Playback Error'],
  account_login:        ['bg-violet-50 text-violet-700 border-violet-200', 'Account / Login'],
  premium_subscription: ['bg-teal-50   text-teal-700   border-teal-200',   'Premium'],
  billing_charge:       ['bg-amber-50  text-amber-700  border-amber-200',  'Billing'],
  app_crash_bug:        ['bg-red-50    text-red-700    border-red-200',    'App Crash'],
  playlist_library:     ['bg-cyan-50   text-cyan-700   border-cyan-200',   'Playlist'],
  content_unavailable:  ['bg-yellow-50 text-yellow-700 border-yellow-200', 'Unavailable'],
  device_platform:      ['bg-indigo-50 text-indigo-700 border-indigo-200', 'Device / Platform'],
  offline_download:     ['bg-emerald-50 text-emerald-700 border-emerald-200','Offline'],
}

export function IntentBadge({ intent, dark = false }) {
  if (dark) {
    // dark-context version
    const labels = {
      playback_error: 'Playback Error', account_login: 'Account / Login',
      premium_subscription: 'Premium', billing_charge: 'Billing',
      app_crash_bug: 'App Crash', playlist_library: 'Playlist',
      content_unavailable: 'Unavailable', device_platform: 'Device / Platform',
      offline_download: 'Offline',
    }
    return (
      <span className="inline-flex items-center px-2 py-px rounded text-11 font-medium
                       bg-white/[0.08] text-dtxt2 border border-dline">
        {labels[intent] || intent}
      </span>
    )
  }
  const [cls, lbl] = INTENT_MAP[intent] || ['bg-stone-50 text-stone-600 border-stone-200', intent || '—']
  return (
    <span className={cn('inline-flex items-center px-2 py-px rounded text-11 font-medium border', cls)}>
      {lbl}
    </span>
  )
}

/* ── Decision badge ───────────────────────────────────────────── */
export function DecisionBadge({ decision, dark = false }) {
  const esc = decision === 'ESCALATE'
  if (dark) {
    return (
      <span className={cn(
        'inline-flex items-center gap-1 px-2 py-px rounded text-11 font-semibold border',
        esc ? 'bg-stop-bg/20 text-stop border-stop/30' : 'bg-go-bg/20 text-go border-go/30',
      )}>
        {esc ? <AlertTriangle size={10} /> : <CheckCircle2 size={10} />}
        {esc ? 'Escalate' : 'Auto-Handle'}
      </span>
    )
  }
  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-2 py-px rounded text-11 font-semibold border',
      esc
        ? 'bg-stop-bg text-stop-text border-red-200'
        : 'bg-go-bg  text-go-text  border-green-200',
    )}>
      {esc ? <AlertTriangle size={10} /> : <CheckCircle2 size={10} />}
      {esc ? 'Escalate' : 'Auto-Handle'}
    </span>
  )
}

/* ── Confidence bar ───────────────────────────────────────────── */
export function ConfBar({ value, dark = false }) {
  const pct = Math.round((value || 0) * 100)
  const col  = pct >= 80 ? 'bg-go' : pct >= 55 ? 'bg-hold' : 'bg-stop'
  const track = dark ? 'bg-white/[0.08]' : 'bg-stone-100'
  return (
    <div className="flex items-center gap-2.5">
      <div className={cn('flex-1 h-1 rounded-full overflow-hidden', track)}>
        <motion.div className={cn('h-full rounded-full', col)}
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }} />
      </div>
      <span className={cn('text-12 font-semibold tabular-nums w-9', dark ? 'text-dtxt' : 'text-ink')}>{pct}%</span>
    </div>
  )
}

/* ── Count-up number ──────────────────────────────────────────── */
export function CountUp({ to, decimals = 0, suffix = '', className }) {
  const ref = useRef(null)
  useEffect(() => {
    let st = null
    const dur = 900
    const tick = ts => {
      if (!st) st = ts
      const p = Math.min((ts - st) / dur, 1)
      const v = to * (1 - Math.pow(1 - p, 3))
      if (ref.current) ref.current.textContent = v.toFixed(decimals) + suffix
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [to, decimals, suffix])
  return <span ref={ref} className={className}>{to.toFixed(decimals)}{suffix}</span>
}

/* ── Skeleton ─────────────────────────────────────────────────── */
export function Skeleton({ className, dark = false }) {
  return <div className={cn('rounded animate-shimmer', dark ? 'bg-white/[0.06]' : 'bg-stone-100', className)} />
}
