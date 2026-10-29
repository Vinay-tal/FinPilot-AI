import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Tag,
  ShieldCheck,
  Calendar,
  AlertCircle,
  ArrowRight,
  Layers,
  RefreshCw,
  Sliders,
} from 'lucide-react'
import {
  getRecommendationsApi,
  generateRecommendationsApi,
  updateRecommendationStatusApi,
  applyRecommendationApi,
} from '@/api/recommendations'
import { RecommendationItem } from '@/types'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { CardSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { useToast } from '@/context/ToastContext'
import { formatINR } from '@/lib/formatters'

export const PersonalizedRecommendationsView: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<'all' | 'new' | 'accepted' | 'completed' | 'dismissed'>('all')
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const {
    data: recommendations = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<RecommendationItem[]>({
    queryKey: ['recommendations', statusFilter],
    queryFn: () => getRecommendationsApi(statusFilter),
  })

  const scanMutation = useMutation({
    mutationFn: generateRecommendationsApi,
    onSuccess: (data) => {
      showToast({
        type: 'success',
        title: 'Recommendations Evaluated',
        message: `Generated ${data.length} personalized financial optimizations.`,
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
    onError: (err: any) => {
      showToast({
        type: 'error',
        title: 'Scan Failed',
        message: err?.message || 'Could not evaluate recommendations.',
      })
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'new' | 'accepted' | 'dismissed' | 'completed' }) =>
      updateRecommendationStatusApi(id, status),
    onSuccess: (updated) => {
      showToast({
        type: 'success',
        title: 'Status Updated',
        message: `Recommendation marked as ${updated.status}.`,
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  const applyMutation = useMutation({
    mutationFn: (id: string) => applyRecommendationApi(id),
    onSuccess: (res) => {
      showToast({
        type: 'success',
        title: 'Action Applied',
        message: res.message,
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['goals'] })
    },
    onError: (err: any) => {
      showToast({
        type: 'error',
        title: 'Action Failed',
        message: err?.message || 'Could not apply recommendation automatically.',
      })
    },
  })

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'BUDGET_OVERSPEND':
        return <Badge variant="warning">Budget Optimization</Badge>
      case 'RECURRING_REVIEW':
        return <Badge variant="info">Subscription Audit</Badge>
      case 'EMERGENCY_RESERVE':
        return <Badge variant="success">Emergency Buffer</Badge>
      case 'GOAL_ADJUSTMENT':
        return <Badge variant="indigo">Goal Alignment</Badge>
      case 'UPCOMING_BILL':
        return <Badge variant="danger">Upcoming Obligation</Badge>
      default:
        return <Badge variant="neutral">Financial Advisory</Badge>
    }
  }

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'HIGH':
        return <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">High Confidence</span>
      case 'MEDIUM':
        return <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">Medium Confidence</span>
      default:
        return <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">Preliminary Guidance</span>
    }
  }

  const activeCount = recommendations.filter((r) => r.status === 'new').length
  const totalPotentialBenefit = recommendations
    .filter((r) => r.status !== 'dismissed')
    .reduce((acc, r) => acc + (r.estimated_impact_inr || 0), 0)

  return (
    <div className="space-y-6">
      {/* Deduplication Guarantee & Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-slate-900 tracking-tight">Personalized Recommendation Engine</h3>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              Deterministic Advisory
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 max-w-xl">
            Derived from your verified transactions, category pacing limits, and upcoming obligations. Savings figures are rigorously deduplicated to prevent double-counting.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {totalPotentialBenefit > 0 && (
            <div className="text-right hidden md:block">
              <span className="block text-2xs text-slate-400 font-medium">Estimated Optimization</span>
              <span className="text-sm font-bold text-emerald-600">+{formatINR(totalPotentialBenefit)}</span>
            </div>
          )}

          <Button
            size="sm"
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${scanMutation.isPending ? 'animate-spin' : ''}`} />}
          >
            {scanMutation.isPending ? 'Analyzing...' : 'Scan & Refresh'}
          </Button>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
        {(['all', 'new', 'accepted', 'completed', 'dismissed'] as const).map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
              statusFilter === st
                ? 'bg-slate-900 text-white shadow-2xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {st} {st === 'new' && activeCount > 0 ? `(${activeCount})` : ''}
          </button>
        ))}
      </div>

      {/* Recommendations List */}
      {isLoading ? (
        <CardSkeleton count={3} />
      ) : recommendations.length === 0 ? (
        <EmptyState
          title="No recommendations found"
          description={
            statusFilter === 'all'
              ? 'No active spending adjustments needed right now. Click "Scan & Refresh" to run fresh checks across your ledger.'
              : `No recommendations with status "${statusFilter}".`
          }
        />
      ) : (
        <div className="space-y-4">
          {recommendations.map((rec: RecommendationItem) => (
            <div
              key={rec.id}
              className={`rounded-xl border p-5 bg-white transition-all shadow-2xs ${
                rec.status === 'completed'
                  ? 'border-emerald-200 bg-emerald-50/20'
                  : rec.status === 'dismissed'
                  ? 'border-slate-200 opacity-60 bg-slate-50/50'
                  : 'border-slate-200/90 hover:border-slate-300'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-2.5">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {getTypeBadge(rec.recommendation_type)}
                    {getConfidenceBadge(rec.confidence)}
                    <span className="text-2xs text-slate-400 font-medium">Period: {rec.data_period}</span>
                  </div>
                  <h4 className="text-base font-bold text-slate-900 tracking-tight">{rec.title}</h4>
                </div>

                {rec.estimated_impact_inr > 0 && (
                  <div className="text-left sm:text-right shrink-0">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      +{formatINR(rec.estimated_impact_inr)} Benefit
                    </span>
                  </div>
                )}
              </div>

              {/* Explanation & Assumptions */}
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                {rec.explanation}
              </p>

              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-2xs space-y-1 text-slate-600 mb-4">
                <p>
                  <strong className="text-slate-700">Financial Assumptions:</strong> {rec.impact_assumptions}
                </p>
                <p>
                  <strong className="text-slate-700">Suggested Action:</strong> {rec.suggested_action}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="text-2xs text-slate-400 capitalize">Status: <strong>{rec.status}</strong></span>
                </div>

                <div className="flex items-center gap-2">
                  {rec.status === 'new' && (
                    <>
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => statusMutation.mutate({ id: rec.id, status: 'dismissed' })}
                        disabled={statusMutation.isPending}
                      >
                        Dismiss
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => statusMutation.mutate({ id: rec.id, status: 'accepted' })}
                        disabled={statusMutation.isPending}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        variant="primary"
                        onClick={() => applyMutation.mutate(rec.id)}
                        disabled={applyMutation.isPending}
                        icon={<Sparkles className="w-3.5 h-3.5" />}
                      >
                        {applyMutation.isPending ? 'Applying...' : 'Apply Action'}
                      </Button>
                    </>
                  )}

                  {rec.status === 'accepted' && (
                    <>
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => statusMutation.mutate({ id: rec.id, status: 'dismissed' })}
                        disabled={statusMutation.isPending}
                      >
                        Dismiss
                      </Button>
                      <Button
                        size="xs"
                        variant="primary"
                        onClick={() => applyMutation.mutate(rec.id)}
                        disabled={applyMutation.isPending}
                        icon={<Sparkles className="w-3.5 h-3.5" />}
                      >
                        {applyMutation.isPending ? 'Applying...' : 'Apply Action'}
                      </Button>
                    </>
                  )}

                  {(rec.status === 'completed' || rec.status === 'dismissed') && (
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => statusMutation.mutate({ id: rec.id, status: 'new' })}
                      disabled={statusMutation.isPending}
                    >
                      Reopen
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
