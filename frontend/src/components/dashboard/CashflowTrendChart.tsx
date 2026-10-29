import React from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { CashflowTrendItem } from '@/types'
import { formatINR } from '@/lib/formatters'

interface Props {
  data: CashflowTrendItem[]
}

export const CashflowTrendChart: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Income vs Expenses Trend</h3>
          <p className="text-xs text-slate-500">6-Month historical cash-flow trajectory</p>
        </div>
      </div>

      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="month"
              stroke="#94a3b8"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis
              stroke="#94a3b8"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const inc = payload.find((p) => p.dataKey === 'income_inr')?.value as number
                  const exp = payload.find((p) => p.dataKey === 'expenses_inr')?.value as number
                  const net = inc - exp
                  return (
                    <div className="bg-navy-900 text-white p-3 rounded-xl shadow-xl text-xs space-y-1.5 border border-navy-700 min-w-44">
                      <p className="font-bold text-slate-200 border-b border-navy-800 pb-1">{label}</p>
                      <div className="flex justify-between items-center text-emerald-400">
                        <span>Income:</span>
                        <span className="font-mono font-semibold">{formatINR(inc)}</span>
                      </div>
                      <div className="flex justify-between items-center text-rose-400">
                        <span>Expenses:</span>
                        <span className="font-mono font-semibold">{formatINR(exp)}</span>
                      </div>
                      <div className="flex justify-between items-center pt-1 border-t border-navy-800 text-teal-300 font-bold">
                        <span>Net Surplus:</span>
                        <span className="font-mono">{formatINR(net, { showSign: true })}</span>
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }}
            />
            <Area
              type="monotone"
              dataKey="income_inr"
              name="Income"
              stroke="#10b981"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#incomeGradient)"
            />
            <Area
              type="monotone"
              dataKey="expenses_inr"
              name="Expenses"
              stroke="#f43f5e"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#expenseGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
