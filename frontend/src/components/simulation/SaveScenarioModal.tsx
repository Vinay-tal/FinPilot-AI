import React, { useState } from 'react'
import { Bookmark, X, Check } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { EnhancedSimulationParams } from '@/types'

interface SaveScenarioModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (name: string, description: string) => Promise<void>
  isSaving: boolean
  params: EnhancedSimulationParams
}

export const SaveScenarioModal: React.FC<SaveScenarioModalProps> = ({
  isOpen,
  onClose,
  onSave,
  isSaving,
  params,
}) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Please provide a descriptive scenario name')
      return
    }
    setError('')
    try {
      await onSave(name.trim(), description.trim())
      setName('')
      setDescription('')
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Failed to save scenario')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-teal-50 text-teal-700 rounded-lg">
              <Bookmark className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Save Named Scenario</h3>
              <p className="text-xs text-slate-500">Persist what-if conditions for future reference</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 text-xs rounded-lg bg-rose-50 text-rose-700 border border-rose-200">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Scenario Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., 2026 Salary Hike + Car Purchase"
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Description / Notes (Optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Assumes 15% salary raise, ₹12,000 monthly car EMI, and cutting 10% dining spend."
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
            />
          </div>

          {/* Snapshot of parameters */}
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1 text-2xs text-slate-600 font-mono">
            <div className="font-sans font-semibold text-slate-700 mb-1">Snapshot Parameters:</div>
            <div className="flex justify-between">
              <span>Salary Delta:</span>
              <span className="font-bold">{params.salary_delta_pct > 0 ? `+${params.salary_delta_pct}%` : `${params.salary_delta_pct}%`}</span>
            </div>
            <div className="flex justify-between">
              <span>Rent Delta:</span>
              <span className="font-bold">₹{params.rent_delta_inr.toLocaleString()}/mo</span>
            </div>
            <div className="flex justify-between">
              <span>Discretionary Cut:</span>
              <span className="font-bold">{params.discretionary_reduction_pct}%</span>
            </div>
            <div className="flex justify-between">
              <span>New Recurring:</span>
              <span className="font-bold">₹{params.new_recurring_monthly_inr.toLocaleString()}/mo</span>
            </div>
            <div className="flex justify-between">
              <span>Unexpected Expense:</span>
              <span className="font-bold">₹{params.unexpected_expense_inr.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span>Savings Delta:</span>
              <span className="font-bold">₹{params.monthly_savings_delta_inr.toLocaleString()}/mo</span>
            </div>
          </div>

          <div className="flex justify-end gap-2.5 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isSaving}>
              Cancel
            </Button>
            <Button type="submit" size="sm" isLoading={isSaving}>
              <Check className="w-4 h-4 mr-1.5" />
              Save Scenario
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
