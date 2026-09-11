import { NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LayoutDashboard, Sparkles, MessageSquare, BookOpen, BarChart2, Zap } from 'lucide-react'
import { cn } from '../lib/utils'

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Overview'      },
  { to: '/agent',         icon: Sparkles,        label: 'AI Agent'      },
  { to: '/conversations', icon: MessageSquare,   label: 'Conversations' },
  { to: '/evidence',      icon: BookOpen,        label: 'Evidence'      },
  { to: '/analytics',     icon: BarChart2,       label: 'Analytics'     },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  return (
    <aside className="w-52 flex-shrink-0 flex flex-col h-screen sticky top-0
                      bg-dark border-r border-dline z-20">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 pt-5 pb-4">
        <div className="w-7 h-7 rounded-lg bg-accent-500 flex items-center justify-center flex-shrink-0">
          <Zap size={13} className="text-white" strokeWidth={2.5} fill="white" />
        </div>
        <div>
          <p className="text-14 font-bold text-dtxt leading-none tracking-tight">SpotifyAgent</p>
          <p className="text-10 text-dtxt3 uppercase tracking-caps leading-none mt-0.5">AI Support</p>
        </div>
      </div>

      <div className="mx-3 h-px bg-dline mb-2" />

      <nav className="flex-1 px-2 py-1 space-y-px">
        {NAV.map(({ to, icon: Icon, label }) => {
          const active = pathname === to
          return (
            <NavLink key={to} to={to} aria-current={active ? 'page' : undefined}>
              <div className="relative group">
                {active && (
                  <motion.div
                    layoutId="sb-pill"
                    className="absolute inset-0 rounded-md bg-accent-500/10 border border-accent-500/20"
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
                {/* Hover glow */}
                <div className="absolute inset-0 rounded-md opacity-0 group-hover:opacity-100 transition-opacity
                                bg-white/[0.04] pointer-events-none" />
                <div className={cn(
                  'relative flex items-center gap-2.5 px-3 py-2 text-13 font-medium transition-colors',
                  active ? 'text-accent-400' : 'text-dtxt2 group-hover:text-dtxt',
                )}>
                  <Icon size={14} strokeWidth={active ? 2 : 1.75} className="flex-shrink-0" />
                  {label}
                  {active && (
                    <motion.span
                      initial={{ scale: 0 }} animate={{ scale: 1 }}
                      className="ml-auto w-1 h-1 rounded-full bg-accent-400"
                    />
                  )}
                </div>
              </div>
            </NavLink>
          )
        })}
      </nav>

      <div className="px-3 pb-4">
        <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-white/[0.03] border border-dline">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inset-0 rounded-full bg-go animate-ping-slow opacity-60" />
            <span className="relative rounded-full h-1.5 w-1.5 bg-go" />
          </span>
          <span className="text-11 text-dtxt3">AI system operational</span>
        </div>
      </div>
    </aside>
  )
}
