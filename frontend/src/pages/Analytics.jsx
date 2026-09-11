import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { IntentBadge } from '../components/ui'
import { cn } from '../lib/utils'

const INTENT_F1 = [
  { id:'billing_charge',       f1:0.9600, n:25 },
  { id:'account_login',        f1:0.9375, n:16 },
  { id:'device_platform',      f1:0.9375, n:33 },
  { id:'offline_download',     f1:0.9286, n:13 },
  { id:'premium_subscription', f1:0.8929, n:30 },
  { id:'playback_error',       f1:0.8916, n:38 },
  { id:'playlist_library',     f1:0.8846, n:26 },
  { id:'app_crash_bug',        f1:0.8000, n:8  },
  { id:'content_unavailable',  f1:0.8000, n:11 },
]

const FAILURES = [
  { n:1, mode:'Wrong intent (billing vs subscription)',       count:12, root:'Lexical overlap between billing and premium keywords.' },
  { n:2, mode:'Missed escalation (false auto-handle)',        count:3,  root:'Subtle billing signals without explicit dispute keywords.' },
  { n:3, mode:'DM redirect retrieved as top evidence',       count:8,  root:'Some DM-redirect responses retained after filtering.' },
  { n:4, mode:'Insufficient retrieval evidence',             count:6,  root:'Query too short — no close historical match found.' },
  { n:5, mode:'Platform mismatch in evidence',               count:4,  root:'Platform-filter fallback returns different-platform result.' },
]

function Reveal({ children, delay = 0, className }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-30px' })
  return (
    <motion.div ref={ref}
      initial={{ opacity: 0, y: 14 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay, ease: [0.23, 1, 0.32, 1] }}
      className={className}>
      {children}
    </motion.div>
  )
}

function Card({ children, className }) {
  return (
    <div className={cn('bg-dark2 border border-dline rounded-xl overflow-hidden', className)}>
      {children}
    </div>
  )
}

function CardHead({ title, sub }) {
  return (
    <div className="px-5 py-3.5 border-b border-dline">
      <p className="text-14 font-bold text-dtxt">{title}</p>
      {sub && <p className="text-11 text-dtxt3 mt-0.5">{sub}</p>}
    </div>
  )
}

function AnimBar({ value, color = 'bg-accent-500', delay = 0 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })
  return (
    <div ref={ref} className="flex-1 h-1 bg-dline rounded-full overflow-hidden">
      <motion.div className={cn('h-full rounded-full', color)}
        initial={{ width: 0 }}
        animate={inView ? { width: `${value * 100}%` } : {}}
        transition={{ duration: 0.6, delay, ease: 'easeOut' }} />
    </div>
  )
}

export default function Analytics() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="min-h-screen bg-dark p-6"
    >
      <div className="mb-6">
        <h1 className="text-20 font-bold text-dtxt tracking-tight mb-0.5">Analytics</h1>
        <p className="text-13 text-dtxt3">
          All numbers from{' '}
          <span className="font-mono text-12 text-dtxt2">results/full_evaluation.json</span>
          {' '}— n=200 golden examples
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Baseline comparison */}
        <Reveal className="lg:col-span-2">
          <Card>
            <CardHead title="Baseline Comparison" sub="Trivial baseline vs TF-IDF+LR vs Final agent" />
            <div className="px-5 py-4">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dline">
                    {['System','Accuracy','Macro F1','Wtd F1'].map((h,i) => (
                      <th key={h} className={cn('pb-2.5 text-10 font-semibold uppercase tracking-widest text-dtxt3',
                        i === 0 ? 'text-left' : 'text-right')}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-dline">
                  {[
                    { sys:'Majority baseline', acc:'0.190', mf1:'0.036', wf1:'0.061', dim:true  },
                    { sys:'TF-IDF + LR',        acc:'0.905', mf1:'0.893', wf1:'0.904'            },
                    { sys:'Final agent',         acc:'0.905', mf1:'0.893', wf1:'0.904', bold:true },
                  ].map(r => (
                    <tr key={r.sys} className={r.dim ? 'opacity-40' : ''}>
                      <td className={cn('py-3 text-13', r.bold ? 'font-bold text-dtxt' : 'text-dtxt2')}>
                        {r.sys}
                      </td>
                      {[r.acc, r.mf1, r.wf1].map((v, i) => (
                        <td key={i} className={cn('py-3 text-right text-12 font-mono tabular-nums',
                          r.bold && i === 1 ? 'font-black text-accent-400' : 'text-dtxt2')}>{v}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-11 text-dtxt3 mt-3 pt-3 border-t border-dline">
                Macro F1: 0.036 (majority) → 0.893 (final agent) — 24.8x improvement
              </p>
            </div>
          </Card>
        </Reveal>

        {/* Escalation */}
        <Reveal delay={0.05}>
          <Card>
            <CardHead title="Escalation Policy" sub="Final agent · golden set n=200" />
            <div className="px-5 py-4 space-y-4">
              {[
                { label:'Precision',         value:0.321, fmt:'0.321', color:'bg-accent-500' },
                { label:'Recall',            value:0.900, fmt:'0.900', color:'bg-go'         },
                { label:'F1',                value:0.474, fmt:'0.474', color:'bg-accent-500' },
                { label:'False auto-handle', value:0.100, fmt:'10.0%', color:'bg-hold'       },
              ].map((m, i) => (
                <div key={m.label}>
                  <div className="flex justify-between mb-1.5">
                    <span className="text-12 text-dtxt2">{m.label}</span>
                    <span className="text-12 font-bold font-mono text-dtxt tabular-nums">{m.fmt}</span>
                  </div>
                  <AnimBar value={m.value} color={m.color} delay={0.05 * i} />
                </div>
              ))}
              <p className="text-11 text-dtxt3 pt-2 border-t border-dline leading-relaxed">
                Recall 0.90 = only 3/30 true escalations missed.
                Low precision is intentional — prefer over-escalating to missing a billing dispute.
              </p>
            </div>
          </Card>
        </Reveal>

        {/* Per-intent F1 */}
        <Reveal delay={0.08} className="lg:col-span-2">
          <Card>
            <CardHead title="Per-Intent F1" sub="Final agent on golden set" />
            <div className="px-5 py-4 space-y-2.5">
              {INTENT_F1.map((row, i) => (
                <div key={row.id} className="flex items-center gap-3">
                  <div className="w-32 flex-shrink-0">
                    <IntentBadge intent={row.id} dark />
                  </div>
                  <AnimBar value={row.f1} delay={0.04 * i} />
                  <span className="text-12 font-mono font-bold text-dtxt tabular-nums w-12 text-right">
                    {row.f1.toFixed(4)}
                  </span>
                  <span className="text-10 text-dtxt3 w-10 text-right">n={row.n}</span>
                </div>
              ))}
            </div>
          </Card>
        </Reveal>

        {/* Retrieval ablation */}
        <Reveal delay={0.1}>
          <Card>
            <CardHead title="Retrieval Ablation" sub="500-example corpus sample" />
            <div className="px-5 py-4 space-y-4">
              {[
                { name:'Jaccard baseline',    cov:0.530, avg:0.176, pm:0.581, current:false },
                { name:'Hybrid TF-IDF+Jac',  cov:0.570, avg:0.178, pm:0.488, current:true  },
              ].map((r, ri) => (
                <div key={r.name} className={cn('rounded-lg px-3.5 py-3 border',
                  r.current ? 'border-accent-500/25 bg-accent-500/5' : 'border-dline bg-dark3')}>
                  <p className={cn('text-12 font-semibold mb-2.5',
                    r.current ? 'text-accent-400' : 'text-dtxt2')}>
                    {r.name}{r.current && ' ← used'}
                  </p>
                  {[
                    { l:'Coverage >0.15', v:r.cov, f:r.cov.toFixed(3) },
                    { l:'Avg top-1 sim',  v:r.avg, f:r.avg.toFixed(3) },
                    { l:'Platform match', v:r.pm,  f:r.pm.toFixed(3)  },
                  ].map((m, mi) => (
                    <div key={m.l} className="flex items-center gap-2 mb-1.5">
                      <span className="text-11 text-dtxt3 w-24">{m.l}</span>
                      <AnimBar value={m.v} delay={ri * 0.08 + mi * 0.04}
                               color={r.current ? 'bg-accent-500' : 'bg-dtxt3'} />
                      <span className="text-11 font-mono text-dtxt2 w-10 text-right">{m.f}</span>
                    </div>
                  ))}
                </div>
              ))}
              <p className="text-10 text-dtxt3">
                Recall@K not reported — no ground-truth relevance labels.
              </p>
            </div>
          </Card>
        </Reveal>

        {/* Failure modes */}
        <Reveal delay={0.12} className="lg:col-span-2">
          <Card>
            <CardHead title="Top 5 Failure Modes" sub="From failure_analysis.py on final_predictions.jsonl" />
            <div className="divide-y divide-dline">
              {FAILURES.map((f, i) => (
                <motion.div
                  key={f.n}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: 0.05 * i }}
                  className="flex items-start gap-4 px-5 py-4"
                >
                  <span className="w-6 h-6 rounded-full bg-dark3 border border-dline
                                   flex items-center justify-center text-11 font-bold text-dtxt3
                                   flex-shrink-0 mt-0.5">
                    {f.n}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-13 font-semibold text-dtxt mb-0.5">{f.mode}</p>
                    <p className="text-12 text-dtxt3 leading-relaxed">{f.root}</p>
                  </div>
                  <span className="text-13 font-bold text-dtxt3 tabular-nums flex-shrink-0">{f.count}</span>
                </motion.div>
              ))}
            </div>
          </Card>
        </Reveal>

        {/* Limitations */}
        <Reveal delay={0.15}>
          <Card>
            <CardHead title="Limitations" sub="What the headline number hides" />
            <div className="px-5 py-4 space-y-2">
              {[
                'Golden set n=200; rare classes (n<15) have high variance.',
                'Retrieval capped at 500 examples (sample). Full = 34,721 pairs.',
                'No OPENAI_API_KEY: template fallback, not grounded LLM.',
                'Response quality not evaluated — requires API + LLM judge.',
                'Intent labels are keyword-derived, not human-annotated.',
                'Escalation labels are rule-derived heuristics.',
                'Dataset is 2013–2017; Spotify product has changed.',
              ].map((l, i) => (
                <p key={i} className="flex gap-2 text-12 text-dtxt2 leading-relaxed">
                  <span className="text-dtxt3 flex-shrink-0 mt-0.5">·</span>{l}
                </p>
              ))}
            </div>
          </Card>
        </Reveal>

      </div>
    </motion.div>
  )
}
