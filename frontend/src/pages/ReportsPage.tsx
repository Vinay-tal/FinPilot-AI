import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FileSpreadsheet,
  Download,
  Printer,
  Calendar,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  PieChart as PieIcon,
  ShieldCheck,
  Target,
  Sparkles,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react'
import { getMonthlyReportApi, downloadReportCsvApi } from '@/api/planning'
import { Button } from '@/components/common/Button'
import { Skeleton } from '@/components/common/Skeleton'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { formatINR, formatPercent, formatDateIST } from '@/lib/formatters'
import { useToast } from '@/context/ToastContext'
import { MonthlyReportResponse } from '@/types'

export const ReportsPage: React.FC = () => {
  const today = new Date()
  const [month, setMonth] = useState<number>(today.getMonth() + 1)
  const [year, setYear] = useState<number>(today.getFullYear())
  const [isExportingCSV, setIsExportingCSV] = useState(false)
  const { success: toastSuccess, error: toastError } = useToast()

  const {
    data: report,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<MonthlyReportResponse>({
    queryKey: ['monthlyReport', month, year],
    queryFn: () => getMonthlyReportApi(month, year),
  })

  // Export CSV handler
  const handleExportCSV = async () => {
    try {
      setIsExportingCSV(true)
      await downloadReportCsvApi(month, year)
      toastSuccess('Monthly report CSV downloaded successfully!')
    } catch (err: any) {
      toastError(err?.message || 'Failed to download report CSV.')
    } finally {
      setIsExportingCSV(false)
    }
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Monthly Financial Dossier &amp; Reports
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              Audit &amp; Intelligence
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-0.5">
            Comprehensive audit reports reconciling cashflows, category budgets, forecasts, anomalies, and recommendations.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            isLoading={isExportingCSV}
            className="text-xs font-semibold"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Export CSV
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handlePrint}
            className="text-xs font-semibold"
          >
            <Printer className="w-4 h-4 mr-1.5" />
            Print / PDF
          </Button>
        </div>
      </div>

      {/* Month / Year Selector */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between print:hidden">
        <div className="flex items-center space-x-2">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
            Statement Period:
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          >
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
              <option key={m} value={m}>
                {new Date(2026, m - 1, 1).toLocaleString('default', { month: 'long' })}
              </option>
            ))}
          </select>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          >
            {[2024, 2025, 2026, 2027].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Report Container (printable) */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-6 sm:p-8 space-y-8 print:border-none print:shadow-none print:p-0">
        {/* Document Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="w-9 h-9 rounded-lg bg-teal-600 text-white font-bold flex items-center justify-center text-sm shadow-xs">
                FP
              </span>
              <div>
                <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                  FinPilot AI Monthly Financial Statement
                </h2>
                <p className="text-xs text-slate-500">
                  Certified Cashflow Audit, Category Performance &amp; Advisory Dossier
                </p>
              </div>
            </div>
          </div>

          <div className="text-left sm:text-right space-y-0.5">
            <p className="text-xs font-medium text-slate-500">
              Period:{' '}
              <span className="font-bold text-slate-800">
                {report?.month_label || `${month}/${year}`}
              </span>
            </p>
            <p className="text-[11px] text-slate-400">
              Generated: {report ? formatDateIST(report.generated_at) : formatDateIST(new Date().toISOString())}
            </p>
          </div>
        </div>

        {isError ? (
          <ErrorAlert
            title="Failed to generate statement report"
            message={error instanceof Error ? error.message : 'Please try again.'}
            onRetry={() => refetch()}
          />
        ) : isLoading || !report ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
        ) : (
          <>
            {/* Core Financial Summary KPIs */}
            <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                1. Monthly Cashflow &amp; Wealth Metrics
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Inflows</p>
                  <p className="text-xl font-bold text-emerald-600 mt-1">{formatINR(report.total_income_inr)}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Salary &amp; Credits</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Outflows</p>
                  <p className="text-xl font-bold text-rose-600 mt-1">{formatINR(report.total_expenses_inr)}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">{report.transactions_count} Transactions</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Net Savings</p>
                  <p className="text-xl font-bold text-teal-700 mt-1">{formatINR(report.net_savings_inr)}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Retained Capital</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Savings Rate</p>
                  <p className="text-xl font-bold text-slate-900 mt-1">{report.savings_rate_pct.toFixed(1)}%</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Target &ge; 30%</p>
                </div>
              </div>
            </div>

            {/* Category Breakdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                  <PieIcon className="w-4 h-4 mr-2 text-teal-600" />
                  2. Category Outflow Breakdown &amp; MoM Shift
                </h3>
                <span className="text-xs text-slate-400">
                  {report.category_breakdown.length} Categories Active
                </span>
              </div>

              {report.category_breakdown.length === 0 ? (
                <p className="text-xs text-slate-500 py-3 text-center">No category spending recorded for this period.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase text-2xs tracking-wider">
                        <th className="py-2.5 px-3 font-semibold">Category</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Amount (INR)</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Share</th>
                        <th className="py-2.5 px-3 text-right font-semibold">MoM Variance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {report.category_breakdown.map((c) => (
                        <tr key={c.category_name} className="hover:bg-slate-50/50">
                          <td className="py-2.5 px-3 text-slate-900 font-semibold flex items-center space-x-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: c.category_color || '#0D9488' }}
                            />
                            <span>{c.category_name}</span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                            {formatINR(c.spent_inr)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {c.share_pct.toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono">
                            <span
                              className={
                                c.mom_change_inr > 0
                                  ? 'text-rose-600 font-semibold'
                                  : c.mom_change_inr < 0
                                  ? 'text-emerald-600 font-semibold'
                                  : 'text-slate-500'
                              }
                            >
                              {c.mom_change_inr > 0 ? `+${formatINR(c.mom_change_inr)}` : formatINR(c.mom_change_inr)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Budget Performance */}
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                  <Target className="w-4 h-4 mr-2 text-teal-600" />
                  3. Budget Adherence &amp; Pacing
                </h3>
                <span className="text-xs text-slate-400">
                  Utilization: <strong>{report.budget_utilization_pct.toFixed(1)}%</strong>
                </span>
              </div>

              {report.budget_performance.length === 0 ? (
                <p className="text-xs text-slate-500 py-3 text-center">
                  No budgets configured for this month. Set budgets in the Budgets module to track adherence.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase text-2xs tracking-wider">
                        <th className="py-2.5 px-3 font-semibold">Category</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Budgeted</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Actual Spent</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Variance</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Pacing</th>
                        <th className="py-2.5 px-3 text-right font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-medium">
                      {report.budget_performance.map((b) => (
                        <tr key={b.category_name} className="hover:bg-slate-50/50">
                          <td className="py-2.5 px-3 font-semibold text-slate-900">{b.category_name}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                            {formatINR(b.budgeted_inr)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-900 font-bold">
                            {formatINR(b.spent_inr)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono">
                            <span className={b.variance_inr < 0 ? 'text-rose-600 font-semibold' : 'text-emerald-600'}>
                              {formatINR(b.variance_inr)}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {b.pacing_pct.toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <span
                              className={`px-2 py-0.5 rounded text-2xs font-semibold ${
                                b.status === 'EXCEEDED'
                                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : b.status === 'WARNING'
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                            >
                              {b.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Forecast vs Actual Reconciliation */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-100 pb-2">
                4. Forecast Model vs. Actual Balance Reconciliation
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                  <p className="text-xs text-slate-500">Current Liquid Balance</p>
                  <p className="text-lg font-bold text-slate-900 mt-1">
                    {formatINR(report.total_liquid_balance_inr)}
                  </p>
                  <p className="text-2xs text-slate-400 mt-0.5">Across {report.accounts_count} Accounts</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                  <p className="text-xs text-slate-500">Predicted Month-End Balance</p>
                  <p className="text-lg font-bold text-teal-700 mt-1">
                    {report.forecast_month_end_balance_inr
                      ? formatINR(report.forecast_month_end_balance_inr)
                      : 'N/A'}
                  </p>
                  <p className="text-2xs text-slate-400 mt-0.5">ML / Hybrid Pipeline</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                  <p className="text-xs text-slate-500">Forecast vs Actual Variance</p>
                  <p className="text-lg font-bold text-slate-900 mt-1 font-mono">
                    {report.actual_vs_forecast_delta_inr !== undefined
                      ? formatINR(report.actual_vs_forecast_delta_inr)
                      : 'On Track'}
                  </p>
                  <p className="text-2xs text-slate-400 mt-0.5">Projection Gap</p>
                </div>
              </div>
            </div>

            {/* Anomalies Detected & Recommendation History */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Anomalies */}
              <div className="bg-slate-50 p-5 rounded-xl border border-slate-200/80 space-y-3">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                    5. Detected Anomalies &amp; Outliers
                  </h4>
                </div>
                {report.anomalies_detected.length === 0 ? (
                  <p className="text-xs text-slate-500 py-2">
                    No high-severity anomalous transactions detected for this period.
                  </p>
                ) : (
                  <ul className="space-y-1.5 text-xs text-slate-700">
                    {report.anomalies_detected.map((anomaly, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                        <span>{anomaly}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Recommendation Lifecycle Summary */}
              <div className="bg-slate-50 p-5 rounded-xl border border-slate-200/80 space-y-3">
                <div className="flex items-center space-x-2">
                  <Lightbulb className="w-4 h-4 text-teal-600" />
                  <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wider">
                    6. Personalized Recommendation Lifecycle
                  </h4>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                    <p className="text-slate-400 text-2xs uppercase">New / Active</p>
                    <p className="text-base font-bold text-teal-700 font-mono">
                      {report.recommendation_summary['new'] || 0}
                    </p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                    <p className="text-slate-400 text-2xs uppercase">Accepted</p>
                    <p className="text-base font-bold text-emerald-600 font-mono">
                      {report.recommendation_summary['accepted'] || 0}
                    </p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                    <p className="text-slate-400 text-2xs uppercase">Completed</p>
                    <p className="text-base font-bold text-slate-800 font-mono">
                      {report.recommendation_summary['completed'] || 0}
                    </p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200 text-center">
                    <p className="text-slate-400 text-2xs uppercase">Dismissed</p>
                    <p className="text-base font-bold text-slate-400 font-mono">
                      {report.recommendation_summary['dismissed'] || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Disclaimer & Verification Footer */}
            <div className="pt-6 border-t border-slate-200 text-slate-400 text-[11px] leading-relaxed flex flex-col sm:flex-row justify-between gap-4">
              <div>
                <p className="font-semibold text-slate-500 uppercase tracking-wider">
                  Audit &amp; Reconciliation Protocol
                </p>
                <p className="mt-0.5">
                  FinPilot AI stores all values in minor units (paise) with exact integer arithmetic.
                  This monthly report is an educational heuristic and planning aid, not an audited bank balance certificate.
                </p>
              </div>
              <div className="sm:text-right shrink-0">
                <span className="inline-flex items-center text-teal-700 font-semibold bg-teal-50 px-2.5 py-1 rounded-md border border-teal-200">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1 text-teal-600" />
                  Verified FinPilot Dossier
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
