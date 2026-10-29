import React, { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bot,
  Send,
  Sparkles,
  ShieldCheck,
  User,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  MessageSquare,
  HelpCircle,
  Database,
  Loader2,
  TrendingUp,
  AlertTriangle,
  Calendar,
  Layers,
  ChevronRight,
  Info,
  CheckCircle2,
  Cpu,
} from 'lucide-react'
import {
  listConversationsApi,
  createConversationApi,
  renameConversationApi,
  deleteConversationApi,
  getConversationMessagesApi,
  sendConversationMessageApi,
} from '@/api/copilot'
import { formatINR } from '@/lib/formatters'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { useToast } from '@/context/ToastContext'
import {
  ConversationItem,
  ChatMessage,
  CopilotTurnResponse,
  ScenarioCard,
} from '@/types'

const CURATED_PROMPTS = [
  'How much did I spend on food this month?',
  'Which categories increased the most compared with last month?',
  'Can I afford a ₹15,000 purchase without dropping below my emergency reserve?',
  'Why does the system predict a low balance near month-end?',
  'Where could I reduce spending by ₹2,000 next month?',
  'What recurring payments are due soon?',
  'How much could I save in six months under different spending assumptions?',
]

export const CopilotPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { success: toastSuccess, error: toastError } = useToast()

  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [queryInput, setQueryInput] = useState('')
  const [editingConvId, setEditingConvId] = useState<string | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [activeFollowups, setActiveFollowups] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 1. Fetch user's conversation sessions
  const { data: conversations = [], isLoading: isConvLoading } = useQuery({
    queryKey: ['copilot-conversations'],
    queryFn: listConversationsApi,
  })

  // Set initial active conversation
  useEffect(() => {
    if (conversations.length > 0 && !activeConvId) {
      setActiveConvId(conversations[0].id)
    }
  }, [conversations, activeConvId])

  // 2. Fetch messages for active conversation
  const { data: messages = [], isLoading: isMessagesLoading } = useQuery({
    queryKey: ['copilot-messages', activeConvId],
    queryFn: () => (activeConvId ? getConversationMessagesApi(activeConvId) : Promise.resolve([])),
    enabled: Boolean(activeConvId),
  })

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // 3. Create conversation mutation
  const createConvMutation = useMutation({
    mutationFn: (title?: string) => createConversationApi(title),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ['copilot-conversations'] })
      setActiveConvId(newConv.id)
      toastSuccess('Started new financial discussion')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to start conversation')
    },
  })

  // 4. Rename conversation mutation
  const renameConvMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameConversationApi(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['copilot-conversations'] })
      setEditingConvId(null)
      toastSuccess('Conversation renamed')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to rename conversation')
    },
  })

  // 5. Delete conversation mutation
  const deleteConvMutation = useMutation({
    mutationFn: (id: string) => deleteConversationApi(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['copilot-conversations'] })
      if (activeConvId === deletedId) {
        const remaining = conversations.filter((c) => c.id !== deletedId)
        setActiveConvId(remaining.length > 0 ? remaining[0].id : null)
      }
      toastSuccess('Conversation deleted')
    },
    onError: (err: any) => {
      toastError(err?.message || 'Failed to delete conversation')
    },
  })

  // 6. Send message turn mutation
  const sendMessageMutation = useMutation({
    mutationFn: ({ convId, query }: { convId: string; query: string }) =>
      sendConversationMessageApi(convId, query),
    onSuccess: (res: CopilotTurnResponse) => {
      setActiveFollowups(res.suggested_followups || [])
      queryClient.invalidateQueries({ queryKey: ['copilot-messages', activeConvId] })
      queryClient.invalidateQueries({ queryKey: ['copilot-conversations'] })
    },
    onError: (err: any) => {
      toastError(err?.message || 'Copilot reasoning failed')
    },
  })

  const handleSend = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sendMessageMutation.isPending) return

    if (!activeConvId) {
      // Create conversation first then send
      createConvMutation.mutate(trimmed.slice(0, 30), {
        onSuccess: (conv) => {
          sendMessageMutation.mutate({ convId: conv.id, query: trimmed })
        },
      })
    } else {
      sendMessageMutation.mutate({ convId: activeConvId, query: trimmed })
    }
    setQueryInput('')
  }

  const activeConversation = conversations.find((c) => c.id === activeConvId)

  // Render scenario result card
  const renderScenarioCard = (card?: ScenarioCard | null) => {
    if (!card) return null

    if (card.type === 'AFFORDABILITY') {
      const isSafe = card.verdict === 'AFFORDABLE_SAFE'
      const isWarning = card.verdict === 'TEMPORARY_DIP_WARNING'

      return (
        <div
          className={`mt-3 p-4 rounded-xl border text-xs space-y-2.5 ${
            isSafe
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
              : isWarning
              ? 'bg-amber-50/70 border-amber-200 text-amber-950'
              : 'bg-rose-50/70 border-rose-200 text-rose-950'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-bold flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              {isSafe ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-amber-600" />}
              {card.title}
            </span>
            <Badge variant={isSafe ? 'success' : isWarning ? 'warning' : 'danger'}>
              {card.verdict?.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1 text-[11px]">
            <div className="bg-white/80 p-2 rounded-lg border border-slate-200/60">
              <span className="text-slate-500">Current Liquid Cash</span>
              <p className="font-bold font-mono text-slate-900 mt-0.5">{formatINR(card.current_liquid_inr || 0)}</p>
            </div>
            <div className="bg-white/80 p-2 rounded-lg border border-slate-200/60">
              <span className="text-slate-500">Post-Purchase Min Dip</span>
              <p className={`font-bold font-mono mt-0.5 ${isSafe ? 'text-emerald-700' : 'text-rose-700'}`}>
                {formatINR(card.post_purchase_min_dip_inr || 0)}
              </p>
            </div>
            <div className="bg-white/80 p-2 rounded-lg border border-slate-200/60 col-span-2 sm:col-span-1">
              <span className="text-slate-500">Emergency Reserve Buffer</span>
              <p className="font-bold font-mono text-slate-800 mt-0.5">{formatINR(card.reserve_threshold_inr || 10000)}</p>
            </div>
          </div>

          {card.recommendation && (
            <p className="text-slate-700 leading-relaxed pt-1 border-t border-slate-200/60">
              {card.recommendation}
            </p>
          )}
        </div>
      )
    }

    if (card.type === 'SPENDING_REDUCTION') {
      return (
        <div className="mt-3 p-4 rounded-xl border border-indigo-200 bg-indigo-50/60 text-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-indigo-950 flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <TrendingUp className="w-4 h-4 text-indigo-600" />
              {card.title}
            </span>
            <Badge variant="info">
              Save {formatINR(card.target_reduction_inr || 0)}/mo
            </Badge>
          </div>

          <div className="space-y-1.5">
            {(card.allocation || []).map((alloc, idx) => (
              <div key={idx} className="p-2.5 bg-white/90 rounded-lg border border-indigo-100 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-800">{alloc.category_name}</span>
                  <p className="text-[10px] text-slate-500 mt-0.5">{alloc.action_tip}</p>
                </div>
                <div className="text-right font-mono">
                  <span className="text-emerald-700 font-bold">-{formatINR(alloc.recommended_cut_inr)}</span>
                  <p className="text-[10px] text-slate-400">Target: {formatINR(alloc.target_spent_inr)}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between text-[11px] pt-1 text-indigo-900 border-t border-indigo-200/60">
            <span>Projected Monthly Savings: <strong>{formatINR(card.projected_monthly_savings_inr || 0)}</strong></span>
            <span>Projected Savings Rate: <strong>{card.projected_savings_rate_pct}%</strong></span>
          </div>
        </div>
      )
    }

    if (card.type === 'SAVINGS_HORIZON') {
      return (
        <div className="mt-3 p-4 rounded-xl border border-teal-200 bg-teal-50/60 text-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-teal-950 flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
              <Calendar className="w-4 h-4 text-teal-600" />
              {card.title}
            </span>
            <Badge variant="teal">
              +{formatINR(card.additional_wealth_inr || 0)} Wealth Created
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-3 text-[11px]">
            <div className="p-2.5 bg-white rounded-lg border border-teal-100">
              <span className="text-slate-500">Baseline Cumulative ({card.months} mo)</span>
              <p className="font-bold font-mono text-slate-700 mt-0.5">{formatINR(card.baseline_cumulative_inr || 0)}</p>
            </div>
            <div className="p-2.5 bg-white rounded-lg border border-teal-100">
              <span className="text-slate-500">Optimized Cumulative ({card.months} mo)</span>
              <p className="font-bold font-mono text-teal-700 mt-0.5">{formatINR(card.optimized_cumulative_inr || 0)}</p>
            </div>
          </div>
        </div>
      )
    }

    return null
  }

  return (
    <div className="h-[calc(100vh-8.5rem)] flex bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
      {/* 1. Left Sidebar: Conversation History Sessions */}
      <div className="w-72 shrink-0 border-r border-slate-200 bg-slate-50/70 flex flex-col justify-between hidden md:flex">
        {/* Sidebar Header */}
        <div className="p-3.5 border-b border-slate-200/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-xs">
              <Bot className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-900 tracking-tight">Copilot Discussions</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => createConvMutation.mutate('New Discussion')}
            isLoading={createConvMutation.isPending}
            title="Start new conversation"
          >
            <Plus className="w-3.5 h-3.5" />
          </Button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isConvLoading ? (
            <div className="p-4 text-center text-xs text-slate-400">Loading discussions...</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-400">No active discussions. Start one above!</div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeConvId
              const isEditing = editingConvId === conv.id

              return (
                <div
                  key={conv.id}
                  onClick={() => !isEditing && setActiveConvId(conv.id)}
                  className={`group relative flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                    isActive
                      ? 'bg-white text-navy-900 shadow-xs border border-slate-200 font-semibold'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden flex-1 mr-2">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                    {isEditing ? (
                      <input
                        type="text"
                        value={renameTitle}
                        onChange={(e) => setRenameTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            renameConvMutation.mutate({ id: conv.id, title: renameTitle })
                          } else if (e.key === 'Escape') {
                            setEditingConvId(null)
                          }
                        }}
                        autoFocus
                        className="w-full text-xs px-1.5 py-0.5 rounded border border-teal-500 bg-white"
                      />
                    ) : (
                      <span className="truncate">{conv.title}</span>
                    )}
                  </div>

                  {/* Actions (Rename / Delete) */}
                  {isEditing ? (
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          renameConvMutation.mutate({ id: conv.id, title: renameTitle })
                        }}
                        className="text-teal-600 hover:text-teal-800 p-0.5"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingConvId(null)
                        }}
                        className="text-slate-400 hover:text-slate-600 p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="hidden group-hover:flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingConvId(conv.id)
                          setRenameTitle(conv.title)
                        }}
                        className="text-slate-400 hover:text-slate-700 p-0.5"
                        title="Rename"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this conversation session?')) {
                            deleteConvMutation.mutate(conv.id)
                          }
                        }}
                        className="text-slate-400 hover:text-rose-600 p-0.5"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* Sidebar Footer info */}
        <div className="p-3 border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-600" /> Grounded in Ledger
          </span>
          <span className="font-mono text-[10px] bg-slate-200/80 px-1.5 py-0.5 rounded">Milestone 5</span>
        </div>
      </div>

      {/* 2. Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden bg-white">
        {/* Chat Top Header */}
        <div className="p-3.5 sm:p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-teal-600 text-white flex items-center justify-center shadow-xs md:hidden">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                  {activeConversation?.title || 'FinPilot AI Financial Copilot'}
                </h2>
                <Badge variant="teal">Grounding Active</Badge>
              </div>
              <p className="text-[11px] text-slate-500">
                Deterministic calculations & tool-assisted reasoning over accounts, transactions, and cash-flow models
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <div className="hidden sm:flex items-center space-x-1.5 text-xs text-slate-500 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
              <Cpu className="w-3.5 h-3.5 text-indigo-600" />
              <span>Provider: Groq (Llama-3.3-70B) / Offline Mock</span>
            </div>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {isMessagesLoading ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-2">
                <Loader2 className="w-6 h-6 animate-spin text-teal-600 mx-auto" />
                <p className="text-xs text-slate-500">Loading conversation history...</p>
              </div>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === 'USER'

              return (
                <div
                  key={m.id}
                  className={`flex items-start space-x-3 max-w-3xl ${
                    isUser ? 'ml-auto flex-row-reverse space-x-reverse' : 'mr-auto'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                      isUser
                        ? 'bg-navy-900 text-white shadow-xs'
                        : 'bg-teal-600 text-white shadow-xs'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? 'bg-navy-900 text-white rounded-tr-none shadow-xs'
                        : 'bg-slate-50 text-slate-900 rounded-tl-none border border-slate-200/90 shadow-xs'
                    }`}
                  >
                    {/* Message Body */}
                    <div className="whitespace-pre-wrap space-y-2">
                      {m.content}
                    </div>

                    {/* Scenario Card if present */}
                    {renderScenarioCard(m.scenario_card)}

                    {/* Citations Tag Strip if present */}
                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200/80 flex flex-wrap items-center gap-1.5 text-[10px]">
                        <span className="font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                          <Database className="w-3 h-3 text-teal-600" /> Evidence Citing:
                        </span>
                        {m.citations.map((c, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 font-mono"
                            title={`${c.detail} (${c.source})`}
                          >
                            {c.title}: <strong className="text-slate-900">{c.value}</strong>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Message Metadata Footer */}
                    <div
                      className={`mt-2 text-[10px] font-mono flex items-center justify-between ${
                        isUser ? 'text-slate-300' : 'text-slate-400'
                      }`}
                    >
                      <span>{m.created_at}</span>
                      {!isUser && (
                        <span className="flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3 text-teal-600" /> Verified Deterministic
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}

          {sendMessageMutation.isPending && (
            <div className="flex items-start space-x-3 mr-auto max-w-md">
              <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs shrink-0 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 text-slate-700 text-xs rounded-tl-none border border-slate-200 flex items-center space-x-2.5">
                <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
                <span className="font-medium animate-pulse">
                  Querying verified ledger, running tools, and synthesizing grounded answer...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Follow-up Prompts or Curated Prompts */}
        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/80 overflow-x-auto flex items-center gap-1.5 shrink-0 text-xs">
          <span className="text-[11px] font-semibold text-slate-500 shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-teal-600" /> Suggested:
          </span>
          {(activeFollowups.length > 0 ? activeFollowups : CURATED_PROMPTS).map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              disabled={sendMessageMutation.isPending}
              className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white hover:bg-teal-50 hover:text-teal-700 hover:border-teal-300 border border-slate-200 text-slate-700 font-medium transition-all text-[11px] shadow-2xs"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3.5 border-t border-slate-200 bg-white shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend(queryInput)
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Ask about your expenses, affordability, recurring bills, forecast dip..."
              className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 shadow-2xs"
            />
            <Button
              type="submit"
              disabled={!queryInput.trim() || sendMessageMutation.isPending}
              isLoading={sendMessageMutation.isPending}
              icon={<Send className="w-4 h-4" />}
            >
              Ask Copilot
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default CopilotPage
