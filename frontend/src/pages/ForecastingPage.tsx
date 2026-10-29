import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Calendar,
  ShieldCheck,
  ShieldAlert,
  Info,
  Clock,
  Sparkles,
  CheckCircle2,
  HelpCircle,
  Activity,
  Layers,
  Cpu,
  Zap,
  Save,
  RefreshCw,
  ArrowRight,
  Shield,
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import {
  getForecastApi,
  generateAndSaveForecastApi,
  getCategoryForecastsApi,
  getForecastEvaluationApi,
  simulateStressScenarioApi,
} from '@/api/forecasting'
import { formatINR, formatDate } from '@/lib/formatters'
import { StatCard } from '@/components/common/StatCard'
import { CardSkeleton } from '@/components/common/Skeleton'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { useToast } from '@/context/ToastContext'

export const ForecastingPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()

  const [horizon, setHorizon] = useState<number>(30)
  const [modelType, setModelType] = useState<'auto' | 'ridge' | 'baseline'>('auto')
  const [reserveThreshold, setReserveThreshold] = useState<number>(10000)
  const [activeTab, setActiveTab] = useState<
    'explainability' | 'categories' | 'evaluation' | 'stress_test'
  >('explainability')

  // Stress test simulator state
  const [activeScenario, setActiveScenario] = useState<
    'SALARY_DELAY' | 'EMERGENCY_EXPENSE' | 'SPENDING_SURGE'
  >('SALARY_DELAY')
  const [delayDays, setDelayDays] = useState<number>(7)
  const [emergencyExpenseInr, setEmergencyExpenseInr] = useState<number>(25000)
  const [spendSurgePct, setSpendSurgePct] = useState<number>(40)

  // 1. Forecast query
  const {
    data: forecast,
    isLoading: isForecastLoading,
    error: forecastError,
    refetch: refetchForecast,
  } = useQuery({
    queryKey: ['forecasting', horizon, modelType, reserveThreshold],
    queryFn: () =>
      getForecastApi({
        days: horizon,
        model_type: modelType,
        reserve_threshold_inr: reserveThreshold,
      }),
  })

  // 2. Categories query
  const { data: categoryForecasts = [], isLoading: isCategoriesLoading } = useQuery({
    queryKey: ['forecasting-categories'],
    queryFn: getCategoryForecastsApi,
  })

  // 3. Model evaluation query
  const { data: evaluation, isLoading: isEvalLoading, refetch: refetchEval } = useQuery({
    queryKey: ['forecasting-evaluation'],
    queryFn: getForecastEvaluationApi,
  })

  // 4. Stress testing mutation / query
  const {
    data: stressResult,
    mutate: runStressTest,
    isPending: isStressLoading,
  } = useMutation({
    mutationFn: () =>
      simulateStressScenarioApi({
        scenario_type: activeScenario,
        horizon_days: horizon,
        delay_days: delayDays,
        expense_amount_inr: emergencyExpenseInr,
        spend_surge_pct: spendSurgePct,
      }),
  })

  // 5. Persist mutation
  const persistMutation = useMutation({
    mutationFn: () =>
      generateAndSaveForecastApi({
        days: horizon,
        model_type: modelType,
        reserve_threshold_inr: reserveThreshold,
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['forecasting'] })
      toastSuccess(`Forecast snapshot persisted to database! Model: ${res.model_version}`)
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to persist forecast.')
    },
  })

  // Prepare unified time series for chart (combining 14-day history + forward forecast)
  const chartData = React.useMemo(() => {
    if (!forecast) return []
    const hist = (forecast.historical_points || []).map((h) => ({
      date: h.date,
      display_date: h.display_date,
      balance_inr: h.balance_inr,
      is_historical: true,
    }))
    const future = (forecast.forecast_points || []).map((f) => ({
      date: f.date,
      display_date: f.display_date || f.date,
      balance_inr: f.balance_inr,
      lower_bound_inr: f.lower_bound_inr,
      upper_bound_inr: f.upper_bound_inr,
      lower_bound_95_inr: f.lower_bound_95_inr,
      upper_bound_95_inr: f.upper_bound_95_inr,
      event_name: f.event_name,
      is_historical: false,
    }))
    return [...hist, ...future]
  }, [forecast])

  return (
    <div className="space-y-6">
      {/* Top Banner and Interactive Control Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Financial Forecasting & Risk Analysis Engine
            </h1>
            <Badge variant="teal">Milestone 4</Badge>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Statistical & ML cash flow projections with calendar regressors, uncertainty bands, and shortfall risk calibration
          </p>
        </div>

        {/* Controls: Horizon & Model & Save */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          {/* Model Selector */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1">
            <Cpu className="w-3.5 h-3.5 text-indigo-600" />
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value as any)}
              className="bg-transparent text-slate-800 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="auto">Auto (Best Walk-Forward Fit)</option>
              <option value="ridge">Ridge ML (Calendar Regressors)</option>
              <option value="baseline">Burn Rate Baseline + DOW</option>
            </select>
          </div>

          {/* Horizon Selector */}
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5 bg-slate-50 font-semibold">
            {[30, 60, 90].map((days) => (
              <button
                key={days}
                onClick={() => setHorizon(days)}
                className={`px-3 py-1 rounded-md transition-all ${
                  horizon === days
                    ? 'bg-navy-900 text-white shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {days}d
              </button>
            ))}
          </div>

          {/* Snapshot Persist Action */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => persistMutation.mutate()}
            isLoading={persistMutation.isPending}
            title="Persist forecast points to database"
          >
            <Save className="w-3.5 h-3.5 mr-1 text-teal-600" />
            Save Snapshot
          </Button>
        </div>
      </div>

      {/* KPI Cards Strip */}
      {isForecastLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : forecast ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Current Verified Balance"
            value={formatINR(forecast.current_balance_inr)}
            subtitle="Combined liquid accounts"
            accentColor="teal"
          />
          <StatCard
            title={`Projected ${horizon}-Day Balance`}
            value={formatINR(forecast.projected_end_balance_inr)}
            change={{
              value: formatINR(forecast.net_projected_change_inr, { showSign: true }),
              isPositive: forecast.net_projected_change_inr >= 0,
            }}
            accentColor="indigo"
          />
          <StatCard
            title="Minimum Dip Point"
            value={formatINR(forecast.min_projected_balance_inr)}
            subtitle={`Reserve Target: ${formatINR(forecast.risk_analysis?.reserve_threshold_inr || reserveThreshold)}`}
            accentColor={
              forecast.min_projected_balance_inr < reserveThreshold ? 'rose' : 'emerald'
            }
          />
          <StatCard
            title="Shortfall Risk Probability"
            value={
              forecast.risk_analysis?.probability_calibrated
                ? `${forecast.risk_analysis.shortfall_probability_pct}%`
                : forecast.risk_analysis?.risk_level || 'SAFE'
            }
            subtitle={
              forecast.shortfall_detected
                ? `Breach expected on ${forecast.shortfall_date}`
                : 'Liquid buffer remains secure'
            }
            accentColor={forecast.shortfall_detected ? 'rose' : 'emerald'}
          />
        </div>
      ) : null}

      {/* Shortfall Risk Alert Banner if detected */}
      {forecast?.shortfall_detected && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start space-x-3.5 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-rose-950 flex items-center gap-2">
              Potential Liquidity Shortfall Warning
              <Badge variant="danger">
                {forecast.risk_analysis?.risk_level}
              </Badge>
            </h4>
            <p className="text-xs text-rose-800 leading-relaxed">
              Based on scheduled commitments and current spending velocity, your liquid balance is projected
              to drop below your safety buffer of {formatINR(reserveThreshold)} on{' '}
              <strong>{forecast.shortfall_date}</strong> (buffer deficit of{' '}
              <strong>{formatINR(forecast.risk_analysis?.buffer_deficit_inr || 0)}</strong>).
              Consider postponing non-essential expenses or transferring reserve funds before this date.
            </p>
          </div>
        </div>
      )}

      {/* Main Trajectory Chart with Uncertainty Fan */}
      <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-600" />
              Cash-Flow Trajectory & Conformal Uncertainty Fan
            </h3>
            <p className="text-xs text-slate-500">
              Shaded fan represents 80% and 95% confidence bounds based on residual volatility; dotted marker denotes safety reserve threshold
            </p>
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-3 h-0.5 bg-teal-600 rounded" />
              <span>Projected Balance</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-600">
              <span className="w-3 h-2 bg-teal-500/20 rounded border border-teal-500/40" />
              <span>80% Range</span>
            </div>
            <div className="flex items-center gap-1.5 text-rose-600 font-semibold">
              <span className="w-3 h-0.5 bg-rose-500 rounded border-dashed" />
              <span>₹10k Reserve</span>
            </div>
          </div>
        </div>

        {forecastError ? (
          <ErrorAlert
            title="Error generating forecast"
            message={(forecastError as Error).message}
            onRetry={() => refetchForecast()}
          />
        ) : isForecastLoading ? (
          <div className="h-80 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
          </div>
        ) : forecast ? (
          <div className="h-80 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="uncertaintyGradient80" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="display_date"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const pt = payload[0].payload
                      return (
                        <div className="bg-navy-900 text-white p-3 rounded-xl shadow-xl text-xs space-y-1.5 border border-navy-700 min-w-52">
                          <p className="font-bold text-slate-200 border-b border-navy-800 pb-1">
                            {pt.display_date} {pt.is_historical ? '(Historical Verified)' : ''}
                          </p>
                          <div className="flex justify-between items-center text-teal-300 font-bold">
                            <span>Balance:</span>
                            <span className="font-mono">{formatINR(pt.balance_inr)}</span>
                          </div>
                          {!pt.is_historical && pt.lower_bound_inr != null && (
                            <div className="flex justify-between items-center text-slate-300 text-[11px]">
                              <span>80% CI:</span>
                              <span className="font-mono">
                                {formatINR(pt.lower_bound_inr, { hideDecimals: true })} -{' '}
                                {formatINR(pt.upper_bound_inr, { hideDecimals: true })}
                              </span>
                            </div>
                          )}
                          {pt.event_name && (
                            <div className="mt-1 pt-1 border-t border-navy-800 text-amber-300 text-[11px] font-semibold">
                              &bull; {pt.event_name}
                            </div>
                          )}
                        </div>
                      )
                    }
                    return null
                  }}
                />
                {/* Safety Reserve Threshold Reference Line */}
                <ReferenceLine
                  y={reserveThreshold}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                />
                {/* 80% Uncertainty Band */}
                <Area
                  type="monotone"
                  dataKey="upper_bound_inr"
                  stroke="transparent"
                  fill="url(#uncertaintyGradient80)"
                />
                <Area
                  type="monotone"
                  dataKey="lower_bound_inr"
                  stroke="transparent"
                  fill="#ffffff"
                />
                {/* Projected Line */}
                <Line
                  type="monotone"
                  dataKey="balance_inr"
                  name="Projected Balance"
                  stroke="#0d9488"
                  strokeWidth={2.5}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </div>

      {/* Milestone 4 Deep-Dive Navigation Tabs */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 p-1.5 bg-slate-100 rounded-xl border border-slate-200">
          <button
            onClick={() => setActiveTab('explainability')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'explainability'
                ? 'bg-white text-navy-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            Explainability & Drivers
          </button>

          <button
            onClick={() => setActiveTab('categories')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'categories'
                ? 'bg-white text-navy-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-indigo-600" />
            Category-Level Projections ({categoryForecasts.length})
          </button>

          <button
            onClick={() => setActiveTab('evaluation')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'evaluation'
                ? 'bg-white text-navy-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 text-sky-600" />
            Model Benchmark & Temporal CV
          </button>

          <button
            onClick={() => {
              setActiveTab('stress_test')
              if (!stressResult) runStressTest()
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'stress_test'
                ? 'bg-white text-navy-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-amber-600" />
            Stress-Test Simulator
          </button>
        </div>

        {/* Tab 1: Explainability & Attribution */}
        {activeTab === 'explainability' && forecast?.explanation && (
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-5">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Forecast Explainability & Factor Attribution
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {forecast.explanation.summary_narrative}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Observed Facts */}
              <div className="p-4 bg-emerald-50/60 rounded-xl border border-emerald-200/80 space-y-2.5">
                <h4 className="text-xs font-bold text-emerald-950 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Observed Facts (Empirical Data)
                </h4>
                <ul className="space-y-1.5 text-xs text-emerald-900">
                  {forecast.explanation.observed_facts.map((fact, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{fact}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Modeling Assumptions */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-indigo-600" />
                  Modeling Assumptions
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-700">
                  {forecast.explanation.assumptions.map((assump, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-slate-400 font-bold">•</span>
                      <span>{assump}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Drivers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Positive Drivers */}
              <div className="border border-slate-200 rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                  Primary Inflow & Cushion Drivers
                </h4>
                <div className="space-y-2">
                  {forecast.explanation.positive_drivers.map((drv, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg text-xs"
                    >
                      <div>
                        <p className="font-semibold text-slate-900">{drv.factor}</p>
                        <p className="text-[11px] text-slate-500">{drv.description}</p>
                      </div>
                      <span className="font-bold text-emerald-600 font-mono">
                        +{formatINR(drv.impact_inr)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Negative Drivers */}
              <div className="border border-slate-200 rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-rose-600" />
                  Outflow & Burn Pressure Drivers
                </h4>
                <div className="space-y-2">
                  {forecast.explanation.negative_drivers.map((drv, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg text-xs"
                    >
                      <div>
                        <p className="font-semibold text-slate-900">{drv.factor}</p>
                        <p className="text-[11px] text-slate-500">{drv.description}</p>
                      </div>
                      <span className="font-bold text-rose-600 font-mono">
                        {formatINR(drv.impact_inr)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Category-Level Projections */}
        {activeTab === 'categories' && (
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Month-End Category Expense Projections
                </h3>
                <p className="text-xs text-slate-500">
                  Combines current MTD spend with empirical Bayes shrinkage against 90-day historical run-rates
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3">Category</th>
                    <th className="p-3 text-right">Spent MTD</th>
                    <th className="p-3 text-right">Daily Run-Rate</th>
                    <th className="p-3 text-right">Remaining Forecast</th>
                    <th className="p-3 text-right font-bold">Month-End Total</th>
                    <th className="p-3 text-center">Pacing Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {categoryForecasts.map((cat) => (
                    <tr key={cat.category_id} className="hover:bg-slate-50">
                      <td className="p-3 font-semibold text-slate-900 flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: cat.category_color || '#94a3b8' }}
                        />
                        {cat.category_name}
                      </td>
                      <td className="p-3 text-right font-mono text-slate-700">
                        {formatINR(cat.current_spent_inr)}
                      </td>
                      <td className="p-3 text-right font-mono text-slate-500">
                        {formatINR(cat.daily_run_rate_inr)}/d
                      </td>
                      <td className="p-3 text-right font-mono text-slate-600">
                        {formatINR(cat.projected_remaining_inr)}
                      </td>
                      <td className="p-3 text-right font-mono font-bold text-slate-900">
                        {formatINR(cat.projected_month_end_inr)}
                      </td>
                      <td className="p-3 text-center">
                        <Badge
                          variant={
                            cat.pacing_status === 'ELEVATED'
                              ? 'danger'
                              : cat.pacing_status === 'UNDER_PACING'
                              ? 'teal'
                              : 'success'
                          }
                        >
                          {cat.pacing_status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Model Benchmark & Temporal Evaluation */}
        {activeTab === 'evaluation' && (
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Walk-Forward Temporal Cross-Validation
                </h3>
                <p className="text-xs text-slate-500">
                  Strictly avoids future data leakage by evaluating rolling test horizons against past training splits
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetchEval()}>
                <RefreshCw className="w-3.5 h-3.5 mr-1" /> Re-evaluate
              </Button>
            </div>

            {isEvalLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">Running temporal cross validation...</div>
            ) : evaluation && evaluation.status === 'SUCCESS' ? (
              <div className="space-y-4">
                {/* Metric Comparison Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">
                      Baseline Model (Burn Rate)
                    </span>
                    <p className="text-xl font-bold text-slate-800 mt-1 font-mono">
                      MAE: {formatINR(evaluation.baseline.mae_inr)}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      RMSE: {formatINR(evaluation.baseline.rmse_inr)}
                    </p>
                  </div>

                  <div className="p-4 bg-teal-50/70 rounded-xl border border-teal-200">
                    <span className="text-[11px] font-semibold text-teal-800 uppercase">
                      Advanced Model (Ridge ML)
                    </span>
                    <p className="text-xl font-bold text-teal-900 mt-1 font-mono">
                      MAE: {formatINR(evaluation.advanced_model.mae_inr)}
                    </p>
                    <p className="text-[11px] text-teal-700 mt-0.5">
                      RMSE: {formatINR(evaluation.advanced_model.rmse_inr)}
                    </p>
                  </div>

                  <div className="p-4 bg-indigo-50/70 rounded-xl border border-indigo-200">
                    <span className="text-[11px] font-semibold text-indigo-800 uppercase">
                      Recommended Selection
                    </span>
                    <p className="text-lg font-bold text-indigo-950 mt-1 capitalize">
                      {evaluation.recommended_model.replace(/_/g, ' ')}
                    </p>
                    <p className="text-[11px] text-indigo-700 mt-0.5 font-semibold">
                      {evaluation.improvement_pct >= 0 ? `+${evaluation.improvement_pct}%` : `${evaluation.improvement_pct}%`} error delta vs baseline
                    </p>
                  </div>
                </div>

                {/* Abstention & Limitations Note */}
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1.5">
                  <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-teal-600" />
                    Model Abstention Policy & Theoretical Limitations
                  </h5>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Personal finance series exhibit extreme sparsity, holiday shocks, and irregular salary cycles.
                    When user transaction coverage is below <strong>14 days</strong> or under <strong>5 transactions</strong>,
                    the engine explicitly abstains from high-variance ML models and defaults to conservative baseline projections.
                    Synthetic evaluation benchmarks are not conflated with real-world accuracy guarantees.
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-6 bg-slate-50 rounded-xl border border-dashed text-xs text-slate-500 text-center">
                Insufficient historical data points to execute temporal train/test split.
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Interactive Stress-Testing Simulator */}
        {activeTab === 'stress_test' && (
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-600" />
                  Synthetic Stress-Test Scenario Simulator
                </h3>
                <p className="text-xs text-slate-500">
                  Simulate adverse macroeconomic or personal financial shocks to test liquidity resilience
                </p>
              </div>

              {/* Scenario Preset Switcher */}
              <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
                <button
                  onClick={() => {
                    setActiveScenario('SALARY_DELAY')
                    setTimeout(() => runStressTest(), 50)
                  }}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    activeScenario === 'SALARY_DELAY' ? 'bg-white text-navy-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  Salary Delay
                </button>
                <button
                  onClick={() => {
                    setActiveScenario('EMERGENCY_EXPENSE')
                    setTimeout(() => runStressTest(), 50)
                  }}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    activeScenario === 'EMERGENCY_EXPENSE' ? 'bg-white text-navy-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  Emergency Outflow
                </button>
                <button
                  onClick={() => {
                    setActiveScenario('SPENDING_SURGE')
                    setTimeout(() => runStressTest(), 50)
                  }}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    activeScenario === 'SPENDING_SURGE' ? 'bg-white text-navy-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  Spending Surge
                </button>
              </div>
            </div>

            {/* Scenario Configuration Controls */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
              {activeScenario === 'SALARY_DELAY' && (
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-700">Salary Delay Duration:</span>
                  <select
                    value={delayDays}
                    onChange={(e) => {
                      setDelayDays(Number(e.target.value))
                      setTimeout(() => runStressTest(), 50)
                    }}
                    className="rounded border border-slate-300 px-2.5 py-1 bg-white text-slate-800"
                  >
                    <option value={7}>7 Days Late</option>
                    <option value={14}>14 Days Late</option>
                    <option value={21}>21 Days Late</option>
                  </select>
                </div>
              )}

              {activeScenario === 'EMERGENCY_EXPENSE' && (
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-700">Unexpected Emergency Amount:</span>
                  <select
                    value={emergencyExpenseInr}
                    onChange={(e) => {
                      setEmergencyExpenseInr(Number(e.target.value))
                      setTimeout(() => runStressTest(), 50)
                    }}
                    className="rounded border border-slate-300 px-2.5 py-1 bg-white text-slate-800"
                  >
                    <option value={15000}>₹15,000 (Minor Repair)</option>
                    <option value={25000}>₹25,000 (Medical Outflow)</option>
                    <option value={50000}>₹50,000 (Major Emergency)</option>
                  </select>
                </div>
              )}

              {activeScenario === 'SPENDING_SURGE' && (
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-700">Discretionary Surge Rate:</span>
                  <select
                    value={spendSurgePct}
                    onChange={(e) => {
                      setSpendSurgePct(Number(e.target.value))
                      setTimeout(() => runStressTest(), 50)
                    }}
                    className="rounded border border-slate-300 px-2.5 py-1 bg-white text-slate-800"
                  >
                    <option value={25}>+25% Living Expenses</option>
                    <option value={40}>+40% Festive / Travel Surge</option>
                    <option value={75}>+75% Extreme Lifestyle Spike</option>
                  </select>
                </div>
              )}

              <Button
                variant="primary"
                size="sm"
                onClick={() => runStressTest()}
                isLoading={isStressLoading}
              >
                Re-simulate Shock
              </Button>
            </div>

            {/* Stress Test Comparison Results */}
            {stressResult && (
              <div className="space-y-4">
                <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-xs text-amber-900">
                  <strong>Simulated Shock:</strong> {stressResult.shock_description}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium">Baseline End Balance</p>
                    <p className="text-base font-bold text-slate-900 mt-1 font-mono">
                      {formatINR(stressResult.baseline_end_balance_inr)}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium">Stressed End Balance</p>
                    <p className="text-base font-bold text-rose-700 mt-1 font-mono">
                      {formatINR(stressResult.stressed_end_balance_inr)}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium">Stressed Minimum Dip</p>
                    <p className="text-base font-bold text-amber-700 mt-1 font-mono">
                      {formatINR(stressResult.stressed_min_balance_inr)}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-slate-500 font-medium">Shortfall Induced?</p>
                    <p className="text-base font-bold mt-1">
                      {stressResult.shortfall_induced ? (
                        <span className="text-rose-600">Yes (Breached)</span>
                      ) : (
                        <span className="text-emerald-600">Resilient</span>
                      )}
                    </p>
                  </div>
                </div>

                {/* Stressed vs Baseline Chart */}
                <div className="h-64 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stressResult.comparison_points}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="display_date" stroke="#94a3b8" fontSize={10} tickLine={false} />
                      <YAxis
                        stroke="#94a3b8"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const pt = payload[0].payload
                            return (
                              <div className="bg-navy-900 text-white p-2.5 rounded-lg text-xs space-y-1">
                                <p className="font-bold text-slate-200">{pt.display_date}</p>
                                <div className="text-slate-300">
                                  Baseline: <span className="font-mono">{formatINR(pt.baseline_balance_inr)}</span>
                                </div>
                                <div className="text-rose-300 font-bold">
                                  Stressed: <span className="font-mono">{formatINR(pt.stressed_balance_inr)}</span>
                                </div>
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="baseline_balance_inr"
                        name="Baseline Trajectory"
                        stroke="#94a3b8"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="stressed_balance_inr"
                        name="Stressed Trajectory"
                        stroke="#e11d48"
                        strokeWidth={2.5}
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ForecastingPage
