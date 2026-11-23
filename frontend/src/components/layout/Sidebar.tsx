import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  ArrowLeftRight,
  PieChart,
  Target,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  Sliders,
  FileSpreadsheet,
  Settings,
  LogOut,
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
    { label: 'Copilot', path: '/copilot', icon: MessageSquare },
    { label: 'Insights & Anomalies', path: '/insights', icon: AlertTriangle },
    { label: 'Scenario Simulator', path: '/simulation', icon: Sliders },
    { label: 'Reports & Export', path: '/reports', icon: FileSpreadsheet },
    { label: 'Settings', path: '/settings', icon: Settings },
  ]

  return (
    <aside className="w-64 h-screen bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 select-none shadow-sidebar">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-slate-200" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight leading-none">FinPilot</h1>
            <p className="text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-1">Financial Management</p>
          </div>
        </div>
      </div>

      {/* Demo Persona Callout */}
      {isDemoMode && (
        <div className="mx-3.5 mt-3 px-3 py-2 bg-slate-800/80 border border-slate-700/80 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider">Demo Account</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          </div>
          <p className="text-xs text-slate-200 font-medium truncate mt-0.5">Rahul Sharma</p>
          <p className="text-[10px] text-slate-400">Bengaluru • ₹1,25,000/mo salary</p>
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
                    ? 'bg-slate-800 text-white font-semibold pl-3 shadow-xs'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                )
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-105" />
                <span>{item.label}</span>
              </div>
            </NavLink>
          )
        })}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-900">
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-800/50 border border-slate-800">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-7 h-7 rounded-full bg-slate-700 text-slate-200 flex items-center justify-center font-bold text-xs shrink-0">
              {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || 'User'}</p>
              <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign Out"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}
