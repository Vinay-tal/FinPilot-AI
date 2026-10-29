import React from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ChevronRight, PieChart } from 'lucide-react'
import { Budget } from '@/types'
import { formatINR } from '@/lib/formatters'
import { Badge } from '../common/Badge'

interface Props {
  budgets: Budget[]
}

export const BudgetPacingList: React.FC<Props> = ({ budgets }) => {
  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Monthly Budget Pacing</h3>
          <p className="text-xs text-slate-500">Spend actuals vs allocated limits</p>
        </div>
        <Link
          to="/budgets"
          className="text-xs text-teal-700 hover:text-teal-800 font-semibold inline-flex items-center space-x-1"
        >
          <span>Manage</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="space-y-3.5">
        {budgets.slice(0, 4).map((b) => {
          const isExceeded = b.alert_status === 'EXCEEDED'
          const isWarning = b.alert_status === 'WARNING'

          const barColor = isExceeded ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-teal-500'

          return (
            <div key={b.id} className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-800">{b.category_name || 'Category'}</span>
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500 font-mono">
                    <strong className="text-slate-900">{formatINR(b.spent_inr, { hideDecimals: true })}</strong> /{' '}
                    {formatINR(b.amount_inr, { hideDecimals: true })}
                  </span>
                  <Badge variant={isExceeded ? 'danger' : isWarning ? 'warning' : 'success'}>
                    {b.pacing_pct}%
                  </Badge>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} rounded-full transition-all duration-300`}
                  style={{ width: `${Math.min(b.pacing_pct, 100)}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
