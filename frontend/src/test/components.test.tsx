import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { StatCard } from '@/components/common/StatCard'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorAlert } from '@/components/common/ErrorAlert'
import { Wallet } from 'lucide-react'

describe('Common Components', () => {
  it('renders Button and handles click events', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click Me</Button>)

    const btn = screen.getByRole('button', { name: /click me/i })
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('renders Button in loading state and disables it', () => {
    render(<Button isLoading>Submit</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
  })

  it('renders Badge with custom variants and dot indicator', () => {
    render(<Badge variant="success" dot>Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders StatCard with value, title, and trend badge', () => {
    render(
      <StatCard
        title="Total Liquid Assets"
        value="₹4,25,000"
        subtitle="Across 3 accounts"
        change={{ value: '+12.5%', isPositive: true }}
        icon={Wallet}
      />
    )
    expect(screen.getByText('Total Liquid Assets')).toBeInTheDocument()
    expect(screen.getByText('₹4,25,000')).toBeInTheDocument()
    expect(screen.getByText('+12.5%')).toBeInTheDocument()
  })

  it('renders EmptyState with action button', () => {
    const onAction = vi.fn()
    render(
      <EmptyState
        title="No Transactions Found"
        description="Try adjusting your filter"
        actionLabel="Clear Filter"
        onAction={onAction}
      />
    )
    expect(screen.getByText('No Transactions Found')).toBeInTheDocument()
    const actionBtn = screen.getByRole('button', { name: /clear filter/i })
    fireEvent.click(actionBtn)
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('renders ErrorAlert with retry callback', () => {
    const onRetry = vi.fn()
    render(
      <ErrorAlert
        title="Connection Error"
        message="Backend server did not respond"
        onRetry={onRetry}
      />
    )
    expect(screen.getByText('Connection Error')).toBeInTheDocument()
    const retryBtn = screen.getByRole('button', { name: /try again/i })
    fireEvent.click(retryBtn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
