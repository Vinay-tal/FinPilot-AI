import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { FinancialAccount, TransactionCategory } from '@/types'

const transactionSchema = z.object({
  account_id: z.string().min(1, 'Please select an account'),
  category_id: z.string().min(1, 'Please select a category'),
  amount_inr: z.coerce.number().positive('Amount must be positive'),
  transaction_type: z.enum(['DEBIT', 'CREDIT']),
  date: z.string().min(1, 'Date is required'),
  narration: z.string().min(2, 'Narration must be at least 2 characters'),
  merchant_name: z.string().optional(),
  payment_mode: z.enum(['UPI', 'NET_BANKING', 'DEBIT_CARD', 'CREDIT_CARD', 'CASH', 'CHEQUE']),
})

type FormData = z.infer<typeof transactionSchema>

interface Props {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: FormData) => Promise<void>
  accounts: FinancialAccount[]
  categories: TransactionCategory[]
  isLoading?: boolean
}

export const AddTransactionModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  accounts,
  categories,
  isLoading = false,
}) => {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      transaction_type: 'DEBIT',
      payment_mode: 'UPI',
      date: new Date().toISOString().split('T')[0],
      amount_inr: 500,
    },
  })

  const handleFormSubmit = async (data: FormData) => {
    await onSubmit(data)
    reset()
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add New Transaction"
      description="Record an income or expense in your ledger"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        {/* Transaction Type Radio */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Type</label>
          <div className="grid grid-cols-2 gap-2">
            <label className="flex items-center justify-center p-2 rounded-lg border cursor-pointer text-xs font-semibold hover:bg-slate-50 transition-colors has-[:checked]:bg-rose-50 has-[:checked]:border-rose-400 has-[:checked]:text-rose-700">
              <input
                type="radio"
                value="DEBIT"
                {...register('transaction_type')}
                className="sr-only"
              />
              <span>Debit (Expense)</span>
            </label>
            <label className="flex items-center justify-center p-2 rounded-lg border cursor-pointer text-xs font-semibold hover:bg-slate-50 transition-colors has-[:checked]:bg-emerald-50 has-[:checked]:border-emerald-400 has-[:checked]:text-emerald-700">
              <input
                type="radio"
                value="CREDIT"
                {...register('transaction_type')}
                className="sr-only"
              />
              <span>Credit (Income)</span>
            </label>
          </div>
        </div>

        {/* Amount INR */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Amount (₹ INR)</label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-slate-400 font-bold text-sm">₹</span>
            <input
              type="number"
              step="0.01"
              placeholder="0.00"
              {...register('amount_inr', { valueAsNumber: true })}
              className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono font-medium"
            />
          </div>
          {errors.amount_inr && (
            <p className="text-[11px] text-rose-600 mt-1">{errors.amount_inr.message}</p>
          )}
        </div>

        {/* Narration */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Narration / Description</label>
          <input
            type="text"
            placeholder="e.g. Swiggy Biryani Dinner Indiranagar"
            {...register('narration')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          {errors.narration && (
            <p className="text-[11px] text-rose-600 mt-1">{errors.narration.message}</p>
          )}
        </div>

        {/* Account and Category Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Account</label>
            <select
              {...register('account_id')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="">Select Account</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            {errors.account_id && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.account_id.message}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
            <select
              {...register('category_id')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="">Select Category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {errors.category_id && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.category_id.message}</p>
            )}
          </div>
        </div>

        {/* Date and Payment Mode Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Date</label>
            <input
              type="date"
              {...register('date')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            {errors.date && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.date.message}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Mode</label>
            <select
              {...register('payment_mode')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="UPI">UPI</option>
              <option value="NET_BANKING">Net Banking</option>
              <option value="DEBIT_CARD">Debit Card</option>
              <option value="CREDIT_CARD">Credit Card</option>
              <option value="CASH">Cash</option>
            </select>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={isLoading}>
            Add Transaction
          </Button>
        </div>
      </form>
    </Modal>
  )
}
