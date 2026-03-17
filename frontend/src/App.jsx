import { Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { LayoutDashboard, History, Settings } from 'lucide-react'
import Home from './pages/Home'
import HistoryPage from './pages/History'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Sidebar */}
      <nav className="w-14 flex flex-col items-center py-4 gap-6 bg-gray-900 border-r border-gray-800 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm select-none">
          AI
        </div>
        <NavItem to="/" icon={<LayoutDashboard size={20} />} label="Build" />
        <NavItem to="/history" icon={<History size={20} />} label="History" />
        <div className="mt-auto">
          <NavItem to="/settings" icon={<Settings size={20} />} label="Settings" />
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1f2937',
            color: '#f9fafb',
            border: '1px solid #374151',
          },
        }}
      />
    </div>
  )
}

function NavItem({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={label}
      className={({ isActive }) =>
        `w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
          isActive
            ? 'bg-brand-500 text-white'
            : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
        }`
      }
    >
      {icon}
    </NavLink>
  )
}
