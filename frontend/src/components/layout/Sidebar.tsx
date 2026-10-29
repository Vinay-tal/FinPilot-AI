import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  ArrowLeftRight,
  PieChart,
  Target,
  TrendingUp,
  Bot,
  AlertTriangle,
  Sliders,
  FileSpreadsheet,
  Settings,
  LogOut,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'

interface SidebarProps {
  onCloseMobile?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile }) => {
  const { user, logout, isDemoMode } = useAuth()

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Transactions', path: '/transactions', icon: ArrowLeftRight },
    { label: 'Budgets & Pacing', path: '/budgets', icon: PieChart },
    { label: 'Financial Goals', path: '/goals', icon: Target },
    { label: 'Cash Flow Forecast', path: '/forecasting', icon: TrendingUp },
    { label: 'AI Copilot', path: '/copilot', icon: Bot, badge: 'AI' },
    { label: 'Insights & Anomalies', path: '/insights', icon: AlertTriangle },
    { label: 'Scenario Simulator', path: '/simulation', icon: Sliders },
    { label: 'Reports & Export', path: '/reports', icon: FileSpreadsheet },
    { label: 'Settings', path: '/settings', icon: Settings },
  ]

  return (
    <aside className="w-64 h-screen bg-navy-900 border-r border-navy-800 flex flex-col shrink-0 select-none shadow-sidebar">
      {/* Brand Header */}
      <div className="p-5 border-b border-navy-800/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-teal-600 to-teal-400 flex items-center justify-center shadow-md shadow-teal-900/30">
            <Sparkles className="w-5 h-5 text-navy-950 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight leading-tight">FinPilot AI</h1>
            <p className="text-[10px] text-teal-300 font-medium tracking-wider uppercase">India Financial Advisor</p>
          </div>
        </div>
      </div>

      {/* Demo Persona Callout */}
      {isDemoMode && (
        <div className="mx-3.5 mt-3 px-3 py-2 bg-navy-850 border border-teal-900/50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-teal-300 uppercase tracking-wider">Demo Mode</span>
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
          </div>
          <p className="text-xs text-slate-300 font-medium truncate mt-0.5">Rahul Sharma (Bengaluru)</p>
          <p className="text-[11px] text-slate-400">₹1,25,000/mo salary • 350+ txs</p>
        </div>
      )}

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1 dark-scroll">
        <p className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Navigation
        </p>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all group',
                  isActive
                    ? 'bg-teal-600/15 text-teal-300 border-l-2 border-teal-400 font-semibold pl-2.5 shadow-xs'
                    : 'text-slate-300 hover:text-white hover:bg-navy-850'
                )
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-105" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-navy-800 bg-navy-950/40">
        <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-navy-850/60 border border-navy-800/80">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-navy-700 text-teal-300 border border-teal-500/30 flex items-center justify-center font-bold text-xs shrink-0">
              {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white truncate">{user?.full_name || 'User'}</p>
              <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-navy-800 rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
