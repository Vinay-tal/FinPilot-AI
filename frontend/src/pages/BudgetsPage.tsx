import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  PieChart,
  AlertCircle,
  Trash2,
  Calendar,
  CheckCircle2,
  Sparkles,
  AlertTriangle,
} from 'lucide-react'
import {
  getBudgetsApi,
  createBudgetApi,
  deleteBudgetApi,
  getBudgetRecommendationsApi,
  applyBudgetRecommendationsApi,
} from '@/api/budgets'
import { getCategoriesApi } from '@/api/categories'
import { formatINR } from '@/lib/formatters'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { StatCard } from '@/components/common/StatCard'
import { AddBudgetModal } from '@/components/budgets/AddBudgetModal'
import { AiBudgetRecommendationsModal } from '@/components/budgets/AiBudgetRecommendationsModal'
import { CardSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { useToast } from '@/context/ToastContext'

export const BudgetsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()

  const today = new Date()
  const [month, setMonth] = useState<number>(today.getMonth() + 1)
  const [year, setYear] = useState<number>(today.getFullYear())
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isAiModalOpen, setIsAiModalOpen] = useState(false)

  const {
    data: budgets = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['budgets', month, year],
    queryFn: () => getBudgetsApi(month, year),
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategoriesApi,
  })

  // AI budget recommendations query
  const {
    data: aiRecommendations,
    isLoading: isLoadingAiRecommendations,
    refetch: refetchAiRecommendations,
  } = useQuery({
    queryKey: ['budgetRecommendations', month, year],
    queryFn: () => getBudgetRecommendationsApi(month, year),
    enabled: isAiModalOpen,
  })

  const createMutation = useMutation({
    mutationFn: async (formData: any) => {
      await createBudgetApi({
        category_id: formData.category_id,
        month: formData.month,
        year: formData.year,
        amount_paise: Math.round(formData.amount_inr * 100),
        alert_threshold: formData.alert_threshold,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
      toastSuccess('Category budget allocation saved!')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to create budget.')
    },
  })

  const applyAiMutation = useMutation({
    mutationFn: async ({
      selectedCategoryIds,
      overrides: _overrides,
    }: {
      selectedCategoryIds: string[]
      overrides?: Record<string, number>
    }) => {
      await applyBudgetRecommendationsApi({
        month,
        year,
        selected_category_ids: selectedCategoryIds,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
      toastSuccess('AI suggested budgets applied successfully!')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to apply budget recommendations.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteBudgetApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
      toastSuccess('Budget allocation removed.')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to delete budget.')
    },
  })

  // Calculate aggregates
  const totalBudgeted = budgets.reduce((acc, b) => acc + b.amount_inr, 0)
  const totalSpent = budgets.reduce((acc, b) => acc + b.spent_inr, 0)
  const totalRemaining = Math.max(0, totalBudgeted - totalSpent)
  const overallBurnPct = totalBudgeted > 0 ? (totalSpent / totalBudgeted) * 100 : 0

  const exceededCount = budgets.filter((b) => b.alert_status === 'EXCEEDED').length
  const warningCount = budgets.filter((b) => b.alert_status === 'WARNING').length

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Category Budgets &amp; Pacing</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Set proactive category spending limits, inspect AI recommendations, and monitor real-time burn
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 focus:bg-white"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                <option key={m} value={m}>
                  {new Date(2026, m - 1, 1).toLocaleString('default', { month: 'short' })}
                </option>
              ))}
            </select>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 focus:bg-white"
            >
              {[2024, 2025, 2026, 2027].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAiModalOpen(true)}
            className="text-xs font-semibold hover:border-teal-600 hover:text-teal-700"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1 text-teal-600" />
            AI Suggestions
          </Button>

          <Button
            onClick={() => setIsModalOpen(true)}
            icon={<Plus className="w-4 h-4" />}
            size="sm"
          >
            Set Budget
          </Button>
        </div>
      </div>

      {/* Threshold Warning Banner */}
      {(exceededCount > 0 || warningCount > 0) && (
        <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-900 flex items-center justify-between text-xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Budget Threshold Notice:</strong> {exceededCount > 0 && `${exceededCount} category exceeded`}
              {exceededCount > 0 && warningCount > 0 && ' and '}
              {warningCount > 0 && `${warningCount} category nearing 80% threshold`}.
            </span>
          </div>
          <span className="text-2xs font-semibold text-amber-800">Review below</span>
        </div>
      )}

      {/* Aggregate Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Total Monthly Allocation"
          value={formatINR(totalBudgeted, { hideDecimals: true })}
          subtitle={`${budgets.length} Categories Budgeted`}
          accentColor="slate"
        />
        <StatCard
          title="Actual Month-to-Date Spend"
          value={formatINR(totalSpent, { hideDecimals: true })}
          subtitle={`Overall Pacing: ${overallBurnPct.toFixed(1)}%`}
          accentColor={overallBurnPct >= 100 ? 'rose' : overallBurnPct >= 80 ? 'amber' : 'teal'}
        />
        <StatCard
          title="Remaining Monthly Buffer"
          value={formatINR(totalRemaining, { hideDecimals: true })}
          subtitle="Remaining allowance across categories"
          accentColor="emerald"
        />
      </div>

      {/* Budgets Grid */}
      {error ? (
        <ErrorAlert
          title="Error loading budgets"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : budgets.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {budgets.map((b) => {
            const isExceeded = b.alert_status === 'EXCEEDED'
            const isWarning = b.alert_status === 'WARNING'
            const barColor = isExceeded ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-teal-500'

            return (
              <div
                key={b.id}
                className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs hover:shadow-card-hover transition-all space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span
                        className="w-3 h-3 rounded-full shrink-0"
                        style={{ backgroundColor: b.category_color || '#0d9488' }}
                      />
                      <h3 className="font-bold text-slate-900 text-sm">{b.category_name}</h3>
                    </div>
                    <p className="text-xs text-slate-500">
                      Limit: <strong className="text-slate-800">{formatINR(b.amount_inr)}</strong>
                    </p>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <Badge variant={isExceeded ? 'danger' : isWarning ? 'warning' : 'success'}>
                      {b.pacing_pct}%
                    </Badge>
                    <button
                      onClick={() => {
                        if (window.confirm('Delete this category budget?')) {
                          deleteMutation.mutate(b.id)
                        }
                      }}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1">
                  <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${barColor} rounded-full transition-all duration-300`}
                      style={{ width: `${Math.min(b.pacing_pct, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                    <span>Spent: {formatINR(b.spent_inr, { hideDecimals: true })}</span>
                    <span>Remaining: {formatINR(b.remaining_inr, { hideDecimals: true })}</span>
                  </div>
                </div>

                {/* Pacing Advice */}
                <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                  {isExceeded ? (
                    <span className="text-rose-600 font-medium flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Budget exceeded by{' '}
                      {formatINR(b.spent_inr - b.amount_inr)}
                    </span>
                  ) : isWarning ? (
                    <span className="text-amber-700 font-medium flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Warning: Consumed &ge;{b.alert_threshold * 100}%
                    </span>
                  ) : (
                    <span className="text-emerald-700 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> On track for this month
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState
          title="No category budgets configured"
          description="Create your first budget to monitor real-time category spending limits and prevent overspending."
          actionLabel="Set Category Budget"
          onAction={() => setIsModalOpen(true)}
        />
      )}

      {/* Add Modal */}
      <AddBudgetModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={async (data) => createMutation.mutateAsync(data)}
        categories={categories}
        isLoading={createMutation.isPending}
      />

      {/* AI Budget Recommendations Modal */}
      <AiBudgetRecommendationsModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        recommendationsData={aiRecommendations}
        isLoading={isLoadingAiRecommendations}
        onApply={async (selectedCategoryIds, overrides) => {
          await applyAiMutation.mutateAsync({ selectedCategoryIds, overrides })
        }}
        isApplying={applyAiMutation.isPending}
      />
    </div>
  )
}
