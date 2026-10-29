import React from 'react'
import { Calendar, Repeat, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { RecurringTransaction } from '@/types'
import { formatINR, formatDate } from '@/lib/formatters'
import { Badge } from '../common/Badge'

interface Props {
  recurring?: RecurringTransaction[]
}

export const RecurringBillsList: React.FC<Props> = ({ recurring = [] }) => {
  const getDaysLeft = (dateStr: string) => {
    const today = new Date()
    const target = new Date(dateStr)
    const diffTime = target.getTime() - today.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return 'Due today'
    if (diffDays === 1) return 'Due tomorrow'
    if (diffDays > 0) return `In ${diffDays} days`
    return `${Math.abs(diffDays)}d ago`
  }

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Upcoming Recurring Bills & SIPs</h3>
          <p className="text-xs text-slate-500">Scheduled commitments next 30 days</p>
        </div>
        <Repeat className="w-4 h-4 text-slate-400" />
      </div>

      <div className="divide-y divide-slate-100">
        {recurring.slice(0, 5).map((r) => {
          const isSalary = r.name.toLowerCase().includes('salary')
          return (
            <div key={r.id} className="py-2.5 flex items-center justify-between text-xs">
              <div className="space-y-0.5 min-w-0">
                <p className="font-semibold text-slate-900 truncate">{r.name}</p>
                <div className="flex items-center space-x-2 text-slate-500">
                  <span className="text-[11px] font-medium text-teal-700 bg-teal-50 px-1.5 py-0.2 rounded">
                    {getDaysLeft(r.next_expected_date)}
                  </span>
                  <span>&bull;</span>
                  <span className="text-slate-400">{formatDate(r.next_expected_date)}</span>
                </div>
              </div>

              <div className="text-right">
                <span
                  className={`font-mono font-bold text-sm ${
                    isSalary ? 'text-emerald-600' : 'text-slate-900'
                  }`}
                >
                  {formatINR(r.expected_amount_inr, { showSign: isSalary })}
                </span>
                <p className="text-[10px] text-slate-400 uppercase tracking-wider">{r.frequency}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
