import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'

const goalSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  target_amount_inr: z.coerce.number().positive('Must be positive'),
  current_amount_inr: z.coerce.number().min(0).default(0),
  target_date: z.string().min(1, 'Target date is required'),
  category: z.enum(['EMERGENCY_FUND', 'VACATION', 'PURCHASE', 'INVESTMENT', 'OTHER']),
  priority: z.enum(['HIGH', 'MEDIUM', 'LOW']),
})

type FormData = z.infer<typeof goalSchema>

interface Props {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: FormData) => Promise<void>
  isLoading?: boolean
}

export const AddGoalModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(goalSchema),
    defaultValues: {
      category: 'SAVINGS' as any,
      priority: 'MEDIUM',
      target_date: '2026-12-31',
      current_amount_inr: 0,
      target_amount_inr: 100000,
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
      title="Create Savings Goal"
      description="Track milestones, emergency funds, or planned acquisitions"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Goal Name</label>
          <input
            type="text"
            placeholder="e.g. 6-Month Emergency Reserve, Goa Trip"
            {...register('name')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
          {errors.name && (
            <p className="text-[11px] text-rose-600 mt-1">{errors.name.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Amount (₹)</label>
            <input
              type="number"
              step="1000"
              {...register('target_amount_inr', { valueAsNumber: true })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
            />
            {errors.target_amount_inr && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.target_amount_inr.message}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Saved So Far (₹)</label>
            <input
              type="number"
              step="1000"
              {...register('current_amount_inr', { valueAsNumber: true })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
            <select
              {...register('category')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="EMERGENCY_FUND">Emergency Fund</option>
              <option value="VACATION">Vacation / Travel</option>
              <option value="PURCHASE">Major Purchase</option>
              <option value="INVESTMENT">Investment Target</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Priority</label>
            <select
              {...register('priority')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
            >
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Date</label>
            <input
              type="date"
              {...register('target_date')}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={isLoading}>
            Create Goal
          </Button>
        </div>
      </form>
    </Modal>
  )
}
