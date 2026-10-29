import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ShieldCheck,
  TrendingUp,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  Info,
  Sparkles,
  PieChart,
  RefreshCw,
} from 'lucide-react'
import { getHealthScoreApi } from '@/api/planning'
import { HealthScoreResponse, HealthFactorItem } from '@/types'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { CardSkeleton } from '@/components/common/Skeleton'
import { formatINR } from '@/lib/formatters'

export const FinancialHealthScoreView: React.FC = () => {
  const {
    data: health,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<HealthScoreResponse>({
    queryKey: ['financialHealthScore'],
    queryFn: getHealthScoreApi,
    staleTime: 60000,
  })

  if (isLoading) {
    return <CardSkeleton count={3} />
  }

  if (isError || !health) {
    return (
      <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-rose-800">
        <p className="font-semibold">Unable to load Financial Health Score</p>
        <p className="text-sm mt-1">{(error as any)?.message || 'Service temporarily unavailable.'}</p>
        <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-4">
          Retry Evaluation
        </Button>
      </div>
    )
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 bg-emerald-50 border-emerald-200 ring-emerald-500'
    if (score >= 65) return 'text-teal-600 bg-teal-50 border-teal-200 ring-teal-500'
    if (score >= 50) return 'text-amber-600 bg-amber-50 border-amber-200 ring-amber-500'
    return 'text-rose-600 bg-rose-50 border-rose-200 ring-rose-500'
  }

  const getGradeBadge = (grade: string) => {
    switch (grade) {
      case 'Excellent':
        return <Badge variant="success" dot>Excellent Health</Badge>
      case 'Good':
        return <Badge variant="info" dot>Good Foundation</Badge>
      case 'Fair':
        return <Badge variant="warning" dot>Fair (Room for Growth)</Badge>
      default:
        return <Badge variant="danger" dot>Needs Attention</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Educational Heuristic Disclosure Banner */}
      <div className="bg-amber-50/80 border border-amber-200/90 rounded-xl p-4 flex items-start gap-3 text-amber-900 shadow-2xs">
        <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed space-y-1">
          <p className="font-semibold text-amber-950">Educational Heuristic Assessment</p>
          <p className="text-amber-800">
            {health.disclaimer} This heuristic analyzes your liquid cash buffer, monthly savings velocity, budget discipline, and spending stability to provide actionable improvement suggestions.
          </p>
        </div>
      </div>

      {/* Main Score Hero Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            {/* Score Ring */}
            <div className={`relative flex items-center justify-center w-28 h-28 rounded-full border-4 ${getScoreColor(health.overall_score)} shadow-inner shrink-0`}>
              <div className="text-center">
                <span className="text-4xl font-extrabold tracking-tight text-slate-900 leading-none">
                  {health.overall_score}
                </span>
                <span className="block text-2xs font-semibold uppercase tracking-wider text-slate-500 mt-0.5">
                  / 100
                </span>
              </div>
            </div>

            {/* Assessment Text */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Financial Health Index</h2>
                {getGradeBadge(health.grade)}
              </div>
              <p className="text-sm text-slate-600 max-w-xl leading-relaxed">
                {health.summary}
              </p>
              <div className="flex flex-wrap items-center gap-4 pt-1 text-xs text-slate-500">
                <span>Liquid Buffer: <strong className="text-slate-800">{formatINR(health.liquid_reserve_inr)}</strong></span>
                <span>•</span>
                <span>Monthly Burn: <strong className="text-slate-800">{formatINR(health.monthly_expenses_inr)}</strong></span>
                <span>•</span>
                <span>Savings Velocity: <strong className="text-slate-800">{health.savings_rate_pct}%</strong></span>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />}
            className="self-stretch sm:self-auto shrink-0"
          >
            Re-evaluate
          </Button>
        </div>
      </div>

      {/* 6 Explainable Sub-Factors Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight">Normalized Health Factors</h3>
            <p className="text-xs text-slate-500">
              Each factor is evaluated against established personal finance benchmarks and re-weighted dynamically if data is unavailable.
            </p>
          </div>
          {health.excluded_factors_count > 0 && (
            <span className="text-2xs font-medium px-2 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
              {health.excluded_factors_count} factor{health.excluded_factors_count > 1 ? 's' : ''} excluded & normalized
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {health.factors.map((factor: HealthFactorItem) => (
            <div
              key={factor.factor_id}
              className={`rounded-xl border p-5 transition-all shadow-2xs ${
                factor.is_excluded
                  ? 'bg-slate-50/70 border-slate-200 opacity-80'
                  : 'bg-white border-slate-200/90 hover:border-slate-300'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <h4 className="text-sm font-semibold text-slate-900">{factor.name}</h4>
                  <span className="text-2xs text-slate-400">Weight: {factor.weight} pts</span>
                </div>

                {factor.is_excluded ? (
                  <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                    Excluded
                  </span>
                ) : (
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800">
                    {factor.score}/{factor.max_score} pts
                  </span>
                )}
              </div>

              {/* Progress bar if included */}
              {!factor.is_excluded && (
                <div className="w-full bg-slate-100 rounded-full h-1.5 mb-3 overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full ${
                      factor.normalized_pct >= 80
                        ? 'bg-emerald-500'
                        : factor.normalized_pct >= 50
                        ? 'bg-teal-500'
                        : 'bg-amber-500'
                    }`}
                    style={{ width: `${Math.min(100, factor.normalized_pct)}%` }}
                  />
                </div>
              )}

              {/* Metric & Calculation */}
              <div className="text-xs space-y-1.5 text-slate-600 mt-2">
                {factor.metric_value && (
                  <div className="flex items-center justify-between text-2xs font-medium">
                    <span className="text-slate-500">Observed Value:</span>
                    <span className="font-semibold text-slate-900">{factor.metric_value}</span>
                  </div>
                )}

                <p className="text-2xs text-slate-500 leading-normal">
                  <strong className="text-slate-600">Formula:</strong> {factor.calculation_details}
                </p>

                {factor.is_excluded && factor.exclusion_reason && (
                  <p className="text-2xs text-amber-700 font-medium bg-amber-50 p-1.5 rounded border border-amber-100">
                    Note: {factor.exclusion_reason}
                  </p>
                )}

                {!factor.is_excluded && (
                  <div className="pt-2 border-t border-slate-100 mt-2 flex items-start gap-1.5 text-2xs text-teal-800 bg-teal-50/50 p-2 rounded">
                    <Sparkles className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                    <span>{factor.actionable_tip}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Actionable Improvement Checklist */}
      {health.top_improvement_actions.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-teal-600" />
            <h4 className="text-sm font-bold text-slate-900 tracking-tight">
              Priority Actions to Increase Your Health Score
            </h4>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {health.top_improvement_actions.map((action, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200/80 text-xs text-slate-700"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span className="leading-snug">{action}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
