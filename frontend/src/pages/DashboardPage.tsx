import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Wallet,
  TrendingUp,
  CreditCard,
  PiggyBank,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  TrendingDown,
  Calendar,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDashboardSummaryApi, getCashflowTrendApi, getCategoryBreakdownApi } from '@/api/dashboard'
import { getBudgetsApi } from '@/api/budgets'
import { getRecurringApi } from '@/api/recurring'
import { getInsightsApi } from '@/api/insights'
import { formatINR, formatPercent } from '@/lib/formatters'
import { StatCard } from '@/components/common/StatCard'
import { CashflowTrendChart } from '@/components/dashboard/CashflowTrendChart'
import { CategoryDonutChart } from '@/components/dashboard/CategoryDonutChart'
import { HealthScoreCard } from '@/components/dashboard/HealthScoreCard'
import { RecentTransactionsCard } from '@/components/dashboard/RecentTransactionsCard'
import { BudgetPacingList } from '@/components/dashboard/BudgetPacingList'
import { RecurringBillsList } from '@/components/dashboard/RecurringBillsList'
import { CardSkeleton } from '@/components/common/Skeleton'
import { ErrorAlert } from '@/components/common/ErrorAlert'

export const DashboardPage: React.FC = () => {
  const [period, setPeriod] = useState<string>('current_month')

  const {
    data: summary,
    isLoading: isSummaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['dashboardSummary', period],
    queryFn: () => getDashboardSummaryApi(period),
  })

  const { data: trendData = [], isLoading: isTrendLoading } = useQuery({
    queryKey: ['cashflowTrend'],
    queryFn: () => getCashflowTrendApi(6),
  })

  const { data: categoryData = [], isLoading: isCategoryLoading } = useQuery({
    queryKey: ['categoryBreakdown', period],
    queryFn: () => getCategoryBreakdownApi(period),
  })

  const { data: budgets = [] } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => getBudgetsApi(),
  })

  const { data: recurring = [] } = useQuery({
    queryKey: ['recurring'],
    queryFn: () => getRecurringApi(),
  })

  const { data: activeInsights = [] } = useQuery({
    queryKey: ['insights', 'active'],
    queryFn: () => getInsightsApi(false),
  })

  if (summaryError) {
    return (
      <ErrorAlert
        title="Could not load dashboard telemetry"
        message={(summaryError as Error).message}
        onRetry={() => refetchSummary()}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Period Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Executive Financial Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time multi-account tracking, budget pacing, and AI recommendations
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-700 cursor-pointer"
          >
            <option value="current_month">Current Month</option>
            <option value="last_30_days">Last 30 Days</option>
            <option value="last_90_days">Last 90 Days</option>
            <option value="ytd">Year to Date (YTD)</option>
          </select>
        </div>
      </div>

      {/* Primary KPI Grid (4 Metrics) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isSummaryLoading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : summary ? (
          <>
            <StatCard
              title="Liquid Bank Assets"
              value={formatINR(summary.total_liquid_balance_inr)}
              subtitle={`${summary.accounts_count} Accounts Connected`}
              icon={<Wallet className="w-5 h-5" />}
              accentColor="teal"
            />
            <StatCard
              title="Period Total Income"
              value={formatINR(summary.total_income_inr)}
              change={{ value: '+100%', isPositive: true, label: 'Inflows' }}
              icon={<TrendingUp className="w-5 h-5" />}
              accentColor="emerald"
            />
            <StatCard
              title="Period Total Expenses"
              value={formatINR(summary.total_expenses_inr)}
              change={{ value: 'Outflow', isPositive: false }}
              subtitle={`${summary.transactions_count} total postings`}
              icon={<TrendingDown className="w-5 h-5" />}
              accentColor="rose"
            />
            <StatCard
              title="Net Savings & Rate"
              value={formatINR(summary.net_savings_inr, { showSign: true })}
              subtitle={`Savings Rate: ${formatPercent(summary.savings_rate)}`}
              icon={<PiggyBank className="w-5 h-5" />}
              accentColor="indigo"
            />
          </>
        ) : null}
      </div>

      {/* High-Priority Anomaly Alert Banner (if any) */}
      {activeInsights.length > 0 && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/80 flex items-start justify-between gap-3 shadow-xs">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 border border-amber-200 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">
                  {activeInsights[0].insight_type.replace('_', ' ')}
                </h4>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                <span className="text-xs font-medium text-amber-800">{activeInsights[0].title}</span>
              </div>
              <p className="text-xs text-amber-700 mt-0.5 leading-relaxed">
                {activeInsights[0].description}
              </p>
            </div>
          </div>
          <Link
            to="/insights"
            className="text-xs font-bold text-amber-900 hover:text-amber-950 inline-flex items-center space-x-1 shrink-0 pt-1 hover:underline"
          >
            <span>Review Anomaly</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Main Charts Row: Cashflow Trend (2/3) + Donut (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {isTrendLoading ? <CardSkeleton /> : <CashflowTrendChart data={trendData} />}
        </div>
        <div className="lg:col-span-1">
          {isCategoryLoading ? <CardSkeleton /> : <CategoryDonutChart data={categoryData} />}
        </div>
      </div>

      {/* Middle Row: Recent Transactions (2/3) + Health Score & Forecast (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {summary ? (
            <RecentTransactionsCard transactions={summary.recent_transactions} />
          ) : (
            <CardSkeleton />
          )}
        </div>
        <div className="lg:col-span-1 space-y-6">
          {summary ? (
            <HealthScoreCard
              score={summary.health_score}
              grade={summary.health_grade}
              savingsRate={summary.savings_rate}
              liquidPaise={summary.total_liquid_balance_paise}
            />
          ) : (
            <CardSkeleton />
          )}
        </div>
      </div>

      {/* Bottom Row: Budgets Pacing & Recurring Bills */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BudgetPacingList budgets={budgets} />
        <RecurringBillsList recurring={recurring} />
      </div>
    </div>
  )
}
