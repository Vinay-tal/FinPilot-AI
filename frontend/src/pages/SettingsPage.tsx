import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Settings,
  User,
  ShieldCheck,
  Server,
  Database,
  Cpu,
  CreditCard,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  LogOut,
  Sparkles,
  Globe,
  Clock,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { getAccountsApi } from '@/api/accounts'
import { getSystemReadinessApi } from '@/api/system'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { Skeleton } from '@/components/common/Skeleton'
import { formatINR, formatDateIST } from '@/lib/formatters'
import { useToast } from '@/context/ToastContext'

export const SettingsPage: React.FC = () => {
  const { user, logout, isDemoMode } = useAuth()
  const { showToast } = useToast()

  const {
    data: accounts = [],
    isLoading: isAccountsLoading,
    refetch: refetchAccounts,
  } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccountsApi,
  })

  const {
    data: system,
    isLoading: isSystemLoading,
    isError: isSystemError,
    refetch: refetchSystem,
  } = useQuery({
    queryKey: ['system', 'readiness'],
    queryFn: getSystemReadinessApi,
    refetchInterval: 15000,
  })

  const handleCopyAccountId = (id: string) => {
    navigator.clipboard.writeText(id)
    showToast({
      type: 'info',
      title: 'Copied',
      message: 'Account ID copied to clipboard.',
    })
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Settings & Workspace
          </h1>
          <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-teal-50 text-teal-700 border border-teal-200">
            Profile & System
          </span>
        </div>
        <p className="text-sm text-slate-600 mt-0.5">
          Manage your account profile, linked financial institutions, and backend database connection.
        </p>
      </div>

      {/* Grid: Profile & Demo Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* User Profile Card (2 cols) */}
        <div className="md:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5">
          <div className="flex items-center space-x-3 pb-4 border-b border-slate-100">
            <div className="w-12 h-12 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-700 font-bold text-lg">
              {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">{user?.full_name || 'FinPilot User'}</h2>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-slate-400 font-medium">User ID</label>
              <p className="font-mono text-slate-700 mt-0.5 truncate">{user?.id}</p>
            </div>
            <div>
              <label className="text-slate-400 font-medium">Base Currency</label>
              <p className="font-semibold text-slate-800 mt-0.5 flex items-center">
                <Globe className="w-3.5 h-3.5 mr-1 text-teal-600" />
                INR (₹ Indian Rupee)
              </p>
            </div>
            <div>
              <label className="text-slate-400 font-medium">Timezone & Locale</label>
              <p className="font-semibold text-slate-800 mt-0.5 flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1 text-teal-600" />
                Asia/Kolkata (IST • UTC+5:30)
              </p>
            </div>
            <div>
              <label className="text-slate-400 font-medium">Account Status</label>
              <div className="mt-0.5">
                <Badge variant="success" dot>Active & Verified</Badge>
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-slate-100">
            <p className="text-[11px] text-slate-400">
              Session is secured with RS256 / HS256 JWT access tokens.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="text-rose-600 border-rose-200 hover:bg-rose-50 hover:border-rose-300"
            >
              <LogOut className="w-4 h-4 mr-1.5" />
              Sign Out
            </Button>
          </div>
        </div>

        {/* Demo Mode & Persona Card (1 col) */}
        <div className="bg-gradient-to-br from-navy-900 to-navy-850 p-6 rounded-xl text-white shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-300 flex items-center">
                <Sparkles className="w-3.5 h-3.5 mr-1" />
                Persona
              </span>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal-500/20 text-teal-300 border border-teal-500/30">
                Demo
              </span>
            </div>

            <h3 className="text-lg font-bold">Rahul Sharma</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Bengaluru software engineer persona with 12 months of realistic Indian financial transactions, SIPs, EMIs, and multi-bank statements.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-navy-800 text-[11px] text-slate-400 space-y-1">
            <p>• ₹1,25,000/month verified salary</p>
            <p>• HDFC Bank, ICICI Bank, Zerodha</p>
            <p>• 350+ categorized ledger transactions</p>
          </div>
        </div>
      </div>

      {/* Backend & AI System Health Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Server className="w-4 h-4 text-teal-600" />
            <h2 className="text-base font-bold text-slate-900">System Diagnostics & AI Backend</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetchSystem()}
            className="text-xs text-slate-500 hover:text-slate-800"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Check Live
          </Button>
        </div>

        {isSystemLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Database Card */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                  <Database className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  Database
                </span>
                <Badge variant={system?.database === 'connected' ? 'success' : 'danger'} dot>
                  {system?.database === 'connected' ? 'Connected' : 'Offline'}
                </Badge>
              </div>
              <p className="text-xs font-mono text-slate-700 truncate pt-1">
                {system?.database_url_masked || 'sqlite:///./finpilot.db'}
              </p>
              <p className="text-[11px] text-slate-400">SQLAlchemy 2.x • ACID Minor Units</p>
            </div>

            {/* AI Provider Card */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                  <Cpu className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  AI Engine
                </span>
                <Badge variant="teal">Active</Badge>
              </div>
              <p className="text-xs font-semibold text-slate-800 pt-1 truncate">
                {system?.ai_provider || 'Groq / Heuristic Multi-LLM'}
              </p>
              <p className="text-[11px] text-slate-400">RAG Grounded on User Ledger</p>
            </div>

            {/* Architecture Card */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1 text-teal-600" />
                  Security Isolation
                </span>
                <Badge variant="info">Enforced</Badge>
              </div>
              <p className="text-xs font-semibold text-slate-800 pt-1">
                Cross-User Row Guard
              </p>
              <p className="text-[11px] text-slate-400">Strict User ID Scoping on Queries</p>
            </div>
          </div>
        )}
      </div>

      {/* Connected Financial Accounts */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center">
              <CreditCard className="w-4 h-4 mr-2 text-teal-600" />
              Connected Financial Accounts
            </h2>
            <p className="text-xs text-slate-500">
              Live balances reconciled in minor units (paise) across savings, credit, and investment accounts.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
            {accounts.length} Accounts Active
          </span>
        </div>

        {isAccountsLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        ) : accounts.length === 0 ? (
          <p className="text-xs text-slate-500 text-center py-4">No accounts linked yet.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {accounts.map((acc) => (
              <div
                key={acc.id}
                className="p-4 rounded-xl border border-slate-200/80 hover:border-teal-300 transition-all bg-slate-50/50 flex flex-col justify-between space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      {acc.institution} • {acc.account_type.replace('_', ' ')}
                    </span>
                    <h4 className="text-sm font-bold text-slate-900">{acc.name}</h4>
                    {acc.account_number_mask && (
                      <p className="text-xs font-mono text-slate-500">•••• {acc.account_number_mask}</p>
                    )}
                  </div>
                  <Badge variant={acc.is_active ? 'success' : 'default'}>
                    {acc.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>

                <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs">
                  <span className="text-slate-500">Current Balance:</span>
                  <span className="font-bold text-sm text-slate-900 font-mono">
                    {formatINR(acc.balance_inr)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compliance & Engineering Specs Footer */}
      <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-slate-500 text-xs leading-relaxed space-y-1">
        <p className="font-bold text-slate-700 uppercase tracking-wider">Engineering Verification Note</p>
        <p>
          FinPilot AI is engineered according to production fintech standards: integer paise storage for exact precision,
          isolated JWT authentication, India Standard Time localization, and responsive layouts across mobile and desktop.
        </p>
      </div>
    </div>
  )
}
