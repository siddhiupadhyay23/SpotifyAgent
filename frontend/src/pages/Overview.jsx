import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ChevronRight, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react'
import { CountUp } from '../components/ui'
import { cn } from '../lib/utils'

/* ── Reveal wrapper — animates children when in view ─────────── */
function Reveal({ children, delay = 0, className }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay, ease: [0.23, 1, 0.32, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/* ── Numbered step card (dark surface, 2-col: text + visual) ── */
function StepCard({ num, title, body, metric, metricLabel, children, delay = 0 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-40px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay, ease: [0.23, 1, 0.32, 1] }}
      className="relative bg-dark2 border border-dline rounded-xl p-6 overflow-hidden
                 hover:border-white/[0.14] transition-colors group"
    >
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
                      from-transparent via-accent-500/30 to-transparent" />

      {/* Step number + metric row */}
      <div className="flex items-start justify-between mb-4">
        <span className="text-10 font-bold text-dtxt3 uppercase tracking-widest">
          {String(num).padStart(2, '0')}
        </span>
        {metric && (
          <div className="text-right">
            <div className="text-[28px] font-black text-dtxt tracking-tightest leading-none">
              {inView
                ? <CountUp to={parseFloat(metric.replace('%',''))}
                    decimals={metric.includes('.') ? 1 : 0}
                    suffix={metric.includes('%') ? '%' : ''} />
                : metric}
            </div>
            <p className="text-10 text-dtxt3 mt-0.5 uppercase tracking-caps">{metricLabel}</p>
          </div>
        )}
      </div>

      <h3 className="text-[17px] font-bold text-dtxt tracking-tight mb-2">{title}</h3>
      <p className="text-13 text-dtxt2 leading-relaxed mb-4">{body}</p>
      {children}
    </motion.div>
  )
}

/* ── Proof stat ───────────────────────────────────────────────── */
function ProofStat({ value, decimals = 0, suffix = '', label, delay = 0 }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-30px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay }}
      className="text-center"
    >
      <div className="text-[44px] font-black text-ink tracking-tightest leading-none mb-2">
        {inView
          ? <CountUp to={value} decimals={decimals} suffix={suffix} />
          : `${value.toFixed(decimals)}${suffix}`}
      </div>
      <p className="text-13 text-ink3 leading-snug max-w-xs mx-auto">{label}</p>
    </motion.div>
  )
}

export default function Overview() {
  const nav = useNavigate()
  return (
    <div className="min-h-screen">

      {/* ════════════════════════════════════════════════════════
          HERO — light editorial section
          ════════════════════════════════════════════════════════ */}
      <section className="relative bg-paper flex flex-col justify-center
                           px-8 lg:px-16 pt-20 pb-16 overflow-hidden">
        {/* Subtle dot grid */}
        <div className="absolute inset-0 bg-dot-light bg-dot opacity-50 pointer-events-none" />
        {/* Faint blue top wash */}
        <div className="absolute top-0 left-0 right-0 h-96
                        bg-gradient-to-b from-accent-50/60 to-transparent pointer-events-none" />

        <div className="relative max-w-5xl mx-auto w-full">
          {/* Label */}
          <Reveal delay={0}>
            <div className="flex items-center gap-2 mb-8">
              <div className="w-5 h-5 rounded bg-accent-500 flex items-center justify-center">
                <Sparkles size={11} className="text-white" />
              </div>
              <span className="text-12 font-semibold text-accent-600 uppercase tracking-widest">
                SpotifyAgent
              </span>
            </div>
          </Reveal>

          {/* Hero headline */}
          <div className="overflow-hidden mb-6">
            {['SUPPORT THAT', 'KNOWS WHAT', 'WORKED BEFORE.'].map((line, i) => (
              <motion.div
                key={line}
                initial={{ y: '110%' }}
                animate={{ y: 0 }}
                transition={{ duration: 0.7, delay: 0.1 + i * 0.12, ease: [0.23, 1, 0.32, 1] }}
              >
                <h1 className={cn(
                  'font-black tracking-tightest leading-none',
                  'text-40 lg:text-[52px]',
                  i === 2 ? 'text-gradient-blue' : 'text-ink',
                )}>
                  {line}
                </h1>
              </motion.div>
            ))}
          </div>

          <Reveal delay={0.5}>
            <p className="text-15 text-ink2 leading-relaxed max-w-xl mb-8 text-balance">
              An evidence-grounded AI support agent that learns from how your team
              solved similar customer problems before.
            </p>
          </Reveal>

          <Reveal delay={0.65}>
            <div className="flex items-center gap-4 flex-wrap">
              <button
                onClick={() => nav('/agent')}
                className="flex items-center gap-2 px-6 py-3 rounded-lg bg-accent-500
                           text-white text-15 font-semibold hover:bg-accent-600
                           transition-colors shadow-glow"
              >
                Open AI Agent
                <ArrowRight size={15} />
              </button>
              <button
                onClick={() => nav('/evidence')}
                className="flex items-center gap-2 px-6 py-3 rounded-lg border border-rule-2
                           text-ink2 text-15 font-semibold hover:bg-canvas hover:border-rule-2
                           transition-colors"
              >
                View Evidence
              </button>
            </div>
          </Reveal>

          {/* Quick proof strip */}
          <Reveal delay={0.8}>
            <div className="mt-10 pt-8 border-t border-rule flex items-center gap-8 flex-wrap">
              {[
                { v: '90.5%', label: 'Intent Accuracy' },
                { v: '89.3%', label: 'Macro F1' },
                { v: '200',   label: 'Golden Examples' },
                { v: '0.82',  label: 'Best Evidence Sim' },
              ].map(s => (
                <div key={s.label}>
                  <p className="text-20 font-black text-ink tracking-tight leading-none">{s.v}</p>
                  <p className="text-11 text-ink3 mt-1 uppercase tracking-caps">{s.label}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════
          AI WORKFLOW — dark section, 4 numbered steps
          ════════════════════════════════════════════════════════ */}
      <section className="bg-void py-16 px-8 lg:px-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-dot-dark bg-dot opacity-100 pointer-events-none" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
                        from-transparent via-dline to-transparent" />

        <div className="relative max-w-5xl mx-auto">
          <Reveal>
            <p className="text-11 font-semibold text-dtxt3 uppercase tracking-widest mb-4">How it works</p>
            <h2 className="text-32 lg:text-[40px] font-black text-dtxt tracking-tightest mb-10">
              Four steps.<br />
              <span className="text-accent-400">One pipeline.</span>
            </h2>
          </Reveal>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <StepCard num={1} title="Understand" delay={0.05}
              metric="90.5%" metricLabel="Intent accuracy"
              body="TF-IDF + Logistic Regression classifies every customer message into one of 9 intents. Platform and device are extracted as separate signals.">
              {/* Visual: classification result panel */}
              <div className="rounded-lg border border-dline bg-dark3 p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-11 font-mono text-accent-400 font-semibold">PLAYBACK_ERROR</span>
                  <span className="text-11 font-bold text-go">92%</span>
                </div>
                <div className="h-1 bg-dline rounded-full overflow-hidden">
                  <div className="h-full w-[92%] bg-go rounded-full" />
                </div>
                <div className="flex items-center gap-3 pt-1">
                  <span className="text-10 text-dtxt3 uppercase tracking-caps">Platform</span>
                  <span className="text-11 text-accent-400 font-medium">Android detected</span>
                </div>
              </div>
            </StepCard>

            <StepCard num={2} title="Remember" delay={0.1}
              metric="0.82" metricLabel="Top similarity"
              body="Hybrid TF-IDF + Jaccard retrieval finds similar historical SpotifyCares conversations. Platform matching boosts platform-relevant results.">
              {/* Visual: evidence card */}
              <div className="rounded-lg border border-dline bg-dark3 p-3.5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-10 text-dtxt3 uppercase tracking-caps">Closest match</span>
                  <div className="flex items-center gap-2">
                    <span className="text-10 text-go font-medium">android ✓</span>
                    <span className="text-10 text-dtxt3 tabular-nums">sim 0.82</span>
                  </div>
                </div>
                <p className="text-12 text-dtxt2 italic leading-snug mb-2">
                  "Spotify keeps stopping on my Android every 30 seconds…"
                </p>
                <p className="text-12 text-dtxt2 leading-snug border-t border-dline pt-2">
                  → "Could you confirm your Android and Spotify versions?"
                </p>
              </div>
            </StepCard>

            <StepCard num={3} title="Respond" delay={0.15}
              body="A grounded response is generated from retrieved historical evidence. The model is instructed not to invent policies or troubleshooting steps absent from evidence.">
              {/* Visual: AI response card */}
              <div className="rounded-lg border border-accent-500/20 bg-accent-500/5 p-3.5 relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
                                from-transparent via-accent-500/40 to-transparent" />
                <p className="text-10 text-accent-400 uppercase tracking-caps mb-2">AI Suggested Response</p>
                <p className="text-12 text-dtxt2 leading-relaxed">
                  "Hi Alex! Could you confirm your Android and Spotify versions? It'd help to know if this happens on WiFi and mobile data."
                </p>
              </div>
            </StepCard>

            <StepCard num={4} title="Decide" delay={0.2}
              metric="47.4%" metricLabel="Escalation F1"
              body="Confidence threshold + risk-signal rules determine AUTO-HANDLE vs ESCALATE. Recall 0.90 — only 3 of 30 true escalations missed.">
              {/* Visual: decision panel */}
              <div className="space-y-2">
                <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-go/10 border border-go/25">
                  <CheckCircle2 size={13} className="text-go" />
                  <div>
                    <p className="text-12 font-bold text-go leading-none">AUTO-HANDLE</p>
                    <p className="text-10 text-dtxt3 mt-0.5">Strong evidence · Low risk</p>
                  </div>
                </div>
                <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-stop/10 border border-stop/25">
                  <AlertTriangle size={13} className="text-stop" />
                  <div>
                    <p className="text-12 font-bold text-stop leading-none">ESCALATE</p>
                    <p className="text-10 text-dtxt3 mt-0.5">Billing dispute · Security risk</p>
                  </div>
                </div>
              </div>
            </StepCard>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════
          PROOF SECTION — light, oversized numbers
          ════════════════════════════════════════════════════════ */}
      <section className="bg-paper py-16 px-8 lg:px-16 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-px bg-rule" />

        <div className="max-w-5xl mx-auto">
          <Reveal>
            <p className="text-11 font-semibold text-accent-600 uppercase tracking-widest mb-4">Measured Results</p>
            <h2 className="text-28 lg:text-[36px] font-black text-ink tracking-tightest mb-12">
              The numbers<br />don't lie.
            </h2>
          </Reveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            <ProofStat value={90.5}  decimals={1} suffix="%" label="Intent accuracy on 200 held-out golden examples" delay={0}    />
            <ProofStat value={89.3}  decimals={1} suffix="%" label="Macro F1 across all 9 intent categories"         delay={0.1}  />
            <ProofStat value={90}    decimals={0} suffix="%" label="Escalation recall — catches 9 in 10 true escalations" delay={0.2} />
          </div>

          <Reveal delay={0.3}>
            <div className="mt-12 pt-8 border-t border-rule">
              <p className="text-11 text-ink3 uppercase tracking-widest mb-3">Baseline comparison</p>
              <div className="grid grid-cols-3 gap-px bg-rule-2 rounded-lg overflow-hidden text-center">
                {[
                  { sys: 'Majority Baseline', mf1: '0.036', dim: true  },
                  { sys: 'TF-IDF + LR',       mf1: '0.893', dim: false },
                  { sys: 'Final Agent',        mf1: '0.893', bold: true },
                ].map(r => (
                  <div key={r.sys} className={cn(
                    'px-5 py-4',
                    r.bold ? 'bg-accent-50' : 'bg-white',
                  )}>
                    <p className={cn('text-11 mb-1.5 uppercase tracking-caps',
                      r.dim ? 'text-ink3' : 'text-ink2')}>{r.sys}</p>
                    <p className={cn('text-24 font-black tracking-tightest',
                      r.bold ? 'text-accent-600' : r.dim ? 'text-ink3' : 'text-ink')}>{r.mf1}</p>
                    <p className="text-10 text-ink3 mt-1">Macro F1</p>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════
          CTA — dark closing section
          ════════════════════════════════════════════════════════ */}
      <section className="bg-dark2 py-14 px-8 lg:px-16 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
                        from-transparent via-accent-500/30 to-transparent" />
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-8 flex-wrap">
          <div>
            <Reveal>
              <h2 className="text-24 lg:text-[32px] font-black text-dtxt tracking-tightest mb-1.5">
                See it in action.
              </h2>
              <p className="text-15 text-dtxt2">Open the AI Agent workspace to run the full pipeline.</p>
            </Reveal>
          </div>
          <Reveal delay={0.1}>
            <button
              onClick={() => nav('/agent')}
              className="flex items-center gap-2 px-8 py-4 rounded-lg bg-accent-500
                         text-white text-15 font-bold hover:bg-accent-600 transition-colors"
            >
              Open AI Agent
              <ChevronRight size={15} />
            </button>
            <button
              onClick={() => nav('/portal')}
              className="flex items-center gap-2 px-6 py-4 rounded-lg border border-white/20
                         text-dtxt text-15 font-bold hover:bg-white/[0.06] transition-colors"
            >
              Customer portal
              <ChevronRight size={15} />
            </button>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
