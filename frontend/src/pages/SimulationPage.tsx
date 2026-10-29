import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Sliders,
  TrendingUp,
  TrendingDown,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  Calendar,
  Bookmark,
  FolderHeart,
  Target,
  AlertTriangle,
  Layers,
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import {
  runSimulationApi,
  listSavedScenariosApi,
  saveScenarioApi,
  deleteSavedScenarioApi,
} from '@/api/simulation'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { SaveScenarioModal } from '@/components/simulation/SaveScenarioModal'
import { SavedScenariosModal } from '@/components/simulation/SavedScenariosModal'
import { formatINR } from '@/lib/formatters'
import { useToast } from '@/context/ToastContext'
import { EnhancedSimulationParams, EnhancedSimulationResponse } from '@/types'

const DEFAULT_PARAMS: EnhancedSimulationParams = {
  salary_delta_pct: 0,
  rent_delta_inr: 0,
  discretionary_reduction_pct: 0,
  new_recurring_monthly_inr: 0,
  unexpected_expense_inr: 0,
  monthly_savings_delta_inr: 0,
  horizon_months: 12,
}

export const SimulationPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()

  const [params, setParams] = useState<EnhancedSimulationParams>(DEFAULT_PARAMS)
  const [debouncedParams, setDebouncedParams] = useState<EnhancedSimulationParams>(DEFAULT_PARAMS)
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false)
  const [isSavedListOpen, setIsSavedListOpen] = useState(false)

  // Debounce API calls for smooth slider dragging
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedParams(params)
    }, 250)
    return () => clearTimeout(timer)
  }, [params])

  // Simulation run query
  const {
    data: simulation,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<EnhancedSimulationResponse>({
    queryKey: ['simulation', debouncedParams],
    queryFn: () => runSimulationApi(debouncedParams),
    staleTime: 30000,
  })

  // Saved scenarios query
  const { data: savedScenarios = [], isLoading: isLoadingScenarios } = useQuery({
    queryKey: ['savedScenarios'],
    queryFn: listSavedScenariosApi,
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) =>
      saveScenarioApi(name, description, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedScenarios'] })
      toastSuccess('Scenario saved successfully!')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to save scenario')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSavedScenarioApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedScenarios'] })
      toastSuccess('Scenario removed')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to delete scenario')
    },
  })

  const updateParam = <K extends keyof EnhancedSimulationParams>(key: K, val: number) => {
    setParams((prev) => ({ ...prev, [key]: val }))
  }

  const applyPreset = (preset: Partial<EnhancedSimulationParams>) => {
    setParams({ ...DEFAULT_PARAMS, ...preset })
  }

  const resetAll = () => {
    setParams(DEFAULT_PARAMS)
  }

  const isSimulated =
    params.salary_delta_pct !== 0 ||
    params.rent_delta_inr !== 0 ||
    params.discretionary_reduction_pct !== 0 ||
    params.new_recurring_monthly_inr !== 0 ||
    params.unexpected_expense_inr !== 0 ||
    params.monthly_savings_delta_inr !== 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Scenario Simulator
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              Deterministic What-If Engine
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-0.5">
            Model multi-variable financial shifts without altering historical records. Test salary changes, rent hikes, discretionary cuts, and emergency buffer breaches.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSavedListOpen(true)}
            className="text-xs font-semibold"
          >
            <FolderHeart className="w-4 h-4 mr-1.5 text-slate-500" />
            Saved Scenarios ({savedScenarios.length})
          </Button>
          <Button
            size="sm"
            onClick={() => setIsSaveModalOpen(true)}
            className="text-xs font-semibold"
          >
            <Bookmark className="w-4 h-4 mr-1.5" />
            Save Scenario
          </Button>
          {isSimulated && (
            <Button variant="ghost" size="sm" onClick={resetAll} className="text-xs text-slate-500">
              <RotateCcw className="w-4 h-4 mr-1" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Preset Quick Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-500 font-semibold uppercase tracking-wider shrink-0 mr-1 flex items-center">
          <Sparkles className="w-3.5 h-3.5 mr-1 text-teal-600" /> Quick Presets:
        </span>
        <button
          onClick={() => applyPreset({ salary_delta_pct: 15 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          +15% Salary Hike
        </button>
        <button
          onClick={() => applyPreset({ rent_delta_inr: 8000 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          +₹8,000 Rent Hike
        </button>
        <button
          onClick={() => applyPreset({ new_recurring_monthly_inr: 15000 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          New Car Loan EMI (₹15k/mo)
        </button>
        <button
          onClick={() => applyPreset({ discretionary_reduction_pct: 20 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          Cut 20% Discretionary Spend
        </button>
        <button
          onClick={() => applyPreset({ unexpected_expense_inr: 50000 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          ₹50k Unexpected Emergency
        </button>
        <button
          onClick={() => applyPreset({ monthly_savings_delta_inr: 10000 })}
          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:border-teal-500 hover:text-teal-700 shrink-0 transition-colors shadow-xs"
        >
          +₹10,000/mo Goal Allocation
        </button>
      </div>

      {/* Main Grid: Controls + Outcomes */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Sliders and Controls (5 cols) */}
        <div className="lg:col-span-5 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900 flex items-center">
              <Sliders className="w-4 h-4 mr-2 text-teal-600" />
              Scenario Parameters
            </h2>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-500">Horizon:</span>
              <select
                value={params.horizon_months}
                onChange={(e) => updateParam('horizon_months', Number(e.target.value))}
                className="text-xs font-semibold border border-slate-200 rounded px-1.5 py-0.5 bg-slate-50 text-slate-700"
              >
                <option value={6}>6 Months</option>
                <option value={12}>12 Months</option>
                <option value={24}>24 Months</option>
              </select>
            </div>
          </div>

          {/* 1. Salary Delta */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">Salary Change</label>
              <span
                className={`font-bold font-mono text-xs px-2 py-0.5 rounded ${
                  params.salary_delta_pct > 0
                    ? 'bg-emerald-50 text-emerald-700'
                    : params.salary_delta_pct < 0
                    ? 'bg-rose-50 text-rose-700'
                    : 'bg-slate-100 text-slate-700'
                }`}
              >
                {params.salary_delta_pct > 0 ? `+${params.salary_delta_pct}%` : `${params.salary_delta_pct}%`}
              </span>
            </div>
            <input
              type="range"
              min="-30"
              max="50"
              step="5"
              value={params.salary_delta_pct}
              onChange={(e) => updateParam('salary_delta_pct', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>-30% (Pay Cut)</span>
              <span>Baseline</span>
              <span>+50% (Hike / Promotion)</span>
            </div>
          </div>

          {/* 2. Rent Delta */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">Rent Adjustment (Monthly)</label>
              <span
                className={`font-bold font-mono text-xs px-2 py-0.5 rounded ${
                  params.rent_delta_inr < 0
                    ? 'bg-emerald-50 text-emerald-700'
                    : params.rent_delta_inr > 0
                    ? 'bg-rose-50 text-rose-700'
                    : 'bg-slate-100 text-slate-700'
                }`}
              >
                {params.rent_delta_inr > 0 ? `+₹${params.rent_delta_inr.toLocaleString()}` : `₹${params.rent_delta_inr.toLocaleString()}`}
              </span>
            </div>
            <input
              type="range"
              min="-15000"
              max="25000"
              step="1000"
              value={params.rent_delta_inr}
              onChange={(e) => updateParam('rent_delta_inr', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>-₹15k (Downsize)</span>
              <span>Same Rent</span>
              <span>+₹25k (Relocation / Hike)</span>
            </div>
          </div>

          {/* 3. Discretionary Spending Cut */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">Reduced Discretionary Spending</label>
              <span className="font-bold font-mono text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-700">
                {params.discretionary_reduction_pct}% Cut
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={params.discretionary_reduction_pct}
              onChange={(e) => updateParam('discretionary_reduction_pct', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>0% (No change)</span>
              <span>25% Cut</span>
              <span>50% (High Frugality)</span>
            </div>
          </div>

          {/* 4. New Recurring Subscriptions / EMI */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">New Monthly Subscriptions / EMI</label>
              <span className="font-bold font-mono text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700">
                +₹{params.new_recurring_monthly_inr.toLocaleString()}/mo
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="40000"
              step="2000"
              value={params.new_recurring_monthly_inr}
              onChange={(e) => updateParam('new_recurring_monthly_inr', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>₹0</span>
              <span>₹20,000</span>
              <span>₹40,000 (Major EMI)</span>
            </div>
          </div>

          {/* 5. Unexpected Expense in Month 1 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">Unexpected Expense (Month 1)</label>
              <span
                className={`font-bold font-mono text-xs px-2 py-0.5 rounded ${
                  params.unexpected_expense_inr > 0 ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-700'
                }`}
              >
                ₹{params.unexpected_expense_inr.toLocaleString()}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="200000"
              step="10000"
              value={params.unexpected_expense_inr}
              onChange={(e) => updateParam('unexpected_expense_inr', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>₹0</span>
              <span>₹1,00,000</span>
              <span>₹2,00,000 (Emergency)</span>
            </div>
          </div>

          {/* 6. Monthly Savings Delta */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <label className="font-semibold text-slate-700">Monthly Savings Contribution Delta</label>
              <span
                className={`font-bold font-mono text-xs px-2 py-0.5 rounded ${
                  params.monthly_savings_delta_inr > 0
                    ? 'bg-teal-50 text-teal-700'
                    : params.monthly_savings_delta_inr < 0
                    ? 'bg-rose-50 text-rose-700'
                    : 'bg-slate-100 text-slate-700'
                }`}
              >
                {params.monthly_savings_delta_inr > 0 ? `+₹${params.monthly_savings_delta_inr.toLocaleString()}/mo` : `₹${params.monthly_savings_delta_inr.toLocaleString()}/mo`}
              </span>
            </div>
            <input
              type="range"
              min="-20000"
              max="30000"
              step="2500"
              value={params.monthly_savings_delta_inr}
              onChange={(e) => updateParam('monthly_savings_delta_inr', Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>-₹20k/mo</span>
              <span>₹0/mo</span>
              <span>+₹30k/mo (Aggressive)</span>
            </div>
          </div>
        </div>

        {/* Right Column: Outcomes, Alerts & Trajectory (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {isError ? (
            <ErrorAlert
              title="Simulation calculation failed"
              message={error instanceof Error ? error.message : 'Please check connection.'}
              onRetry={() => refetch()}
            />
          ) : isLoading || !simulation ? (
            <div className="space-y-4">
              <Skeleton className="h-28 w-full rounded-xl" />
              <Skeleton className="h-72 w-full rounded-xl" />
            </div>
          ) : (
            <>
              {/* Reserve Threshold Breach Warning Banner */}
              {simulation.has_reserve_breach ? (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3 shadow-xs animate-in fade-in">
                  <div className="p-2 bg-rose-100 rounded-lg text-rose-700 shrink-0 mt-0.5">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-rose-800">
                      Emergency Reserve Threshold Breach Warning
                    </h4>
                    <p className="text-xs text-rose-700 mt-1 leading-relaxed">
                      Under this scenario, your liquid reserves are projected to breach your minimum safety floor of{' '}
                      <strong>{formatINR(simulation.emergency_reserve_floor_inr)}</strong> starting in{' '}
                      <span className="font-bold underline">{simulation.first_breach_month}</span>. Lowest projected balance drops to{' '}
                      <strong>{formatINR(simulation.min_projected_balance_inr)}</strong>.
                    </p>
                    <p className="text-2xs text-rose-600 mt-1.5 font-medium">
                      Suggestion: Rebalance discretionary spending or reduce new recurring commitments to preserve emergency coverage.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-100 text-teal-900 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-teal-600" />
                    <span>
                      Emergency Reserve Floor: <strong>{formatINR(simulation.emergency_reserve_floor_inr)}</strong> is safely preserved across {params.horizon_months} months.
                    </span>
                  </div>
                  <span className="text-teal-700 font-semibold font-mono text-2xs">
                    Min Balance: {formatINR(simulation.min_projected_balance_inr)}
                  </span>
                </div>
              )}

              {/* Monthly Cashflow KPI Row */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3.5">
                <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Baseline Cashflow</p>
                  <p className="text-lg sm:text-xl font-bold text-slate-900 mt-1">
                    {formatINR(simulation.baseline_monthly_savings_inr)}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Inc: {formatINR(simulation.baseline_monthly_income_inr)} | Exp: {formatINR(simulation.baseline_monthly_expense_inr)}
                  </p>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Simulated Cashflow</p>
                  <p className="text-lg sm:text-xl font-bold text-teal-700 mt-1">
                    {formatINR(simulation.simulated_monthly_savings_inr)}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Inc: {formatINR(simulation.simulated_monthly_income_inr)} | Exp: {formatINR(simulation.simulated_monthly_expense_inr)}
                  </p>
                </div>

                <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs col-span-2 sm:col-span-1">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Monthly Delta</p>
                  <p
                    className={`text-lg sm:text-xl font-bold mt-1 flex items-center ${
                      simulation.net_monthly_differential_inr >= 0 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {simulation.net_monthly_differential_inr >= 0 ? (
                      <TrendingUp className="w-5 h-5 mr-1" />
                    ) : (
                      <TrendingDown className="w-5 h-5 mr-1" />
                    )}
                    {formatINR(simulation.net_monthly_differential_inr)}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Per-month difference</p>
                </div>
              </div>

              {/* Annual Net Impact Banner */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-navy-900 to-navy-850 text-white flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
                <div>
                  <p className="text-xs font-medium text-teal-300 uppercase tracking-wider">
                    {params.horizon_months}-Month Cumulative Wealth Impact
                  </p>
                  <p className="text-2xl font-bold mt-0.5">
                    {simulation.annual_savings_impact_inr >= 0 ? '+' : ''}
                    {formatINR(simulation.annual_savings_impact_inr)}
                  </p>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Cumulative delta in your total liquid portfolio over the horizon
                  </p>
                </div>
                <div className="bg-navy-800/80 px-4 py-2.5 rounded-lg border border-navy-700 text-right shrink-0">
                  <p className="text-[11px] text-slate-400 uppercase tracking-wider">Lowest Balance</p>
                  <p
                    className={`text-lg font-bold ${
                      simulation.min_projected_balance_inr < simulation.emergency_reserve_floor_inr
                        ? 'text-rose-400'
                        : 'text-emerald-400'
                    }`}
                  >
                    {formatINR(simulation.min_projected_balance_inr)}
                  </p>
                </div>
              </div>

              {/* Trajectory Area Chart */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Projected Balance Trajectory ({params.horizon_months} Months)
                    </h3>
                    <p className="text-xs text-slate-500">
                      Baseline path vs simulated trajectory with safety floor
                    </p>
                  </div>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={simulation.trajectory}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="simGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0D9488" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#0D9488" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#64748B" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#64748B" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                      <XAxis dataKey="month_label" tick={{ fontSize: 11, fill: '#64748B' }} />
                      <YAxis
                        tick={{ fontSize: 11, fill: '#64748B' }}
                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        formatter={(val: any, name: any) => [
                          formatINR(Number(val) || 0),
                          name === 'cumulative_simulated_balance_inr'
                            ? 'Simulated Balance'
                            : 'Baseline Balance',
                        ]}
                        contentStyle={{
                          backgroundColor: '#0F172A',
                          border: 'none',
                          borderRadius: '8px',
                          color: '#F8FAFC',
                          fontSize: '12px',
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        align="right"
                        iconType="circle"
                        wrapperStyle={{ fontSize: 12 }}
                      />
                      <ReferenceLine
                        y={simulation.emergency_reserve_floor_inr}
                        stroke="#EF4444"
                        strokeDasharray="4 4"
                        label={{
                          value: 'Reserve Floor',
                          fill: '#EF4444',
                          fontSize: 10,
                          position: 'insideTopLeft',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="cumulative_baseline_balance_inr"
                        name="Baseline Balance"
                        stroke="#64748B"
                        strokeDasharray="4 4"
                        fill="url(#baseGrad)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="cumulative_simulated_balance_inr"
                        name="Simulated Balance"
                        stroke="#0D9488"
                        fill="url(#simGrad)"
                        strokeWidth={2.5}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Goal Completion Impacts Table */}
              <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Target className="w-4 h-4 text-teal-600" />
                    <h3 className="text-sm font-bold text-slate-900">Savings Goal Completion Impacts</h3>
                  </div>
                  <span className="text-2xs text-slate-400 font-medium">Deterministic Timeline Model</span>
                </div>

                {simulation.goal_impacts.length === 0 ? (
                  <p className="text-xs text-slate-500 py-3 text-center">
                    No active savings goals found to evaluate. Create a goal in the Goals module.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-100 text-slate-400 uppercase text-2xs tracking-wider">
                          <th className="pb-2 font-semibold">Goal Name</th>
                          <th className="pb-2 font-semibold">Baseline Date</th>
                          <th className="pb-2 font-semibold">Simulated Date</th>
                          <th className="pb-2 font-semibold">Timeline Variance</th>
                          <th className="pb-2 font-semibold text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {simulation.goal_impacts.map((g) => (
                          <tr key={g.goal_id} className="hover:bg-slate-50/50">
                            <td className="py-2.5 font-semibold text-slate-900">{g.goal_name}</td>
                            <td className="py-2.5 text-slate-600 font-mono text-2xs">{g.original_completion_date}</td>
                            <td className="py-2.5 text-slate-900 font-semibold font-mono text-2xs">{g.simulated_completion_date}</td>
                            <td className="py-2.5">
                              {g.variance_months > 0 ? (
                                <span className="font-semibold text-emerald-600">
                                  {g.variance_months} mo faster
                                </span>
                              ) : g.variance_months < 0 ? (
                                <span className="font-semibold text-rose-600">
                                  {Math.abs(g.variance_months)} mo delayed
                                </span>
                              ) : (
                                <span className="text-slate-500 font-medium">No change</span>
                              )}
                            </td>
                            <td className="py-2.5 text-right">
                              <span
                                className={`px-2 py-0.5 rounded text-2xs font-semibold ${
                                  g.status_change === 'ACCELERATED'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : g.status_change === 'DELAYED'
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                    : 'bg-slate-100 text-slate-700'
                                }`}
                              >
                                {g.status_change}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Save Scenario Modal */}
      <SaveScenarioModal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
        onSave={async (name, description) => {
          await saveMutation.mutateAsync({ name, description })
        }}
        isSaving={saveMutation.isPending}
        params={params}
      />

      {/* Saved Scenarios List Modal */}
      <SavedScenariosModal
        isOpen={isSavedListOpen}
        onClose={() => setIsSavedListOpen(false)}
        scenarios={savedScenarios}
        isLoading={isLoadingScenarios}
        onLoadScenario={(loadedParams) => {
          setParams(loadedParams)
          toastSuccess('Loaded scenario parameters')
        }}
        onDeleteScenario={(id) => {
          if (window.confirm('Delete this saved scenario?')) {
            deleteMutation.mutate(id)
          }
        }}
      />
    </div>
  )
}
