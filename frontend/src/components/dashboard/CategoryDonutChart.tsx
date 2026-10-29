import React from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { CategorySpendItem } from '@/types'
import { formatINR } from '@/lib/formatters'

interface Props {
  data: CategorySpendItem[]
}

const DEFAULT_COLORS = ['#f43f5e', '#f97316', '#eab308', '#84cc16', '#3b82f6', '#ec4899', '#8b5cf6', '#64748b']

export const CategoryDonutChart: React.FC<Props> = ({ data }) => {
  const total = data.reduce((acc, curr) => acc + curr.spent_inr, 0)

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div>
        <h3 className="text-sm font-bold text-slate-900 tracking-tight">Spending by Category</h3>
        <p className="text-xs text-slate-500">Current month distribution</p>
      </div>

      <div className="h-56 relative flex items-center justify-center">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="spent_inr"
                nameKey="category_name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={3}
              >
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.category_color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]}
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const item = payload[0].payload as CategorySpendItem
                    return (
                      <div className="bg-navy-900 text-white p-2.5 rounded-lg shadow-xl text-xs space-y-1 border border-navy-700">
                        <p className="font-bold flex items-center space-x-1.5">
                          <span
                            className="w-2.5 h-2.5 rounded-full inline-block"
                            style={{ backgroundColor: item.category_color }}
                          />
                          <span>{item.category_name}</span>
                        </p>
                        <p className="text-slate-300 font-mono">{formatINR(item.spent_inr)} ({item.percentage}%)</p>
                      </div>
                    )
                  }
                  return null
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center text-xs text-slate-400">No expense records for this period</div>
        )}

        {/* Center label */}
        {total > 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Total</span>
            <span className="text-sm font-bold text-slate-800">{formatINR(total, { compact: true })}</span>
          </div>
        )}
      </div>

      {/* Legend chips */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 max-h-32 overflow-y-auto">
        {data.slice(0, 6).map((cat, idx) => (
          <div key={idx} className="flex items-center space-x-2 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: cat.category_color || DEFAULT_COLORS[idx % DEFAULT_COLORS.length] }}
            />
            <span className="text-slate-600 truncate">{cat.category_name}</span>
            <span className="text-slate-400 font-mono ml-auto">{cat.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
