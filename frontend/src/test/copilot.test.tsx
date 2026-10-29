import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CopilotPage } from '@/pages/CopilotPage'
import { ToastProvider } from '@/context/ToastContext'
import * as copilotApi from '@/api/copilot'
import {
  ConversationItem,
  ChatMessage,
  CopilotTurnResponse,
} from '@/types'

vi.mock('@/api/copilot')

const mockConversations: ConversationItem[] = [
  {
    id: 'conv-1',
    title: 'October Budget Audit',
    created_at: '2026-10-23T02:00:00Z',
    updated_at: '2026-10-23T02:30:00Z',
    message_count: 3,
    last_message_preview: 'You have spent ₹12,400 on Food & Dining...',
  },
  {
    id: 'conv-2',
    title: 'Emergency Fund Check',
    created_at: '2026-10-22T10:00:00Z',
    updated_at: '2026-10-22T10:15:00Z',
    message_count: 2,
    last_message_preview: 'Your liquid reserve is currently ₹85,000...',
  },
]

const mockMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'USER',
    content: 'How much did I spend on food this month?',
    created_at: '10:30 AM',
  },
  {
    id: 'msg-2',
    role: 'ASSISTANT',
    content: 'Based on your verified bank transactions, you have spent a total of ₹12,400.00 across 34 transactions this period.',
    provider_used: 'mock-deterministic-v1',
    citations: [
      {
        source: 'TRANSACTIONS_LEDGER',
        title: 'Food & Dining Expenditure',
        value: '₹12,400.00',
        detail: '34 settled transactions in period',
      },
    ],
    scenario_card: {
      type: 'AFFORDABILITY',
      title: 'Affordability Verdict: ₹15,000 Purchase',
      verdict: 'AFFORDABLE_SAFE',
      verdict_title: 'Affordable without breaching your emergency reserve',
      current_liquid_inr: 85000,
      post_purchase_min_dip_inr: 50200,
      reserve_threshold_inr: 10000,
      recommendation: 'You can safely afford this purchase from your liquid cash cushion.',
    },
    created_at: '10:31 AM',
  },
]

const mockTurnResponse: CopilotTurnResponse = {
  conversation_id: 'conv-1',
  message_id: 'msg-3',
  answer: 'You have spent ₹12,400.00 on food this month.',
  provider_used: 'mock-deterministic-v1',
  citations: [
    {
      source: 'TRANSACTIONS_LEDGER',
      title: 'Food & Dining',
      value: '₹12,400.00',
      detail: 'Verified from ledger',
    },
  ],
  facts_vs_estimates: {
    retrieved_facts: ['Verified ₹12,400 settled on accounts.'],
    model_estimates: [],
    hypothetical_scenarios: [],
  },
  scenario_card: null,
  suggested_followups: [
    'Where could I reduce spending by ₹2,000 next month?',
    'What recurring payments are due soon?',
  ],
}

function renderCopilotPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <CopilotPage />
      </ToastProvider>
    </QueryClientProvider>
  )
}

describe('Financial Copilot UI Suite (Milestone 5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(copilotApi.listConversationsApi).mockResolvedValue(mockConversations)
    vi.mocked(copilotApi.getConversationMessagesApi).mockResolvedValue(mockMessages)
    vi.mocked(copilotApi.sendConversationMessageApi).mockResolvedValue(mockTurnResponse)
    vi.mocked(copilotApi.createConversationApi).mockResolvedValue({
      id: 'conv-3',
      title: 'New Discussion',
      created_at: '2026-10-23T03:00:00Z',
      updated_at: '2026-10-23T03:00:00Z',
      message_count: 1,
      last_message_preview: 'New conversation created',
    })
  })

  it('renders conversation list, active title, and grounding badges', async () => {
    renderCopilotPage()

    // Sidebar titles
    await waitFor(() => {
      expect(screen.getByText('October Budget Audit')).toBeInTheDocument()
      expect(screen.getByText('Emergency Fund Check')).toBeInTheDocument()
    })

    // Grounding badge
    expect(screen.getByText('Grounding Active')).toBeInTheDocument()
    expect(screen.getByText(/Grounded in Ledger/)).toBeInTheDocument()
  })

  it('displays chat messages with evidence citations and affordability scenario card', async () => {
    renderCopilotPage()

    await waitFor(() => {
      expect(screen.getByText('October Budget Audit')).toBeInTheDocument()
      expect(screen.getByText('How much did I spend on food this month?')).toBeInTheDocument()
    })

    // Assistant response
    await waitFor(() => {
      expect(
        screen.getByText(/Based on your verified bank transactions/)
      ).toBeInTheDocument()
    })

    // Evidence citation tag
    expect(screen.getByText(/Food & Dining Expenditure:/)).toBeInTheDocument()
    expect(screen.getByText('₹12,400.00')).toBeInTheDocument()

    // Scenario card
    expect(screen.getByText('Affordability Verdict: ₹15,000 Purchase')).toBeInTheDocument()
    expect(screen.getByText(/You can safely afford this purchase/)).toBeInTheDocument()
  })

  it('sends query via input form and calls sendConversationMessageApi', async () => {
    renderCopilotPage()

    await waitFor(() => {
      expect(screen.getByText('October Budget Audit')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/Ask about your expenses, affordability/)).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText(/Ask about your expenses, affordability/)
    fireEvent.change(input, { target: { value: 'What recurring payments are due soon?' } })

    const askBtn = screen.getByText('Ask Copilot')
    fireEvent.click(askBtn)

    await waitFor(() => {
      expect(copilotApi.sendConversationMessageApi).toHaveBeenCalledWith(
        'conv-1',
        'What recurring payments are due soon?'
      )
    })
  })

  it('sends prompt when clicking a suggested prompt chip', async () => {
    renderCopilotPage()

    await waitFor(() => {
      expect(screen.getByText('October Budget Audit')).toBeInTheDocument()
      expect(
        screen.getByText('Which categories increased the most compared with last month?')
      ).toBeInTheDocument()
    })

    const chip = screen.getByText('Which categories increased the most compared with last month?')
    fireEvent.click(chip)

    await waitFor(() => {
      expect(copilotApi.sendConversationMessageApi).toHaveBeenCalledWith(
        'conv-1',
        'Which categories increased the most compared with last month?'
      )
    })
  })

  it('triggers new conversation creation when clicking plus button', async () => {
    renderCopilotPage()

    await waitFor(() => {
      expect(screen.getByTitle('Start new conversation')).toBeInTheDocument()
    })

    const newBtn = screen.getByTitle('Start new conversation')
    fireEvent.click(newBtn)

    await waitFor(() => {
      expect(copilotApi.createConversationApi).toHaveBeenCalledWith('New Discussion')
    })
  })
})
