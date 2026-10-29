import React, { useState, useRef } from 'react'
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  History,
  FileText,
  RefreshCw,
  Info,
} from 'lucide-react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import {
  previewCsvStatementApi,
  importCsvStatementApi,
  listImportJobsApi,
  getJobErrorsDownloadUrl,
} from '@/api/ingestion'
import {
  FinancialAccount,
  CSVPreviewResponse,
  CSVImportResult,
  ImportJobItem,
} from '@/types'
import { formatINR } from '@/lib/formatters'
import { useToast } from '@/context/ToastContext'

interface Props {
  isOpen: boolean
  onClose: () => void
  accounts: FinancialAccount[]
  onSuccess: () => void
}

export const CSVImportModal: React.FC<Props> = ({
  isOpen,
  onClose,
  accounts,
  onSuccess,
}) => {
  const { success: toastSuccess, error: toastError } = useToast()

  const [activeTab, setActiveTab] = useState<'import' | 'history'>('import')
  const [selectedAccountId, setSelectedAccountId] = useState(
    accounts[0]?.id || ''
  )

  React.useEffect(() => {
    if (!selectedAccountId && accounts.length > 0) {
      setSelectedAccountId(accounts[0].id)
    }
  }, [accounts, selectedAccountId])

  const [bankPreset, setBankPreset] = useState<'GENERIC' | 'HDFC' | 'ICICI' | 'SBI' | 'AXIS'>('GENERIC')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [isImportLoading, setIsImportLoading] = useState(false)
  const [previewData, setPreviewData] = useState<CSVPreviewResponse | null>(null)
  const [importResult, setImportResult] = useState<CSVImportResult | null>(null)

  // Column mapping state
  const [columnMapping, setColumnMapping] = useState<{
    date_col: string
    narration_col: string
    debit_col: string
    credit_col: string
    amount_col: string
    balance_col: string
  }>({
    date_col: '',
    narration_col: '',
    debit_col: '',
    credit_col: '',
    amount_col: '',
    balance_col: '',
  })

  // History state
  const [importJobs, setImportJobs] = useState<ImportJobItem[]>([])
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const resetImportState = () => {
    setSelectedFile(null)
    setPreviewData(null)
    setImportResult(null)
    setColumnMapping({
      date_col: '',
      narration_col: '',
      debit_col: '',
      credit_col: '',
      amount_col: '',
      balance_col: '',
    })
  }

  const handleModalClose = () => {
    resetImportState()
    setActiveTab('import')
    onClose()
  }

  const handleFileSelect = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toastError('Please select a valid CSV (.csv) file.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      toastError('File size exceeds the 10 MB limit.')
      return
    }

    setSelectedFile(file)
    setImportResult(null)
    await generatePreview(file)
  }

  const generatePreview = async (file: File) => {
    const accId = selectedAccountId || accounts[0]?.id
    if (!accId) {
      toastError('Please choose a bank account first.')
      return
    }
    if (!selectedAccountId) {
      setSelectedAccountId(accId)
    }
    setIsPreviewLoading(true)
    try {
      const preview = await previewCsvStatementApi(accId, file)
      setPreviewData(preview)

      // Apply suggested mapping
      setColumnMapping({
        date_col: preview.suggested_mapping.date_col || '',
        narration_col: preview.suggested_mapping.narration_col || '',
        debit_col: preview.suggested_mapping.debit_col || '',
        credit_col: preview.suggested_mapping.credit_col || '',
        amount_col: preview.suggested_mapping.amount_col || '',
        balance_col: preview.suggested_mapping.balance_col || '',
      })
    } catch (err: any) {
      toastError(err?.message || 'Failed to generate preview for statement.')
      setPreviewData(null)
    } finally {
      setIsPreviewLoading(false)
    }
  }

  const handleExecuteImport = async () => {
    const accId = selectedAccountId || accounts[0]?.id
    if (!selectedFile || !accId) return

    if (!columnMapping.date_col) {
      toastError('Please map the Date column.')
      return
    }
    if (!columnMapping.narration_col) {
      toastError('Please map the Narration/Description column.')
      return
    }
    if (!columnMapping.amount_col && !columnMapping.debit_col && !columnMapping.credit_col) {
      toastError('Please map at least an Amount column or Debit/Credit columns.')
      return
    }

    setIsImportLoading(true)
    try {
      const result = await importCsvStatementApi(
        accId,
        columnMapping,
        bankPreset,
        selectedFile
      )
      setImportResult(result)
      toastSuccess(`Import completed! ${result.imported_rows} new transactions recorded.`)
      onSuccess()
    } catch (err: any) {
      toastError(err?.message || 'Failed to import CSV statement.')
    } finally {
      setIsImportLoading(false)
    }
  }

  const loadImportHistory = async () => {
    setIsHistoryLoading(true)
    try {
      const jobs = await listImportJobsApi()
      setImportJobs(jobs)
    } catch (err: any) {
      toastError(err?.message || 'Failed to load import history.')
    } finally {
      setIsHistoryLoading(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleModalClose}
      title="CSV Bank Statement Importer"
      description="Upload and ingest bank statements with smart column mapping and safe deduplication"
      maxWidth="4xl"
    >
      <div className="space-y-5">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setActiveTab('import')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'import'
                ? 'bg-navy-900 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Statement Ingestion
          </button>
          <button
            onClick={() => {
              setActiveTab('history')
              loadImportHistory()
            }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'bg-navy-900 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Audit History & Errors
          </button>
        </div>

        {activeTab === 'import' ? (
          <div className="space-y-5">
            {/* Account & Preset Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Destination Bank Account <span className="text-rose-500">*</span>
                </label>
                <select
                  value={selectedAccountId}
                  onChange={(e) => {
                    setSelectedAccountId(e.target.value)
                    if (selectedFile) generatePreview(selectedFile)
                  }}
                  className="w-full text-xs rounded-lg border border-slate-300 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.institution}) — {formatINR(acc.balance_inr)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Bank Format Preset
                </label>
                <div className="grid grid-cols-5 gap-1.5">
                  {(['GENERIC', 'HDFC', 'ICICI', 'SBI', 'AXIS'] as const).map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setBankPreset(fmt)}
                      className={`py-1.5 text-[11px] font-semibold rounded border transition-all ${
                        bankPreset === fmt
                          ? 'bg-teal-50 border-teal-500 text-teal-800 shadow-xs'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Drag and Drop Zone */}
            {!selectedFile ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setIsDragging(false)
                  if (e.dataTransfer.files?.[0]) {
                    handleFileSelect(e.dataTransfer.files[0])
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  isDragging
                    ? 'border-teal-500 bg-teal-50/50'
                    : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFileSelect(e.target.files[0])
                  }}
                />
                <div className="w-12 h-12 mx-auto rounded-full bg-teal-100 text-teal-700 flex items-center justify-center mb-3">
                  <FileSpreadsheet className="w-6 h-6" />
                </div>
                <p className="text-sm font-semibold text-slate-800">
                  Drop your bank CSV statement here, or <span className="text-teal-600 underline">browse</span>
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supports standard CSV statements up to 10 MB (HDFC, ICICI, SBI, Axis, or Generic)
                </p>
                <div className="mt-3 flex items-center justify-center gap-3 text-[11px] text-slate-500">
                  <span>Sample files for testing:</span>
                  <a
                    href="/hdfc_sample_statement.csv"
                    download
                    onClick={(e) => e.stopPropagation()}
                    className="text-teal-700 hover:text-teal-800 underline font-semibold"
                  >
                    HDFC Sample CSV
                  </a>
                  <span>•</span>
                  <a
                    href="/statement_with_errors.csv"
                    download
                    onClick={(e) => e.stopPropagation()}
                    className="text-rose-700 hover:text-rose-800 underline font-semibold"
                  >
                    Statement with Errors CSV
                  </a>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-800">{selectedFile.name}</p>
                    <p className="text-[11px] text-slate-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Detected Encoding:{' '}
                      <span className="font-mono text-slate-700">{previewData?.encoding || 'UTF-8'}</span>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      resetImportState()
                      fileInputRef.current?.click()
                    }}
                  >
                    Change File
                  </Button>
                </div>
              </div>
            )}

            {/* Preview Loading State */}
            {isPreviewLoading && (
              <div className="p-8 text-center">
                <RefreshCw className="w-6 h-6 text-teal-600 animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-600">Analyzing statement structure and detecting columns...</p>
              </div>
            )}

            {/* Column Mapping Configurator */}
            {previewData && !importResult && (
              <div className="space-y-4">
                <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-teal-600" />
                      Configure Column Mapping
                    </h4>
                    <span className="text-[11px] text-slate-500">
                      {(previewData.headers || (previewData as any).columns || []).length} headers detected
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    {/* Date Column */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Date Col <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={columnMapping.date_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, date_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>

                    {/* Narration Column */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Description Col <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={columnMapping.narration_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, narration_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>

                    {/* Debit Column */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Debit Col
                      </label>
                      <select
                        value={columnMapping.debit_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, debit_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>

                    {/* Credit Column */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Credit Col
                      </label>
                      <select
                        value={columnMapping.credit_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, credit_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>

                    {/* Amount Col (Combined) */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Amount Col
                      </label>
                      <select
                        value={columnMapping.amount_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, amount_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>

                    {/* Balance Column */}
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Balance Col
                      </label>
                      <select
                        value={columnMapping.balance_col}
                        onChange={(e) => setColumnMapping({ ...columnMapping, balance_col: e.target.value })}
                        className="w-full text-xs rounded border border-slate-300 px-2 py-1.5 bg-white text-slate-800"
                      >
                        <option value="">-- None --</option>
                        {((previewData.headers || (previewData as any).columns || []) as string[]).map((h) => (
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Deduplication & Summary Info Bar */}
                {(() => {
                  const previewRows = (previewData.parsed_preview_rows || previewData.preview_rows || []) as any[]
                  const totalDetected = previewData.total_detected_rows || previewRows.length
                  const potentialDups = previewData.potential_duplicates ?? previewRows.filter((r) => r.is_duplicate).length

                  return (
                    <>
                      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-teal-50/60 rounded-lg border border-teal-100 text-xs text-teal-900">
                        <div className="flex items-center gap-2">
                          <Info className="w-4 h-4 text-teal-600 shrink-0" />
                          <span>
                            Found <strong>{totalDetected}</strong> statement rows.
                            {potentialDups > 0 ? (
                              <span className="text-amber-700 font-semibold ml-1">
                                ({potentialDups} duplicate fingerprint matches will be safely skipped)
                              </span>
                            ) : (
                              <span className="text-emerald-700 font-semibold ml-1">
                                (No existing duplicates detected in ledger)
                              </span>
                            )}
                          </span>
                        </div>
                        <Badge variant={potentialDups > 0 ? 'warning' : 'success'}>
                          Idempotent Ingestion Safe
                        </Badge>
                      </div>

                      {/* Preview Table */}
                      <div className="border border-slate-200 rounded-xl overflow-hidden">
                        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                          <h5 className="text-xs font-bold text-slate-800">
                            Sample Data Preview ({previewRows.length} rows previewed)
                          </h5>
                          <span className="text-[11px] text-slate-500">Validation & Duplicate Checks</span>
                        </div>
                        <div className="max-h-60 overflow-y-auto">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-slate-100/70 text-slate-600 sticky top-0">
                              <tr>
                                <th className="p-2.5 font-semibold">#</th>
                                <th className="p-2.5 font-semibold">Date</th>
                                <th className="p-2.5 font-semibold">Description</th>
                                <th className="p-2.5 font-semibold">Type</th>
                                <th className="p-2.5 font-semibold">Amount</th>
                                <th className="p-2.5 font-semibold">Balance</th>
                                <th className="p-2.5 font-semibold">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {previewRows.map((row) => (
                                <tr
                                  key={row.row_number || row.row_index}
                                  className={`hover:bg-slate-50 ${
                                    row.is_duplicate ? 'bg-amber-50/40' : row.has_error ? 'bg-rose-50/40' : ''
                                  }`}
                                >
                                  <td className="p-2.5 text-slate-400 font-mono text-[11px]">{row.row_number || row.row_index}</td>
                                  <td className="p-2.5 text-slate-700 font-medium whitespace-nowrap">
                                    {row.parsed_date || row.raw_date || '—'}
                                  </td>
                                  <td className="p-2.5 text-slate-800 max-w-xs truncate" title={row.narration}>
                                    {row.narration || '—'}
                                  </td>
                                  <td className="p-2.5">
                                    {(row.tx_type || row.transaction_type) === 'DEBIT' ? (
                                      <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700">
                                        DEBIT
                                      </span>
                                    ) : (row.tx_type || row.transaction_type) === 'CREDIT' ? (
                                      <span className="inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700">
                                        CREDIT
                                      </span>
                                    ) : (
                                      <span className="text-slate-400">—</span>
                                    )}
                                  </td>
                                  <td className="p-2.5 font-semibold text-slate-900 whitespace-nowrap">
                                    {row.amount_inr != null ? formatINR(row.amount_inr) : '—'}
                                  </td>
                                  <td className="p-2.5 text-slate-600 whitespace-nowrap font-mono text-[11px]">
                                    {row.balance_inr != null ? formatINR(row.balance_inr) : '—'}
                                  </td>
                                  <td className="p-2.5 whitespace-nowrap">
                                    {row.is_duplicate ? (
                                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                        Duplicate
                                      </span>
                                    ) : row.valid !== false ? (
                                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                        Valid
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                                        Error
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </>
                  )
                })()}
                {/* Import Action Bar */}
                <div className="flex items-center justify-between pt-2">
                  <p className="text-[11px] text-slate-500">
                    Safe re-import: Duplicates are ignored; only new transactions will be committed.
                  </p>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={handleModalClose}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleExecuteImport}
                      isLoading={isImportLoading}
                    >
                      Commit Import to Ledger
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Import Result Screen */}
            {importResult && (
              <div className="space-y-4 p-5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">Statement Ingestion Complete</h4>
                    <p className="text-xs text-slate-600">{importResult.message}</p>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3 text-center">
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-slate-500 font-medium">Total Rows</p>
                    <p className="text-lg font-bold text-slate-900 mt-0.5">{importResult.total_rows}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-emerald-600 font-medium">Imported</p>
                    <p className="text-lg font-bold text-emerald-700 mt-0.5">{importResult.imported_rows}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-amber-600 font-medium">Skipped Duplicates</p>
                    <p className="text-lg font-bold text-amber-700 mt-0.5">{importResult.duplicate_rows}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200">
                    <p className="text-xs text-rose-600 font-medium">Failed Rows</p>
                    <p className="text-lg font-bold text-rose-700 mt-0.5">{importResult.failed_rows}</p>
                  </div>
                </div>

                {importResult.failed_rows > 0 && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span className="text-xs text-rose-900">
                        {importResult.failed_rows} rows had formatting errors and were safely bypassed.
                      </span>
                    </div>
                    <a
                      href={getJobErrorsDownloadUrl(importResult.job_id)}
                      download
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-700 bg-white border border-rose-300 rounded hover:bg-rose-50"
                    >
                      <Download className="w-3.5 h-3.5" /> Download Error CSV
                    </a>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                  <Button variant="outline" onClick={resetImportState}>
                    Import Another File
                  </Button>
                  <Button variant="primary" onClick={handleModalClose}>
                    Done & View Ledger
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* History Tab */
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Recent Statement Ingestion Jobs
              </h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={loadImportHistory}
                isLoading={isHistoryLoading}
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
              </Button>
            </div>

            {isHistoryLoading ? (
              <div className="p-8 text-center text-xs text-slate-500">Loading audit log...</div>
            ) : importJobs.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-500">
                No past import jobs found on this account.
              </div>
            ) : (
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold">
                    <tr>
                      <th className="p-3">File / Bank</th>
                      <th className="p-3">Import Date</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Imported / Total</th>
                      <th className="p-3 text-right">Duplicates</th>
                      <th className="p-3 text-center">Audit Report</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {importJobs.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-50">
                        <td className="p-3">
                          <p className="font-semibold text-slate-900">{job.filename}</p>
                          <p className="text-[11px] text-slate-500">{job.bank_format}</p>
                        </td>
                        <td className="p-3 text-slate-600 whitespace-nowrap">
                          {new Date(job.created_at).toLocaleString('en-IN', {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          })}
                        </td>
                        <td className="p-3">
                          <Badge
                            variant={
                              job.status === 'COMPLETED'
                                ? 'success'
                                : job.status === 'PARTIAL'
                                ? 'warning'
                                : 'danger'
                            }
                          >
                            {job.status}
                          </Badge>
                        </td>
                        <td className="p-3 text-right font-medium text-slate-800">
                          {job.imported_rows} / {job.total_rows}
                        </td>
                        <td className="p-3 text-right text-amber-600 font-medium">
                          {job.duplicate_rows}
                        </td>
                        <td className="p-3 text-center">
                          {job.has_errors ? (
                            <a
                              href={getJobErrorsDownloadUrl(job.id)}
                              download
                              className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-700 font-semibold"
                            >
                              <Download className="w-3.5 h-3.5" /> Error CSV
                            </a>
                          ) : (
                            <span className="text-slate-400 text-[11px]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}
