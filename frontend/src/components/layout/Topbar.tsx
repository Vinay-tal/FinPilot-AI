import React from 'react'
import { Menu, Sparkles, Activity, ShieldCheck } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '../common/Button'

interface TopbarProps {
  onToggleMobile: () => void
  pageTitle?: string
}

export const Topbar: React.FC<TopbarProps> = ({ onToggleMobile, pageTitle }) => {
  const { isDemoMode, loginAsDemo } = useAuth()

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
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
        {/* API Health badge */}
        <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-600">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-medium text-[11px]">Backend Live</span>
        </div>

        {/* Currency badge */}
        <div className="hidden md:flex items-center space-x-1 px-2.5 py-1 rounded-md bg-teal-50 border border-teal-200 text-xs font-semibold text-teal-800">
          <span>₹ INR</span>
        </div>

        {/* 1-Click Demo Switcher if logged in as empty user */}
        {!isDemoMode && (
          <Button
            onClick={loginAsDemo}
            size="sm"
            variant="outline"
            icon={<Sparkles className="w-3.5 h-3.5 text-teal-600" />}
            className="border-teal-300 text-teal-800 hover:bg-teal-50 text-xs py-1"
          >
            Load Rahul Sharma Demo
          </Button>
        )}
      </div>
    </header>
  )
}
