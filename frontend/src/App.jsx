import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Sidebar from './components/Sidebar'
import Overview      from './pages/Overview'
import Agent         from './pages/Agent'
import Conversations from './pages/Conversations'
import Evidence      from './pages/Evidence'
import Analytics     from './pages/Analytics'

export default function App() {
  const location = useLocation()
  return (
    <div className="flex h-screen bg-void overflow-hidden">
      <Sidebar />
      <main className="flex-1 min-w-0 overflow-y-auto dark-scroll">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/"              element={<Overview />} />
            <Route path="/agent"         element={<Agent />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/evidence"      element={<Evidence />} />
            <Route path="/analytics"     element={<Analytics />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  )
}
