import React, { useState } from 'react'
import {
  MessageSquare,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
  CreditCard,
  Building2,
  Calendar,
  Hash,
  Wallet,
} from 'lucide-react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { parseSmsApi, importSmsTransactionApi } from '@/api/ingestion'
import { FinancialAccount, TransactionCategory, SMSParseResult } from '@/types'
import { formatINR } from '@/lib/formatters'
import { useToast } from '@/context/ToastContext'

interface Props {
  isOpen: boolean
  onClose: () => void
  accounts: FinancialAccount[]
  categories: TransactionCategory[]
  onSuccess: () => void
}

const SYNTHETIC_SMS_PRESETS = [
  {
    label: 'HDFC • Swiggy Debit',
    text: 'Alert: Your HDFC Bank A/c XX5432 was debited by Rs 1,499.00 on 22-Oct-2026 via UPI/Swiggy. Avl Bal: Rs 42,350.50. UPI Ref: 429381749102',
  },
  {
    label: 'ICICI • Salary Credit',
    text: 'Dear Customer, Acct XX8892 credited with Rs 1,85,000.00 on 01-Oct-2026 by InfoTech Solutions Salary. Avl Bal Rs 2,15,400.00.',
  },
  {
    label: 'SBI • Electricity Bill',
    text: 'SBI: A/c *1234 debited by Rs 2,840.00 on 14-Oct-26 at TATA POWER. Avl Bal Rs 18,920.00. Ref 389271829012',
  },
  {
    label: 'Axis • Flipkart Card',
    text: 'Axis Bank: Transaction of INR 4,299.00 on Credit Card ending 9012 at FLIPKART on 19-Oct-2026. Avail Limit: INR 85,000.',
  },
  {
    label: 'PhonePe • Chai Point UPI',
    text: 'Paid Rs. 450 to Chai Point on 20-Oct-2026. Txn ID: T261020140291. Debited from A/c XX6721.',
  },
  {
    label: 'Refund • Myntra Cashback',
    text: 'Rs. 1,200.00 credited to your account XX3341 on 21-Oct-2026 towards refund from MYNTRA. Ref 9928172910.',
  },
]

export const SMSParserModal: React.FC<Props> = ({
  isOpen,
  onClose,
  accounts,
  categories,
  onSuccess,
}) => {
  const { success: toastSuccess, error: toastError } = useToast()

  const [smsInput, setSmsInput] = useState(SYNTHETIC_SMS_PRESETS[0].text)
  const [isParsing, setIsParsing] = useState(false)
  const [parseResult, setParseResult] = useState<SMSParseResult | null>(null)

  // Ledger import form state
  const [selectedAccountId, setSelectedAccountId] = useState(
    accounts[0]?.id || ''
  )
  const [selectedCategoryId, setSelectedCategoryId] = useState('')
  const [isImporting, setIsImporting] = useState(false)

  const handleParse = async () => {
    if (!smsInput.trim()) {
      toastError('Please enter SMS text to parse.')
      return
    }

    setIsParsing(true)
    try {
      const result = await parseSmsApi(smsInput)
      setParseResult(result)
      if (result.success) {
        // Find matching category
        if (result.category_id) {
          setSelectedCategoryId(result.category_id)
        } else if (result.suggested_category_slug) {
          const match = categories.find((c) => c.slug === result.suggested_category_slug)
          if (match) setSelectedCategoryId(match.id)
        }
      } else {
        toastError(result.parse_error || 'Could not parse financial information from this message.')
      }
    } catch (err: any) {
      toastError(err?.message || 'Failed to parse SMS message.')
    } finally {
      setIsParsing(false)
    }
  }

  const handleAddToLedger = async () => {
    if (!parseResult || !parseResult.success) return
    if (!selectedAccountId) {
      toastError('Please select a bank account.')
      return
    }
    const catId = selectedCategoryId || categories[0]?.id
    if (!catId) {
      toastError('Please select a category.')
      return
    }

    setIsImporting(true)
    try {
      const payload = {
        account_id: selectedAccountId,
        category_id: catId,
        amount_inr: parseResult.amount_inr || 0,
        transaction_type: parseResult.transaction_type || 'DEBIT',
        date: parseResult.timestamp
          ? parseResult.timestamp.split('T')[0]
          : new Date().toISOString().split('T')[0],
        narration: parseResult.clean_narration || parseResult.raw_narration || 'SMS Transaction',
        merchant_name: parseResult.merchant_name,
        payment_mode: 'UPI',
        reference_id: parseResult.upi_reference,
      }

      await importSmsTransactionApi(payload)
      toastSuccess('Transaction parsed and committed to ledger!')
      onSuccess()
      onClose()
    } catch (err: any) {
      toastError(err?.message || 'Failed to add parsed transaction to ledger.')
    } finally {
      setIsImporting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Bank SMS Transaction Parser"
      description="Extract transaction amount, merchant, UPI reference, and intelligent category from bank SMS alerts"
      maxWidth="3xl"
    >
      <div className="space-y-5">
        {/* Synthetic Presets Bar */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center justify-between">
            <span>Synthetic Bank SMS Templates</span>
            <span className="text-[11px] text-slate-400 font-normal">Click to load realistic example</span>
          </label>
          <div className="flex flex-wrap gap-1.5">
            {SYNTHETIC_SMS_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setSmsInput(preset.text)
                  setParseResult(null)
                }}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-lg border transition-all ${
                  smsInput === preset.text
                    ? 'bg-teal-50 border-teal-500 text-teal-800 shadow-xs'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* SMS Input Box */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Raw SMS Message Text
          </label>
          <textarea
            value={smsInput}
            onChange={(e) => setSmsInput(e.target.value)}
            rows={3}
            placeholder="Paste your bank transaction SMS here..."
            className="w-full text-xs font-mono rounded-lg border border-slate-300 p-3 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        {/* Action Button */}
        <div className="flex justify-end">
          <Button
            variant="primary"
            onClick={handleParse}
            isLoading={isParsing}
            className="w-full sm:w-auto"
          >
            <Sparkles className="w-4 h-4 mr-1.5 text-teal-200" />
            Extract & Categorize
          </Button>
        </div>

        {/* Parse Results Breakdown */}
        {parseResult && (
          <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
            {parseResult.success ? (
              <div className="p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-xs">
                      {parseResult.bank_name ? parseResult.bank_name.substring(0, 3) : 'SMS'}
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">
                        {parseResult.bank_name || 'Bank Transaction'} Detected
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        Confidence: {(parseResult.parser_confidence * 100).toFixed(0)}% • Mode: Regular Expression Engine
                      </p>
                    </div>
                  </div>
                  <Badge variant={parseResult.transaction_type === 'CREDIT' ? 'success' : 'danger'}>
                    {parseResult.transaction_type}
                  </Badge>
                </div>

                {/* Structured Extraction Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase flex items-center gap-1">
                      <Wallet className="w-3 h-3 text-slate-500" /> Amount
                    </span>
                    <p
                      className={`text-base font-bold mt-0.5 ${
                        parseResult.transaction_type === 'CREDIT' ? 'text-emerald-600' : 'text-rose-600'
                      }`}
                    >
                      {parseResult.amount_inr != null ? formatINR(parseResult.amount_inr) : '—'}
                    </p>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase flex items-center gap-1">
                      <Building2 className="w-3 h-3 text-slate-500" /> Merchant / Payee
                    </span>
                    <p className="text-xs font-bold text-slate-800 mt-1 truncate">
                      {parseResult.merchant_name || parseResult.clean_narration || 'Direct Payee'}
                    </p>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase flex items-center gap-1">
                      <CreditCard className="w-3 h-3 text-slate-500" /> Account Suffix
                    </span>
                    <p className="text-xs font-mono font-semibold text-slate-800 mt-1">
                      {parseResult.account_mask || 'Not specified'}
                    </p>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-400 font-semibold uppercase flex items-center gap-1">
                      <Hash className="w-3 h-3 text-slate-500" /> UPI / Ref ID
                    </span>
                    <p className="text-xs font-mono text-slate-700 mt-1 truncate" title={parseResult.upi_reference || ''}>
                      {parseResult.upi_reference || 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Second row: Available balance & date */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50/70 rounded-lg border border-slate-100 flex items-center justify-between">
                    <span className="text-slate-500 text-[11px]">Available Balance after Txn:</span>
                    <span className="font-semibold text-slate-800 font-mono">
                      {parseResult.available_balance_inr != null
                        ? formatINR(parseResult.available_balance_inr)
                        : 'Not parsed in SMS'}
                    </span>
                  </div>

                  <div className="p-2.5 bg-slate-50/70 rounded-lg border border-slate-100 flex items-center justify-between">
                    <span className="text-slate-500 text-[11px]">Parsed Timestamp:</span>
                    <span className="font-semibold text-slate-800">
                      {parseResult.timestamp ? parseResult.timestamp.split('T')[0] : 'Current Date'}
                    </span>
                  </div>
                </div>

                {/* Categorization Intelligence Callout */}
                <div className="p-3 bg-teal-50/70 rounded-lg border border-teal-100 flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                      Auto-Categorization Pipeline
                    </p>
                    <p className="text-xs text-slate-700 mt-0.5">
                      Suggested Category:{' '}
                      <strong className="text-slate-900 capitalize">
                        {parseResult.category_name || parseResult.suggested_category_slug}
                      </strong>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-teal-700">
                      {((parseResult.categorization_confidence || 0.95) * 100).toFixed(0)}% match
                    </span>
                    <Badge variant="teal">{parseResult.categorization_method || 'RULE'}</Badge>
                  </div>
                </div>

                {/* 1-Click Commit Section */}
                <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="grid grid-cols-2 gap-2 flex-1">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">
                        Post to Account
                      </label>
                      <select
                        value={selectedAccountId}
                        onChange={(e) => setSelectedAccountId(e.target.value)}
                        className="w-full text-xs rounded border border-slate-300 px-2.5 py-1.5 bg-white text-slate-800"
                      >
                        {accounts.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name} ({a.institution})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">
                        Category
                      </label>
                      <select
                        value={selectedCategoryId}
                        onChange={(e) => setSelectedCategoryId(e.target.value)}
                        className="w-full text-xs rounded border border-slate-300 px-2.5 py-1.5 bg-white text-slate-800"
                      >
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <Button
                    variant="primary"
                    onClick={handleAddToLedger}
                    isLoading={isImporting}
                    className="self-end"
                  >
                    <CheckCircle2 className="w-4 h-4 mr-1.5" />
                    Commit to Ledger
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-4 flex items-center gap-3 text-rose-700 bg-rose-50/50">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <p className="text-xs">
                  {parseResult.parse_error || 'Failed to extract financial data from the message.'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}
