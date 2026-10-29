import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Filter,
  Info,
  RefreshCw,
  Sparkles,
  TrendingDown,
  ShieldAlert,
  Brain,
  BellRing,
} from 'lucide-react'
import { getInsightsApi, resolveInsightApi } from '@/api/insights'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { Skeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { useToast } from '@/context/ToastContext'
import { formatDateIST } from '@/lib/formatters'
import { FinancialInsight } from '@/types'
import { TransactionIntelligenceHub } from '@/components/insights/TransactionIntelligenceHub'
import { FinancialHealthScoreView } from '@/components/insights/FinancialHealthScoreView'
import { PersonalizedRecommendationsView } from '@/components/insights/PersonalizedRecommendationsView'

export const InsightsPage: React.FC = () => {
  const [mainTab, setMainTab] = useState<'health' | 'recommendations' | 'advisory' | 'intelligence'>('health')
  const [filterResolved, setFilterResolved] = useState<'all' | 'active' | 'resolved'>('all')
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'INFO'>('ALL')
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const resolvedParam = filterResolved === 'all' ? undefined : filterResolved === 'resolved'

  const {
    data: insights = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<FinancialInsight[]>({
    queryKey: ['insights', resolvedParam],
    queryFn: () => getInsightsApi(resolvedParam),
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => resolveInsightApi(id),
    onSuccess: (updated) => {
      showToast({
        type: 'success',
        title: 'Insight Resolved',
        message: `Marked "${updated.title}" as resolved.`,
      })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (err: any) => {
      showToast({
        type: 'error',
        title: 'Action Failed',
        message: err?.message || 'Could not resolve insight.',
      })
    },
  })

  // Client-side severity filtering if needed
  const filteredInsights = insights.filter((item) => {
    if (severityFilter !== 'ALL' && item.severity !== severityFilter) {
      return false
    }
    return true
  })

  // Metric summaries
  const totalCount = insights.length
  const criticalCount = insights.filter((i) => i.severity === 'CRITICAL' && !i.is_resolved).length
  const activeCount = insights.filter((i) => !i.is_resolved).length
  const resolvedCount = insights.filter((i) => i.is_resolved).length

  const getSeverityBadge = (severity: FinancialInsight['severity']) => {
    switch (severity) {
      case 'CRITICAL':
        return <Badge variant="danger" dot>Critical</Badge>
      case 'WARNING':
        return <Badge variant="warning" dot>Warning</Badge>
      case 'INFO':
      default:
        return <Badge variant="info">Info</Badge>
    }
  }

  const getTypeIcon = (type: FinancialInsight['insight_type']) => {
    switch (type) {
      case 'ANOMALY':
        return <ShieldAlert className="w-5 h-5 text-rose-500" />
      case 'SPENDING_SPIKE':
        return <TrendingDown className="w-5 h-5 text-amber-500" />
      case 'SHORTFALL_WARNING':
        return <AlertOctagon className="w-5 h-5 text-rose-600" />
      case 'BUDGET_ALERT':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />
      case 'SAVINGS_TIP':
      default:
        return <Sparkles className="w-5 h-5 text-teal-600" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Insights & Anomaly Detection
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              Rule + ML Engine
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-0.5">
            Real-time anomaly scans, spending spikes, and actionable cash-flow warnings.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            loading={isFetching && !isLoading}
          >
            <RefreshCw className="w-4 h-4 mr-1.5" />
            Scan Now
          </Button>
        </div>
      </div>

      {/* Top Main Section Switcher */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setMainTab('health')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            mainTab === 'health'
              ? 'bg-navy-900 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-emerald-400" />
          Financial Health Score
        </button>
        <button
          onClick={() => setMainTab('recommendations')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            mainTab === 'recommendations'
              ? 'bg-navy-900 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Sparkles className="w-4 h-4 text-teal-400" />
          Personalized Recommendations
        </button>
        <button
          onClick={() => setMainTab('advisory')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            mainTab === 'advisory'
              ? 'bg-navy-900 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <BellRing className="w-4 h-4 text-amber-400" />
          Anomaly Alerts ({activeCount})
        </button>
        <button
          onClick={() => setMainTab('intelligence')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            mainTab === 'intelligence'
              ? 'bg-navy-900 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Brain className="w-4 h-4 text-indigo-400" />
          Transaction Intelligence Hub
        </button>
      </div>

      {mainTab === 'health' && <FinancialHealthScoreView />}
      {mainTab === 'recommendations' && <PersonalizedRecommendationsView />}
      {mainTab === 'intelligence' && <TransactionIntelligenceHub />}
      {mainTab === 'advisory' && (
        <div className="space-y-6">
          {/* Summary KPI Badges */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Scanned</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{totalCount}</p>
          <p className="text-xs text-slate-500 mt-0.5">Heuristic & ML findings</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-rose-600 uppercase tracking-wider">Active Critical</p>
          <p className="text-2xl font-bold text-rose-600 mt-1">{criticalCount}</p>
          <p className="text-xs text-slate-500 mt-0.5">Urgent attention needed</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-amber-600 uppercase tracking-wider">Unresolved</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{activeCount}</p>
          <p className="text-xs text-slate-500 mt-0.5">Awaiting user review</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-teal-700 uppercase tracking-wider">Resolved</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">{resolvedCount}</p>
          <p className="text-xs text-slate-500 mt-0.5">Handled or dismissed</p>
        </div>
      </div>

      {/* Filter and Tab Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="inline-flex p-1 bg-slate-100 rounded-lg text-xs font-semibold text-slate-600 self-start sm:self-auto">
          <button
            onClick={() => setFilterResolved('all')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              filterResolved === 'all'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'hover:text-slate-900'
            }`}
          >
            All Insights ({insights.length})
          </button>
          <button
            onClick={() => setFilterResolved('active')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              filterResolved === 'active'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'hover:text-slate-900'
            }`}
          >
            Active ({activeCount})
          </button>
          <button
            onClick={() => setFilterResolved('resolved')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              filterResolved === 'resolved'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'hover:text-slate-900'
            }`}
          >
            Resolved ({resolvedCount})
          </button>
        </div>

        {/* Severity Filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="text-xs text-slate-500 font-medium">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as any)}
            className="text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="WARNING">Warning Only</option>
            <option value="INFO">Info Only</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      {isError ? (
        <ErrorAlert
          title="Failed to load insights"
          message={error instanceof Error ? error.message : 'Please check your connection.'}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : filteredInsights.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No insights found"
          description={
            filterResolved === 'active'
              ? 'Awesome! You have no unresolved financial anomalies or budget spikes.'
              : 'No insights match the current filter criteria.'
          }
        />
      ) : (
        <div className="space-y-3.5">
          {filteredInsights.map((insight) => (
            <div
              key={insight.id}
              className={`p-5 rounded-xl border transition-all ${
                insight.is_resolved
                  ? 'bg-slate-50/70 border-slate-200/70 opacity-75'
                  : insight.severity === 'CRITICAL'
                  ? 'bg-rose-50/20 border-rose-200/80 shadow-xs hover:border-rose-300'
                  : insight.severity === 'WARNING'
                  ? 'bg-amber-50/20 border-amber-200/80 shadow-xs hover:border-amber-300'
                  : 'bg-white border-slate-200/80 shadow-xs hover:border-teal-300'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex items-start space-x-3.5">
                  <div
                    className={`p-2.5 rounded-xl shrink-0 ${
                      insight.severity === 'CRITICAL'
                        ? 'bg-rose-100/70'
                        : insight.severity === 'WARNING'
                        ? 'bg-amber-100/70'
                        : 'bg-teal-100/70'
                    }`}
                  >
                    {getTypeIcon(insight.insight_type)}
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                        {insight.insight_type.replace('_', ' ')}
                      </span>
                      {getSeverityBadge(insight.severity)}
                      {insight.is_resolved && (
                        <span className="inline-flex items-center text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                          Resolved
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-semibold text-slate-900">{insight.title}</h3>
                    <p className="text-sm text-slate-600 leading-relaxed max-w-3xl">
                      {insight.description}
                    </p>
                    <p className="text-xs text-slate-400 pt-1">
                      Detected on {formatDateIST(insight.created_at)}
                    </p>
                  </div>
                </div>

                <div className="sm:self-center shrink-0">
                  {!insight.is_resolved ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => resolveMutation.mutate(insight.id)}
                      loading={resolveMutation.isPending && resolveMutation.variables === insight.id}
                      className="border-slate-300 hover:border-teal-500 hover:text-teal-700"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1.5 text-slate-500" />
                      Mark Resolved
                    </Button>
                  ) : (
                    <span className="text-xs text-slate-400 italic">Resolved</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
        </div>
      )}
    </div>
  )
}
