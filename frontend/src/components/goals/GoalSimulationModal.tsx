import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Sliders,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  X,
  Sparkles,
} from 'lucide-react'
import { simulateGoalApi, updateGoalApi } from '@/api/goals'
import { SavingsGoal, GoalSimulationResponse } from '@/types'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { useToast } from '@/context/ToastContext'
import { formatINR, formatDate } from '@/lib/formatters'

interface GoalSimulationModalProps {
  goal: SavingsGoal | null
  isOpen: boolean
  onClose: () => void
}

export const GoalSimulationModal: React.FC<GoalSimulationModalProps> = ({
  goal,
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const defaultContribution =
    (goal?.monthly_contribution_inr && goal.monthly_contribution_inr > 0)
      ? goal.monthly_contribution_inr
      : (goal?.required_monthly_inr || 5000)

  const [monthlyContribution, setMonthlyContribution] = useState<number>(defaultContribution)
  const [debouncedContribution, setDebouncedContribution] = useState<number>(defaultContribution)

  useEffect(() => {
    if (goal) {
      const d = (goal.monthly_contribution_inr && goal.monthly_contribution_inr > 0)
        ? goal.monthly_contribution_inr
        : (goal.required_monthly_inr || 5000)
      setMonthlyContribution(d)
      setDebouncedContribution(d)
    }
  }, [goal?.id, goal?.monthly_contribution_inr, goal?.required_monthly_inr])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedContribution(monthlyContribution)
    }, 200)
    return () => clearTimeout(timer)
  }, [monthlyContribution])

  const goalId = goal?.id || ''

  const {
    data: simulation,
    isLoading: isSimulating,
  } = useQuery<GoalSimulationResponse>({
    queryKey: ['goalSimulation', goalId, debouncedContribution],
    queryFn: () => simulateGoalApi(goalId, debouncedContribution),
    enabled: isOpen && !!goal && debouncedContribution > 0,
  })

  const saveContributionMutation = useMutation({
    mutationFn: () => {
      if (!goal) return Promise.reject(new Error('No goal selected'))
      return updateGoalApi(goal.id, {
        monthly_contribution_paise: Math.round(monthlyContribution * 100),
      })
    },
    onSuccess: () => {
      showToast({
        type: 'success',
        title: 'Contribution Updated',
        message: `Set committed monthly contribution for "${goal?.name}" to ₹${monthlyContribution.toLocaleString()}.`,
      })
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      onClose()
    },
    onError: (err: any) => {
      showToast({
        type: 'error',
        title: 'Update Failed',
        message: err?.message || 'Could not save contribution.',
      })
    },
  })

  if (!isOpen || !goal) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Goal Timeline Simulator</h3>
              <p className="text-xs text-slate-500">{goal.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Goal Stats */}
        <div className="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
          <div>
            <span className="text-2xs text-slate-400 block font-medium">Target Amount</span>
            <span className="font-bold text-slate-800 text-sm font-mono">{formatINR(goal.target_amount_inr)}</span>
          </div>
          <div>
            <span className="text-2xs text-slate-400 block font-medium">Accumulated</span>
            <span className="font-bold text-emerald-600 text-sm font-mono">{formatINR(goal.current_amount_inr)}</span>
          </div>
          <div>
            <span className="text-2xs text-slate-400 block font-medium">Original Target Date</span>
            <span className="font-medium text-slate-700">{formatDate(goal.target_date)}</span>
          </div>
          <div>
            <span className="text-2xs text-slate-400 block font-medium">Baseline Required</span>
            <span className="font-medium text-slate-700 font-mono">
              ₹{goal.required_monthly_inr?.toLocaleString() || '0'}/mo
            </span>
          </div>
        </div>

        {/* Interactive Slider */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800">
              Hypothetical Monthly Contribution:
            </label>
            <div className="flex items-center gap-1 font-mono font-bold text-sm text-teal-700 bg-teal-50 px-2.5 py-1 rounded-lg border border-teal-200">
              <span>₹</span>
              <input
                type="number"
                min={500}
                max={100000}
                step={500}
                value={monthlyContribution}
                onChange={(e) => setMonthlyContribution(Number(e.target.value))}
                className="w-20 bg-transparent text-right font-bold focus:outline-hidden"
              />
              <span className="text-2xs text-teal-600 font-normal">/mo</span>
            </div>
          </div>

          <input
            type="range"
            min={1000}
            max={Math.max(50000, (goal.target_amount_inr - goal.current_amount_inr) / 2)}
            step={500}
            value={monthlyContribution}
            onChange={(e) => setMonthlyContribution(Number(e.target.value))}
            className="w-full accent-teal-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
          />

          <div className="flex justify-between text-2xs text-slate-400">
            <span>₹1,000/mo</span>
            <span>₹25,000/mo</span>
            <span>₹50,000+/mo</span>
          </div>
        </div>

        {/* Dynamic Simulation Outcome Card */}
        {isSimulating ? (
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-center text-xs text-slate-500 animate-pulse">
            Simulating completion timeline...
          </div>
        ) : simulation ? (
          <div
            className={`p-4 rounded-xl border transition-all text-xs space-y-2 ${
              simulation.is_achievable
                ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
                : 'bg-amber-50/60 border-amber-200 text-amber-950'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold flex items-center gap-1.5">
                {simulation.is_achievable ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                )}
                {simulation.is_achievable ? 'Achievable Plan' : 'Timeline Delayed'}
              </span>
              <Badge variant={simulation.is_achievable ? 'success' : 'warning'}>
                {simulation.feasibility_status.replace('_', ' ')}
              </Badge>
            </div>

            <p className="text-xs leading-relaxed">{simulation.message}</p>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/50 text-2xs text-slate-700">
              <div>
                <span className="text-slate-500 block">Projected Completion:</span>
                <strong className="text-slate-900">{formatDate(simulation.simulated_completion_date)}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Months to Complete:</span>
                <strong className="text-slate-900">{simulation.months_to_completion} Months</strong>
              </div>
            </div>
          </div>
        ) : null}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => saveContributionMutation.mutate()}
            disabled={saveContributionMutation.isPending}
            icon={<Sparkles className="w-3.5 h-3.5" />}
          >
            {saveContributionMutation.isPending ? 'Saving...' : 'Commit Monthly Plan'}
          </Button>
        </div>
      </div>
    </div>
  )
}
