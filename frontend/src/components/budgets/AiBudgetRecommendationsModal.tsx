import React, { useState, useEffect } from 'react'
import { Sparkles, X, Check, CheckSquare, Square, Info } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { BudgetRecommendationsResponse, BudgetRecommendationItem } from '@/types'
import { formatINR } from '@/lib/formatters'

interface AiBudgetRecommendationsModalProps {
  isOpen: boolean
  onClose: () => void
  recommendationsData?: BudgetRecommendationsResponse
  isLoading: boolean
  onApply: (selectedIds: string[], overrides?: Record<string, number>) => Promise<void>
  isApplying: boolean
}

export const AiBudgetRecommendationsModal: React.FC<AiBudgetRecommendationsModalProps> = ({
  isOpen,
  onClose,
  recommendationsData,
  isLoading,
  onApply,
  isApplying,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [overrides, setOverrides] = useState<Record<string, number>>({})

  useEffect(() => {
    if (recommendationsData?.recommendations) {
      setSelectedIds(recommendationsData.recommendations.map((r) => r.category_id))
      const initialOverrides: Record<string, number> = {}
      recommendationsData.recommendations.forEach((r) => {
        initialOverrides[r.category_id] = r.suggested_budget_inr
      })
      setOverrides(initialOverrides)
    }
  }, [recommendationsData])

  if (!isOpen) return null

  const items = recommendationsData?.recommendations || []

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const toggleAll = () => {
    if (selectedIds.length === items.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(items.map((i) => i.category_id))
    }
  }

  const handleAmountChange = (id: string, val: number) => {
    setOverrides((prev) => ({ ...prev, [id]: Math.max(0, val) }))
  }

  const totalSelectedInr = items
    .filter((i) => selectedIds.includes(i.category_id))
    .reduce((sum, i) => sum + (overrides[i.category_id] ?? i.suggested_budget_inr), 0)

  const handleApplyClick = async () => {
    if (selectedIds.length === 0) return
    await onApply(selectedIds, overrides)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[88vh] flex flex-col shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-teal-50/50 to-slate-50/50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-teal-100 text-teal-800 rounded-lg">
              <Sparkles className="w-5 h-5 text-teal-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">
                Historical Spending AI Budget Recommendations
              </h3>
              <p className="text-xs text-slate-500">
                Data-driven category targets based on 90-day spending patterns &amp; category elasticity
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Info Banner */}
        <div className="bg-teal-50/70 border-b border-teal-100 px-6 py-2.5 flex items-center justify-between text-xs text-teal-900">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-teal-600 shrink-0" />
            <span>
              Essentials: <strong>+5% safety buffer</strong> | Discretionary: <strong>-10% savings optimization</strong>
            </span>
          </div>
          <button
            onClick={toggleAll}
            className="text-teal-700 font-semibold hover:underline text-2xs"
          >
            {selectedIds.length === items.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>

        {/* Content list */}
        <div className="p-6 overflow-y-auto space-y-3.5 flex-1 divide-y divide-slate-100">
          {isLoading ? (
            <div className="text-center py-12 text-sm text-slate-500">
              Analyzing historical spending transactions...
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-10 text-sm text-slate-500">
              No historical category expenses found to generate recommendations.
            </div>
          ) : (
            items.map((item) => {
              const isSelected = selectedIds.includes(item.category_id)
              const amount = overrides[item.category_id] ?? item.suggested_budget_inr

              return (
                <div
                  key={item.category_id}
                  className={`pt-3.5 first:pt-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-2.5 rounded-xl transition-all ${
                    isSelected ? 'bg-teal-50/30' : 'opacity-60'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <button
                      type="button"
                      onClick={() => toggleSelect(item.category_id)}
                      className="mt-0.5 text-slate-400 hover:text-teal-600"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-5 h-5 text-teal-600" />
                      ) : (
                        <Square className="w-5 h-5 text-slate-300" />
                      )}
                    </button>

                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: item.category_color || '#0d9488' }}
                        />
                        <span className="font-bold text-sm text-slate-900">{item.category_name}</span>
                        <span
                          className={`text-2xs font-semibold px-1.5 py-0.2 rounded ${
                            item.is_essential
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {item.is_essential ? 'Essential (+5%)' : 'Discretionary (-10%)'}
                        </span>
                      </div>

                      <p className="text-xs text-slate-500">{item.rationale}</p>

                      <div className="flex items-center gap-3 text-2xs text-slate-400 font-mono">
                        <span>Hist Avg: {formatINR(item.historical_avg_spent_inr)}</span>
                        {item.current_budget_inr ? (
                          <span>Current: {formatINR(item.current_budget_inr)}</span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  {/* Override input */}
                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <span className="text-xs text-slate-400">Target: ₹</span>
                    <input
                      type="number"
                      step="500"
                      value={amount}
                      disabled={!isSelected}
                      onChange={(e) => handleAmountChange(item.category_id, Number(e.target.value))}
                      className="w-24 px-2 py-1 text-xs font-mono font-bold rounded border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-600 disabled:bg-slate-100"
                    />
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between">
          <div className="text-xs text-slate-600">
            Selected Total:{' '}
            <strong className="text-slate-900 font-mono text-sm">
              {formatINR(totalSelectedInr)}
            </strong>{' '}
            ({selectedIds.length} categories)
          </div>

          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={onClose} disabled={isApplying}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleApplyClick}
              disabled={selectedIds.length === 0}
              isLoading={isApplying}
            >
              <Check className="w-4 h-4 mr-1.5" />
              Apply {selectedIds.length} Budgets
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
