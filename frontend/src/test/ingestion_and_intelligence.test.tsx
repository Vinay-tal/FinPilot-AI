import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CSVImportModal } from '@/components/transactions/CSVImportModal'
import { SMSParserModal } from '@/components/transactions/SMSParserModal'
import { TransactionIntelligenceHub } from '@/components/insights/TransactionIntelligenceHub'
import { ToastProvider } from '@/context/ToastContext'
import { FinancialAccount, TransactionCategory } from '@/types'

const mockAccounts: FinancialAccount[] = [
  {
    id: 'acc-1',
    user_id: 'user-1',
    name: 'HDFC Salary Account',
    account_type: 'SAVINGS',
    institution: 'HDFC Bank',
    balance_paise: 15420000,
    balance_inr: 154200,
    currency: 'INR',
    is_active: true,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  },
]

const mockCategories: TransactionCategory[] = [
  {
    id: 'cat-food',
    name: 'Food & Dining',
    slug: 'food-dining',
    icon: 'Utensils',
    color: '#F97316',
    is_income: false,
    is_system: true,
    created_at: '2026-10-01T00:00:00Z',
  },
]

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>
  )
}

describe('Transaction Ingestion & Intelligence UI Suite', () => {
  it('renders CSVImportModal with presets and account selector', () => {
    renderWithProviders(
      <CSVImportModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        onSuccess={vi.fn()}
      />
    )

    expect(screen.getByText('CSV Bank Statement Importer')).toBeInTheDocument()
    expect(screen.getByText('Destination Bank Account')).toBeInTheDocument()
    expect(screen.getByText('HDFC')).toBeInTheDocument()
    expect(screen.getByText('ICICI')).toBeInTheDocument()
    expect(screen.getByText('SBI')).toBeInTheDocument()
    expect(screen.getByText('AXIS')).toBeInTheDocument()
    expect(screen.getByText(/Drop your bank CSV statement here/i)).toBeInTheDocument()
  })

  it('renders SMSParserModal with synthetic templates', () => {
    renderWithProviders(
      <SMSParserModal
        isOpen={true}
        onClose={vi.fn()}
        accounts={mockAccounts}
        categories={mockCategories}
        onSuccess={vi.fn()}
      />
    )

    expect(screen.getByText('Bank SMS Transaction Parser')).toBeInTheDocument()
    expect(screen.getByText('HDFC • Swiggy Debit')).toBeInTheDocument()
    expect(screen.getByText('ICICI • Salary Credit')).toBeInTheDocument()
    expect(screen.getByText('SBI • Electricity Bill')).toBeInTheDocument()
    expect(screen.getByText('Extract & Categorize')).toBeInTheDocument()
  })

  it('renders TransactionIntelligenceHub navigation tabs', () => {
    renderWithProviders(<TransactionIntelligenceHub />)

    expect(screen.getByText(/ML Categorizer & Evaluation/i)).toBeInTheDocument()
    expect(screen.getByText(/Recurring Subscriptions/i)).toBeInTheDocument()
    expect(screen.getByText(/Near-Duplicate Alerts/i)).toBeInTheDocument()
    expect(screen.getByText(/Statistical Outliers/i)).toBeInTheDocument()
    expect(screen.getByText(/Merchant Analytics/i)).toBeInTheDocument()
  })
})
