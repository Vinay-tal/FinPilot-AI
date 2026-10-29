import React from 'react'
import { FolderHeart, X, Trash2, ArrowRight, Calendar, Sliders } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { SavedScenarioItem, EnhancedSimulationParams } from '@/types'
import { formatDate } from '@/lib/formatters'

interface SavedScenariosModalProps {
  isOpen: boolean
  onClose: () => void
  scenarios: SavedScenarioItem[]
  isLoading: boolean
  onLoadScenario: (params: EnhancedSimulationParams) => void
  onDeleteScenario: (id: string) => void
}

export const SavedScenariosModal: React.FC<SavedScenariosModalProps> = ({
  isOpen,
  onClose,
  scenarios,
  isLoading,
  onLoadScenario,
  onDeleteScenario,
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-teal-50 text-teal-700 rounded-lg">
              <FolderHeart className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Saved Scenarios</h3>
              <p className="text-xs text-slate-500">
                Load previously modeled financial scenarios ({scenarios.length})
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

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-3 divide-y divide-slate-100">
          {isLoading ? (
            <div className="text-center py-8 text-sm text-slate-500">Loading scenarios...</div>
          ) : scenarios.length === 0 ? (
            <div className="text-center py-10 space-y-2">
              <Sliders className="w-8 h-8 mx-auto text-slate-300" />
              <p className="text-sm font-semibold text-slate-700">No saved scenarios yet</p>
              <p className="text-xs text-slate-400 max-w-xs mx-auto">
                Adjust the sliders on the simulator and click "Save Scenario" to store your what-if models.
              </p>
            </div>
          ) : (
            scenarios.map((sc) => {
              let parsedParams: EnhancedSimulationParams | null = null
              try {
                parsedParams = JSON.parse(sc.params_json)
              } catch (e) {
                // Ignore parse error
              }

              return (
                <div key={sc.id} className="pt-3 first:pt-0 flex items-start justify-between gap-4 group">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-bold text-sm text-slate-900 group-hover:text-teal-700 transition-colors">
                        {sc.name}
                      </h4>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                        <Calendar className="w-3 h-3" />
                        {formatDate(sc.created_at)}
                      </span>
                    </div>

                    {sc.description && (
                      <p className="text-xs text-slate-600 leading-relaxed">{sc.description}</p>
                    )}

                    {parsedParams && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {parsedParams.salary_delta_pct !== 0 && (
                          <span className="text-2xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            Salary {parsedParams.salary_delta_pct > 0 ? `+${parsedParams.salary_delta_pct}%` : `${parsedParams.salary_delta_pct}%`}
                          </span>
                        )}
                        {parsedParams.rent_delta_inr !== 0 && (
                          <span className="text-2xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            Rent ₹{parsedParams.rent_delta_inr > 0 ? `+${parsedParams.rent_delta_inr.toLocaleString()}` : parsedParams.rent_delta_inr.toLocaleString()}
                          </span>
                        )}
                        {parsedParams.discretionary_reduction_pct !== 0 && (
                          <span className="text-2xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            Cut {parsedParams.discretionary_reduction_pct}%
                          </span>
                        )}
                        {parsedParams.new_recurring_monthly_inr !== 0 && (
                          <span className="text-2xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                            EMI +₹{parsedParams.new_recurring_monthly_inr.toLocaleString()}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 shrink-0">
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs font-semibold hover:border-teal-600 hover:text-teal-700"
                      onClick={() => {
                        if (parsedParams) {
                          onLoadScenario(parsedParams)
                          onClose()
                        }
                      }}
                    >
                      Load
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                    <button
                      onClick={() => onDeleteScenario(sc.id)}
                      title="Delete Scenario"
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
