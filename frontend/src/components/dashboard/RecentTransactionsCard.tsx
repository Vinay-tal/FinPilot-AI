import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, ArrowDownRight, Search, ExternalLink } from 'lucide-react'
import { Transaction } from '@/types'
import { formatINR, formatDate } from '@/lib/formatters'
import { Badge } from '../common/Badge'

interface Props {
  transactions: Transaction[]
}

export const RecentTransactionsCard: React.FC<Props> = ({ transactions }) => {
  const [searchTerm, setSearchTerm] = useState('')

  const filtered = transactions.filter((t) =>
    t.narration.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.merchant_name && t.merchant_name.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Recent Transactions</h3>
          <p className="text-xs text-slate-500">Live ledger movements</p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search recent..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 w-36 sm:w-48 transition-all"
            />
          </div>
          <Link
            to="/transactions"
            className="text-xs text-teal-700 hover:text-teal-800 font-semibold inline-flex items-center space-x-1 pl-1"
          >
            <span>View All</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      <div className="divide-y divide-slate-100 overflow-x-auto">
        {filtered.length > 0 ? (
          filtered.slice(0, 6).map((tx) => {
            const isCredit = tx.transaction_type === 'CREDIT'
            return (
              <div key={tx.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center space-x-3 min-w-0">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                      isCredit
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-100'
                        : 'bg-rose-50 text-rose-600 border-rose-100'
                    }`}
                  >
                    {isCredit ? (
                      <ArrowDownRight className="w-4 h-4" />
                    ) : (
                      <ArrowUpRight className="w-4 h-4" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 truncate">
                      {tx.merchant_name || tx.narration}
                    </p>
                    <div className="flex items-center space-x-2 mt-0.5 text-slate-500">
                      <span>{formatDate(tx.date)}</span>
                      <span>&bull;</span>
                      <span className="font-medium text-slate-400">{tx.payment_mode}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  {tx.category_name && (
                    <Badge color={tx.category_color} className="hidden sm:inline-flex">
                      {tx.category_name}
                    </Badge>
                  )}
                  <span
                    className={`font-mono font-bold text-sm ${
                      isCredit ? 'text-emerald-600' : 'text-slate-900'
                    }`}
                  >
                    {formatINR(tx.amount_inr, { showSign: isCredit })}
                  </span>
                </div>
              </div>
            )
          })
        ) : (
          <div className="py-8 text-center text-xs text-slate-400">No matching transactions found</div>
        )}
      </div>
    </div>
  )
}
