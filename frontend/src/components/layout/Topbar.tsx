import React from 'react'
import { Menu } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '../common/Button'

interface TopbarProps {
  onToggleMobile: () => void
  pageTitle?: string
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleMobile, pageTitle }) => {
  const { isDemoMode, loginAsDemo } = useAuth()

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      {/* Left: Mobile trigger & Page title */}
      <div className="flex items-center space-x-3.5">
        <button
          onClick={onToggleMobile}
          className="lg:hidden p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
            {pageTitle || 'Financial Analytics'}
          </h2>
        </div>
      </div>

      {/* Right: Quick actions & status */}
      <div className="flex items-center space-x-3">
        {/* Status badge */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-600">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-medium text-[11px]">System Online</span>
        </div>

        {/* Currency badge */}
        <div className="hidden md:flex items-center space-x-1 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700">
          <span>₹ INR</span>
        </div>

        {/* Demo Switcher if logged in as empty user */}
        {!isDemoMode && (
          <Button
            onClick={loginAsDemo}
            size="sm"
            variant="outline"
            className="text-xs py-1"
          >
            Load Demo Account
          </Button>
        )}
      </div>
    </header>
  )
}
