import React from 'react'
import { ShieldCheck, TrendingUp, AlertCircle, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface HealthScoreCardProps {
  score: number
  grade: string
  savingsRate?: number
  liquidPaise?: number
}

export const HealthScoreCard: React.FC<HealthScoreCardProps> = ({
  score,
  grade,
  savingsRate = 20,
  liquidPaise = 15000000,
}) => {
  const getGradeColor = () => {
    if (score >= 80) return 'text-emerald-600 bg-emerald-50 border-emerald-200'
    if (score >= 65) return 'text-teal-600 bg-teal-50 border-teal-200'
    if (score >= 50) return 'text-amber-600 bg-amber-50 border-amber-200'
    return 'text-rose-600 bg-rose-50 border-rose-200'
  }

  // Calculate transparent sub-pillar points
  const savingsPillar = Math.min(25, Math.round((savingsRate / 20.0) * 25))
  const liquidityPillar = liquidPaise > 15000000 ? 25 : Math.round((liquidPaise / 15000000) * 25)
  const budgetPillar = 20
  const debtPillar = 20

  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Financial Health Score</h3>
          <p className="text-xs text-slate-500">Holistic Indian financial stability metric</p>
        </div>
        <span className={cn('px-2.5 py-1 rounded-full text-xs font-bold border', getGradeColor())}>
          {grade}
        </span>
      </div>

      {/* Main Score Radial/Indicator */}
      <div className="flex items-center space-x-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
        <div className="relative flex items-center justify-center w-16 h-16 rounded-full bg-white border-4 border-teal-500 shadow-xs shrink-0">
          <span className="text-2xl font-black text-slate-900">{score}</span>
        </div>
        <div className="space-y-1">
          <p className="text-xs font-semibold text-slate-700">Composite Score out of 100</p>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            {score >= 80
              ? 'Excellent stability! Your disciplined savings rate and low debt keep your finances resilient.'
              : 'Good progress. Build your emergency liquid reserves to 6 months to reach top tier.'}
          </p>
        </div>
      </div>

      {/* Sub-Pillars */}
      <div className="space-y-2.5 pt-1 text-xs">
        <div>
          <div className="flex justify-between text-slate-600 font-medium mb-1">
            <span>Savings Discipline (Target: &ge;20%)</span>
            <span className="font-mono text-slate-900 font-semibold">{savingsPillar}/25</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${(savingsPillar / 25) * 100}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-slate-600 font-medium mb-1">
            <span>Emergency Runway (Liquid Assets)</span>
            <span className="font-mono text-slate-900 font-semibold">{liquidityPillar}/25</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 rounded-full transition-all duration-500"
              style={{ width: `${(liquidityPillar / 25) * 100}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-slate-600 font-medium mb-1">
            <span>Budget Control & Pacing</span>
            <span className="font-mono text-slate-900 font-semibold">{budgetPillar}/25</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-500"
              style={{ width: `${(budgetPillar / 25) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Quick link */}
      <Link
        to="/copilot"
        className="block text-center text-xs font-semibold text-teal-700 hover:text-teal-800 pt-2 border-t border-slate-100 hover:underline"
      >
        Ask AI Copilot how to reach 95+ score &rarr;
      </Link>
    </div>
  )
}
