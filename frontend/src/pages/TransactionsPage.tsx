import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  Trash2,
  Calendar,
  ChevronLeft,
  ChevronRight,
  UploadCloud,
  MessageSquare,
  Edit2,
  Check,
  X,
  Sparkles,
} from 'lucide-react'
import {
  getTransactionsApi,
  createTransactionApi,
  deleteTransactionApi,
  reclassifyTransactionApi,
  TransactionFilterParams,
} from '@/api/transactions'
import { getAccountsApi } from '@/api/accounts'
import { getCategoriesApi } from '@/api/categories'
import { formatINR, formatDate } from '@/lib/formatters'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { AddTransactionModal } from '@/components/transactions/AddTransactionModal'
import { CSVImportModal } from '@/components/transactions/CSVImportModal'
import { SMSParserModal } from '@/components/transactions/SMSParserModal'
import { TableSkeleton } from '@/components/common/Skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { useToast } from '@/context/ToastContext'

export const TransactionsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [selectedAccount, setSelectedAccount] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false)
  const [isSmsModalOpen, setIsSmsModalOpen] = useState(false)

  // Reclassification state
  const [editingTxId, setEditingTxId] = useState<string | null>(null)
  const [editCategoryId, setEditCategoryId] = useState<string>('')

  const filterParams: TransactionFilterParams = {
    page,
    limit: 15,
    search: search.trim() || undefined,
    category_id: selectedCategory || undefined,
    type: selectedType || undefined,
    account_id: selectedAccount || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  }

  const {
    data: txResponse,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['transactions', filterParams],
    queryFn: () => getTransactionsApi(filterParams),
  })

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccountsApi,
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategoriesApi,
  })

  const createMutation = useMutation({
    mutationFn: async (formData: any) => {
      await createTransactionApi({
        account_id: formData.account_id,
        category_id: formData.category_id,
        date: formData.date,
        amount_paise: Math.round(formData.amount_inr * 100),
        transaction_type: formData.transaction_type,
        narration: formData.narration,
        payment_mode: formData.payment_mode,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
      queryClient.invalidateQueries({ queryKey: ['cashflowTrend'] })
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      toastSuccess('Transaction created and ledger balance updated!')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to create transaction.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTransactionApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
      toastSuccess('Transaction removed and account balance restored.')
    },
    onError: (err: any) => {
      toastError(err.message || 'Failed to delete transaction.')
    },
  })

  const reclassifyMutation = useMutation({
    mutationFn: ({ txId, categoryId }: { txId: string; categoryId: string }) =>
      reclassifyTransactionApi(txId, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['model-evaluation'] })
      setEditingTxId(null)
      toastSuccess('Category updated and recorded as training example!')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to update category.')
    },
  })

  const handleStartEdit = (txId: string, currentCatId: string) => {
    setEditingTxId(txId)
    setEditCategoryId(currentCatId)
  }

  const handleSaveReclassify = (txId: string) => {
    if (!editCategoryId) return
    reclassifyMutation.mutate({ txId, categoryId: editCategoryId })
  }

  return (
    <div className="space-y-6">
      {/* Header and Ingestion Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Transaction Explorer</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Complete financial ledger with multi-column filtering, statement imports, and SMS parsing
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Bank Statement CSV Importer */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsCsvModalOpen(true)}
            className="border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            <UploadCloud className="w-4 h-4 mr-1.5 text-teal-600" />
            Import Statement
          </Button>

          {/* SMS Transaction Parser */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSmsModalOpen(true)}
            className="border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            <MessageSquare className="w-4 h-4 mr-1.5 text-navy-600" />
            Parse Bank SMS
          </Button>

          {/* Add Manual Transaction */}
          <Button
            onClick={() => setIsAddModalOpen(true)}
            size="sm"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Add Transaction
          </Button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          {/* Search */}
          <div className="lg:col-span-2 relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search narration, merchant..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
          </div>

          {/* Category */}
          <div>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value)
                setPage(1)
              }}
              className="w-full px-2.5 py-2 text-xs rounded-lg border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 cursor-pointer"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Type */}
          <div>
            <select
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value)
                setPage(1)
              }}
              className="w-full px-2.5 py-2 text-xs rounded-lg border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 cursor-pointer"
            >
              <option value="">All Types</option>
              <option value="DEBIT">Debit (Outflow)</option>
              <option value="CREDIT">Credit (Inflow)</option>
            </select>
          </div>

          {/* Account */}
          <div>
            <select
              value={selectedAccount}
              onChange={(e) => {
                setSelectedAccount(e.target.value)
                setPage(1)
              }}
              className="w-full px-2.5 py-2 text-xs rounded-lg border border-slate-300 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 cursor-pointer"
            >
              <option value="">All Accounts</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Reset Filters */}
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearch('')
                setSelectedCategory('')
                setSelectedType('')
                setSelectedAccount('')
                setStartDate('')
                setEndDate('')
                setPage(1)
              }}
              className="w-full py-2 text-xs"
            >
              Reset Filters
            </Button>
          </div>
        </div>
      </div>

      {/* Main Ledger Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        {error ? (
          <div className="p-6">
            <ErrorAlert
              title="Error Loading Transactions"
              message={(error as Error).message}
              onRetry={() => refetch()}
            />
          </div>
        ) : isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={8} />
          </div>
        ) : txResponse && txResponse.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-4">Date</th>
                  <th className="py-3.5 px-4">Narration / Payee</th>
                  <th className="py-3.5 px-4">Category & Intelligence</th>
                  <th className="py-3.5 px-4">Account</th>
                  <th className="py-3.5 px-4">Instrument</th>
                  <th className="py-3.5 px-4 text-right">Amount (₹)</th>
                  <th className="py-3.5 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {txResponse.items.map((tx) => {
                  const isCredit = tx.transaction_type === 'CREDIT'
                  const isEditing = editingTxId === tx.id
                  const method = tx.categorization_method || 'RULE'
                  const conf = tx.categorization_confidence != null ? Math.round(tx.categorization_confidence * 100) : null

                  return (
                    <tr key={tx.id} className="hover:bg-slate-50/60 transition-colors">
                      {/* Date */}
                      <td className="py-3 px-4 text-slate-600 font-mono whitespace-nowrap">
                        {formatDate(tx.date)}
                      </td>

                      {/* Narration */}
                      <td className="py-3 px-4 max-w-xs truncate">
                        <span className="font-semibold text-slate-900 block truncate">
                          {tx.merchant_name || tx.narration}
                        </span>
                        {tx.merchant_name && tx.merchant_name !== tx.narration && (
                          <span className="text-[11px] text-slate-400 block truncate mt-0.5">
                            {tx.narration}
                          </span>
                        )}
                        {tx.reference_id && (
                          <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                            Ref: {tx.reference_id}
                          </span>
                        )}
                      </td>

                      {/* Category & Intelligence Metadata */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {isEditing ? (
                          <div className="flex items-center gap-1.5 animate-in fade-in">
                            <select
                              value={editCategoryId}
                              onChange={(e) => setEditCategoryId(e.target.value)}
                              className="text-xs rounded border border-teal-500 px-2 py-1 bg-white text-slate-900 focus:outline-none"
                            >
                              {categories.map((c) => (
                                <option key={c.id} value={c.id}>
                                  {c.name}
                                </option>
                              ))}
                            </select>
                            <button
                              onClick={() => handleSaveReclassify(tx.id)}
                              className="p-1 bg-teal-600 text-white rounded hover:bg-teal-700 transition-colors"
                              title="Save Correction"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setEditingTxId(null)}
                              className="p-1 bg-slate-200 text-slate-600 rounded hover:bg-slate-300 transition-colors"
                              title="Cancel"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleStartEdit(tx.id, tx.category_id)}
                              className="group inline-flex items-center gap-1 hover:opacity-85 transition-opacity"
                              title="Click to reclassify category (records training feedback)"
                            >
                              <Badge color={tx.category_color}>{tx.category_name || 'Uncategorized'}</Badge>
                              <Edit2 className="w-3 h-3 text-slate-300 group-hover:text-slate-600 transition-colors" />
                            </button>

                            {/* Categorization Source Badge */}
                            {method === 'MANUAL' ? (
                              <span
                                className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
                                title="Verified by user manual correction. Protected from automated overwrite."
                              >
                                User Verified
                              </span>
                            ) : method === 'ML' ? (
                              <span
                                className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200"
                                title={`Predicted by TF-IDF & Logistic Regression classifier (${conf}% confidence)`}
                              >
                                ML {conf ? `${conf}%` : ''}
                              </span>
                            ) : (
                              <span
                                className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200"
                                title="Matched via deterministic keyword & merchant rule"
                              >
                                Rule
                              </span>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Account */}
                      <td className="py-3 px-4 text-slate-600 font-medium whitespace-nowrap">
                        {tx.account_name || 'Account'}
                      </td>

                      {/* Instrument */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-medium border border-slate-200">
                          {tx.payment_mode}
                        </span>
                      </td>

                      {/* Amount */}
                      <td className="py-3 px-4 text-right font-mono font-bold whitespace-nowrap text-sm">
                        <span className={isCredit ? 'text-emerald-600' : 'text-slate-900'}>
                          {formatINR(tx.amount_inr, { showSign: isCredit })}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <button
                          onClick={() => {
                            if (window.confirm('Delete this transaction? The account balance will be reversed.')) {
                              deleteMutation.mutate(tx.id)
                            }
                          }}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                          title="Delete Transaction"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {/* Pagination footer */}
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50/50 border-t border-slate-200 text-xs">
              <span className="text-slate-500">
                Showing{' '}
                <strong className="text-slate-900 font-mono">
                  {(page - 1) * 15 + 1} - {Math.min(page * 15, txResponse.total)}
                </strong>{' '}
                of <strong className="text-slate-900 font-mono">{txResponse.total}</strong> transactions
              </span>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="px-2 py-1 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Previous
                </Button>
                <span className="px-2 font-mono font-semibold text-slate-700">
                  {page} / {txResponse.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= txResponse.total_pages}
                  onClick={() => setPage((p) => Math.min(p + 1, txResponse.total_pages))}
                  className="px-2 py-1 text-xs"
                >
                  Next <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No transactions found"
            description="Try adjusting your search criteria or import your bank statement to get started."
            actionLabel="Import Statement"
            onAction={() => setIsCsvModalOpen(true)}
          />
        )}
      </div>

      {/* Manual Add Modal */}
      <AddTransactionModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={async (data) => createMutation.mutateAsync(data)}
        accounts={accounts}
        categories={categories}
        isLoading={createMutation.isPending}
      />

      {/* CSV Statement Importer Modal */}
      <CSVImportModal
        isOpen={isCsvModalOpen}
        onClose={() => setIsCsvModalOpen(false)}
        accounts={accounts}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['transactions'] })
          queryClient.invalidateQueries({ queryKey: ['accounts'] })
          queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
        }}
      />

      {/* SMS Bank Parser Modal */}
      <SMSParserModal
        isOpen={isSmsModalOpen}
        onClose={() => setIsSmsModalOpen(false)}
        accounts={accounts}
        categories={categories}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['transactions'] })
          queryClient.invalidateQueries({ queryKey: ['accounts'] })
          queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] })
        }}
      />
    </div>
  )
}
