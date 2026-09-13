import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Sidebar from './components/Sidebar'
import Overview      from './pages/Overview'
import Agent         from './pages/Agent'
import Conversations from './pages/Conversations'
import Evidence      from './pages/Evidence'
import Analytics     from './pages/Analytics'
import CustomerPortal from './pages/CustomerPortal'
import AdminPortal from './pages/AdminPortal'

export default function App() {
  const location = useLocation()
  const isCustomerPortal = location.pathname === '/portal' || location.pathname === '/customer-portal'
  const isAdminPortal = location.pathname === '/admin'

  if (isCustomerPortal || isAdminPortal) {
    return (
      <Routes location={location} key={location.pathname}>
        <Route path="/portal" element={<CustomerPortal />} />
        <Route path="/customer-portal" element={<CustomerPortal />} />
        <Route path="/admin" element={<AdminPortal />} />
      </Routes>
    )
  }

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
            <Route path="/portal"        element={<CustomerPortal />} />
            <Route path="/customer-portal" element={<CustomerPortal />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  )
}
