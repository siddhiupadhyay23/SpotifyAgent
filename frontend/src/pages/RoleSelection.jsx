import { useNavigate } from 'react-router-dom'
import { ArrowRight, Headphones, ShieldCheck, Sparkles } from 'lucide-react'

const CUSTOMER_SESSION_KEY = 'spotifyagent.customer-session'
const ADMIN_SESSION_KEY = 'spotifyagent.admin-session'

export default function RoleSelection() {
  const navigate = useNavigate()

  function chooseCustomer() {
    window.localStorage.removeItem(CUSTOMER_SESSION_KEY)
    navigate('/portal')
  }

  function chooseAdmin() {
    window.localStorage.removeItem(ADMIN_SESSION_KEY)
    navigate('/admin')
  }

  return (
    <main className="min-h-screen bg-canvas px-5 py-10 text-ink sm:py-16">
      <div className="mx-auto flex min-h-[calc(100vh-80px)] max-w-4xl flex-col justify-center">
        <div className="mb-10 text-center sm:mb-14">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-green-600 text-white shadow-lift">
            <Sparkles size={22} />
          </div>
          <p className="text-12 font-semibold uppercase tracking-widest text-go-text">SpotifyAgent</p>
          <h1 className="mt-2 text-32 font-black tracking-tightest text-ink sm:text-40">AI-powered customer support</h1>
          <p className="mx-auto mt-3 max-w-xl text-15 leading-relaxed text-ink3">Choose how you’d like to use SpotifyAgent.</p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <button onClick={chooseCustomer} className="group rounded-2xl border border-rule bg-white p-7 text-left shadow-card transition hover:-translate-y-0.5 hover:border-green-500 hover:shadow-lift focus:outline-none focus:ring-2 focus:ring-green-500/30">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-green-100 text-go"><Headphones size={21} /></div>
            <h2 className="mt-5 text-20 font-bold tracking-tight">Customer</h2>
            <p className="mt-2 min-h-12 text-13 leading-relaxed text-ink3">Get help, start a support conversation, and follow your own request from start to resolution.</p>
            <span className="mt-6 flex items-center gap-2 text-13 font-semibold text-go-text">Continue as customer <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" /></span>
          </button>

          <button onClick={chooseAdmin} className="group rounded-2xl border border-dark3 bg-dark p-7 text-left shadow-dark-card transition hover:-translate-y-0.5 hover:border-accent-500/60 hover:shadow-glow focus:outline-none focus:ring-2 focus:ring-accent-500/40">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-500/20 text-accent-400"><ShieldCheck size={21} /></div>
            <h2 className="mt-5 text-20 font-bold tracking-tight text-dtxt">Support Admin</h2>
            <p className="mt-2 min-h-12 text-13 leading-relaxed text-dtxt2">Review the real support inbox, take over escalated cases, and resolve customer requests.</p>
            <span className="mt-6 flex items-center gap-2 text-13 font-semibold text-accent-400">Open admin workspace <ArrowRight size={15} className="transition-transform group-hover:translate-x-1" /></span>
          </button>
        </div>
      </div>
    </main>
  )
}
