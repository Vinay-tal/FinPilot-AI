import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Target, Shield, Calendar, Trash2, CheckCircle2, TrendingUp, Sliders } from 'lucide-react'
import { getGoalsApi, createGoalApi, updateGoalApi, deleteGoalApi } from '@/api/goals'
import { getDashboardSummaryApi } from '@/api/dashboard'
import { formatINR, formatDate } from '@/lib/formatters'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { AddGoalModal } from '@/components/goals/AddGoalModal'
import { GoalSimulationModal } from '@/components/goals/GoalSimulationModal'
import { CardSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { useToast } from '@/context/ToastContext'
import { SavingsGoal } from '@/types'

export const GoalsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [simulatingGoal, setSimulatingGoal] = useState<SavingsGoal | null>(null)

  const {
    data: goals = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['goals'],
    queryFn: getGoalsApi,
  })

  const { data: summary } = useQuery({
    queryKey: ['dashboardSummary', 'current_month'],
    queryFn: () => getDashboardSummaryApi('current_month'),
  })

  const createMutation = useMutation({
    mutationFn: async (formData: any) => {
      await createGoalApi({
        name: formData.name,
        target_amount_paise: Math.round(formData.target_amount_inr * 100),
        current_amount_paise: Math.round(formData.current_amount_inr * 100),
        target_date: formData.target_date,
        category: formData.category,
        priority: formData.priority,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      toastSuccess('Savings goal created!')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to create goal.')
    },
  })

  const addFundsMutation = useMutation({
    mutationFn: async ({ id, deltaInr }: { id: string; deltaInr: number }) => {
      const goal = goals.find((g) => g.id === id)
      if (!goal) return
      const newPaise = goal.current_amount_paise + Math.round(deltaInr * 100)
      await updateGoalApi(id, { current_amount_paise: newPaise })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      toastSuccess('Progress updated!')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGoalApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      toastSuccess('Goal removed.')
    },
  })

  // Calculate Emergency fund benchmark (3-6 months mandatory expenses)
  const monthlyExpenses = summary?.total_expenses_inr || 72450
  const liquidAssets = summary?.total_liquid_balance_inr || 184500
  const runwayMonths = (liquidAssets / (monthlyExpenses || 1)).toFixed(1)

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Financial Goals & Emergency Reserve</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Track safety nets, major purchases, vacations, and wealth milestones
          </p>
        </div>

        <Button
          onClick={() => setIsModalOpen(true)}
          icon={<Plus className="w-4 h-4" />}
          size="sm"
        >
          Create Goal
        </Button>
      </div>

      {/* Emergency Fund Intelligence Banner */}
      <div className="bg-gradient-to-r from-teal-900 to-navy-900 text-white rounded-xl p-5 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-300 shrink-0 mt-0.5">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Emergency Fund Runway: {runwayMonths} Months
            </h3>
            <p className="text-xs text-slate-300 mt-0.5 leading-relaxed max-w-xl">
              Based on your monthly mandatory burn of <strong>{formatINR(monthlyExpenses)}</strong>, your liquid
              reserves of <strong>{formatINR(liquidAssets)}</strong> provide {runwayMonths} months of safety net runway.
              Financial advisors in India recommend 6 months ({formatINR(monthlyExpenses * 6)}) for optimal resilience.
            </p>
          </div>
        </div>

        <div className="shrink-0 flex items-center space-x-2 bg-navy-800/80 px-3.5 py-2 rounded-lg border border-navy-700">
          <span className="text-xs text-slate-400">Target 6-Month:</span>
          <span className="font-mono font-bold text-sm text-teal-300">{formatINR(monthlyExpenses * 6, { hideDecimals: true })}</span>
        </div>
      </div>

      {/* Goals Grid */}
      {error ? (
        <ErrorAlert
          title="Error loading savings goals"
          message={(error as Error).message}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : goals.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {goals.map((g) => {
            const isCompleted = g.status === 'COMPLETED' || g.progress_pct >= 100
            return (
              <div
                key={g.id}
                className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs hover:shadow-card-hover transition-all space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <Target className="w-4 h-4 text-teal-600 shrink-0" />
                      <h3 className="font-bold text-slate-900 text-sm truncate">{g.name}</h3>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant={g.priority === 'HIGH' ? 'danger' : 'info'}>
                        {g.priority} Priority
                      </Badge>
                      {g.feasibility_status === 'COMPLETED' ? (
                        <Badge variant="success">Completed</Badge>
                      ) : g.feasibility_status === 'ON_TRACK' ? (
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                          On Track
                        </span>
                      ) : g.feasibility_status === 'BEHIND' ? (
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                          Behind Target
                        </span>
                      ) : (
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                          At Risk
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => setSimulatingGoal(g)}
                      title="Simulate timeline with different contributions"
                      className="p-1 text-slate-400 hover:text-teal-600 hover:bg-slate-50 rounded transition-colors"
                    >
                      <Sliders className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm('Delete this goal?')) {
                          deleteMutation.mutate(g.id)
                        }
                      }}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-baseline text-xs">
                    <span className="font-mono font-bold text-slate-900 text-base">
                      {formatINR(g.current_amount_inr, { hideDecimals: true })}
                    </span>
                    <span className="text-slate-400 font-mono text-xs">
                      Target: {formatINR(g.target_amount_inr, { hideDecimals: true })}
                    </span>
                  </div>

                  <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isCompleted ? 'bg-emerald-500' : 'bg-teal-600'
                      }`}
                      style={{ width: `${Math.min(g.progress_pct, 100)}%` }}
                    />
                  </div>

                  <div className="flex justify-between items-center text-[11px] text-slate-500 pt-0.5">
                    <span className="font-semibold text-teal-700">{g.progress_pct}% Completed</span>
                    <span className="flex items-center gap-1 text-slate-400">
                      <Calendar className="w-3 h-3" />
                      Target: {formatDate(g.target_date)}
                    </span>
                  </div>
                </div>

                {/* Monthly Contribution Stats */}
                <div className="bg-slate-50 rounded-lg p-2.5 text-2xs space-y-1 border border-slate-100 text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Committed Savings:</span>
                    <strong className="text-slate-900 font-mono">
                      ₹{g.monthly_contribution_inr?.toLocaleString() || '0'}/mo
                    </strong>
                  </div>
                  {g.required_monthly_inr && g.required_monthly_inr > 0 && (
                    <div className="flex justify-between">
                      <span className="text-slate-500">Required Pace:</span>
                      <strong className="text-teal-700 font-mono">
                        ₹{g.required_monthly_inr.toLocaleString()}/mo
                      </strong>
                    </div>
                  )}
                  {g.projected_completion_date && (
                    <div className="flex justify-between pt-1 border-t border-slate-200/50">
                      <span className="text-slate-500">Projected Completion:</span>
                      <strong className="text-slate-800">{formatDate(g.projected_completion_date)}</strong>
                    </div>
                  )}
                </div>

                {/* Action Buttons: Simulate Plan + Quick Contribution */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <button
                    onClick={() => setSimulatingGoal(g)}
                    className="flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-800 hover:underline"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    Simulate Plan
                  </button>

                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => addFundsMutation.mutate({ id: g.id, deltaInr: 5000 })}
                      className="px-2 py-1 rounded bg-slate-100 hover:bg-teal-50 hover:text-teal-700 font-mono text-[11px] font-semibold transition-colors"
                    >
                      +₹5k
                    </button>
                    <button
                      onClick={() => addFundsMutation.mutate({ id: g.id, deltaInr: 10000 })}
                      className="px-2 py-1 rounded bg-slate-100 hover:bg-teal-50 hover:text-teal-700 font-mono text-[11px] font-semibold transition-colors"
                    >
                      +₹10k
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState
          title="No savings goals created"
          description="Track an Emergency Fund or target milestone to accelerate your savings journey."
          actionLabel="Create Savings Goal"
          onAction={() => setIsModalOpen(true)}
        />
      )}

      {/* Add Modal */}
      <AddGoalModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={async (data) => createMutation.mutateAsync(data)}
        isLoading={createMutation.isPending}
      />

      {/* Goal Timeline Simulation Modal */}
      <GoalSimulationModal
        goal={simulatingGoal}
        isOpen={!!simulatingGoal}
        onClose={() => setSimulatingGoal(null)}
      />
    </div>
  )
}
