import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HealthScoreCard } from '@/components/dashboard/HealthScoreCard'
import { RecentTransactionsCard } from '@/components/dashboard/RecentTransactionsCard'
import { BudgetPacingList } from '@/components/dashboard/BudgetPacingList'
import { RecurringBillsList } from '@/components/dashboard/RecurringBillsList'
import { MemoryRouter } from 'react-router-dom'
import { Transaction, Budget, RecurringTransaction } from '@/types'

describe('Dashboard Component Suite', () => {
  it('renders HealthScoreCard with score, grade, and progress indicator', () => {
    render(
      <MemoryRouter>
        <HealthScoreCard score={82} grade="Excellent" />
      </MemoryRouter>
    )

    expect(screen.getByText('82')).toBeInTheDocument()
    expect(screen.getByText('Excellent')).toBeInTheDocument()
    expect(screen.getByText('Financial Health Score')).toBeInTheDocument()
  })

  it('renders RecentTransactionsCard with transaction items', () => {
    const mockTxs: Transaction[] = [
      {
        id: 'tx-1',
        user_id: 'user-1',
        account_id: 'acc-1',
        category_id: 'cat-1',
        category_name: 'Dining & Food',
        category_color: '#F97316',
        date: '2026-10-20',
        amount_paise: 85000,
        amount_inr: 850,
        transaction_type: 'DEBIT',
        narration: 'Swiggy Order',
        merchant_name: 'Swiggy',
        payment_mode: 'UPI',
        is_recurring: false,
        fingerprint: 'fp-1',
        categorization_method: 'RULE',
        created_at: '2026-10-20T12:00:00Z',
        updated_at: '2026-10-20T12:00:00Z',
      },
    ]

    render(
      <MemoryRouter>
        <RecentTransactionsCard transactions={mockTxs} />
      </MemoryRouter>
    )

    expect(screen.getByText('Swiggy')).toBeInTheDocument()
    expect(screen.getByText('Dining & Food')).toBeInTheDocument()
    expect(screen.getByText('₹850.00')).toBeInTheDocument()
  })

  it('renders BudgetPacingList with category allocations', () => {
    const mockBudgets: Budget[] = [
      {
        id: 'b-1',
        user_id: 'user-1',
        category_id: 'cat-1',
        category_name: 'Groceries',
        category_color: '#0D9488',
        month: 10,
        year: 2026,
        amount_paise: 2000000,
        amount_inr: 20000,
        alert_threshold: 0.85,
        spent_paise: 1250000,
        spent_inr: 12500,
        remaining_paise: 750000,
        remaining_inr: 7500,
        pacing_pct: 63,
        alert_status: 'NORMAL',
        created_at: '2026-10-01T00:00:00Z',
        updated_at: '2026-10-01T00:00:00Z',
      },
    ]

    render(
      <MemoryRouter>
        <BudgetPacingList budgets={mockBudgets} />
      </MemoryRouter>
    )

    expect(screen.getByText('Groceries')).toBeInTheDocument()
    expect(screen.getByText('63%')).toBeInTheDocument()
  })

  it('renders RecurringBillsList with upcoming obligations', () => {
    const mockBills: RecurringTransaction[] = [
      {
        id: 'rec-1',
        user_id: 'user-1',
        category_id: 'cat-2',
        category_name: 'Housing',
        name: 'Apartment Rent',
        merchant_name: 'Landlord',
        expected_amount_paise: 2800000,
        expected_amount_inr: 28000,
        frequency: 'MONTHLY',
        next_expected_date: '2026-11-01',
        is_active: true,
        created_at: '2026-10-01T00:00:00Z',
        updated_at: '2026-10-01T00:00:00Z',
      },
    ]

    render(<RecurringBillsList recurring={mockBills} />)

    expect(screen.getByText('Apartment Rent')).toBeInTheDocument()
    expect(screen.getByText('₹28,000.00')).toBeInTheDocument()
  })
})
