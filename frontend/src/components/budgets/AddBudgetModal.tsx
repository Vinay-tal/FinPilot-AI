import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { TransactionCategory } from '@/types'

const budgetSchema = z.object({
  category_id: z.string().min(1, 'Please select a category'),
  amount_inr: z.coerce.number().positive('Limit must be positive'),
  month: z.number().min(1).max(12),
  year: z.number().min(2020).max(2100),
  alert_threshold: z.number().min(0.1).max(1.0),
})

type FormData = z.infer<typeof budgetSchema>

interface Props {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: FormData) => Promise<void>
  categories: TransactionCategory[]
  isLoading?: boolean
}

export const AddBudgetModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  categories,
  isLoading = false,
}) => {
  const today = new Date()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(budgetSchema),
    defaultValues: {
      month: today.getMonth() + 1,
      year: today.getFullYear(),
      amount_inr: 15000,
      alert_threshold: 0.80,
    },
  })

  const handleFormSubmit = async (data: FormData) => {
    await onSubmit(data)
    reset()
    onClose()
  }

  // Filter only expense categories
  const expenseCategories = categories.filter((c) => !c.is_income)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Set Category Monthly Budget"
      description="Define spending thresholds and pacing alerts"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Expense Category</label>
          <select
            {...register('category_id')}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
          >
            <option value="">Select Category</option>
            {expenseCategories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {errors.category_id && (
            <p className="text-[11px] text-rose-600 mt-1">{errors.category_id.message}</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly Limit (₹ INR)</label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-slate-400 font-bold text-sm">₹</span>
            <input
              type="number"
              step="100"
              placeholder="e.g. 15000"
              {...register('amount_inr', { valueAsNumber: true })}
              className="w-full pl-8 pr-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono font-medium"
            />
          </div>
          {errors.amount_inr && (
            <p className="text-[11px] text-rose-600 mt-1">{errors.amount_inr.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Month</label>
            <select
              {...register('month', { valueAsNumber: true })}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                <option key={m} value={m}>
                  {new Date(2026, m - 1, 1).toLocaleString('default', { month: 'long' })}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Warning Threshold</label>
            <select
              {...register('alert_threshold', { valueAsNumber: true })}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="0.75">75% of budget</option>
              <option value="0.80">80% of budget</option>
              <option value="0.90">90% of budget</option>
            </select>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={isLoading}>
            Set Budget
          </Button>
        </div>
      </form>
    </Modal>
  )
}
