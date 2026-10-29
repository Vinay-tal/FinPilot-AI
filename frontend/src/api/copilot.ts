import { apiClient } from './client'
import {
  ChatMessage,
  CopilotResponse,
  ConversationItem,
  CopilotTurnResponse,
} from '@/types'

export async function listConversationsApi(): Promise<ConversationItem[]> {
  return apiClient<ConversationItem[]>('/copilot/conversations')
}

export async function createConversationApi(title?: string): Promise<ConversationItem> {
  return apiClient<ConversationItem>('/copilot/conversations', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export async function renameConversationApi(
  conversationId: string,
  title: string
): Promise<ConversationItem> {
  return apiClient<ConversationItem>(`/copilot/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export async function deleteConversationApi(conversationId: string): Promise<void> {
  return apiClient<void>(`/copilot/conversations/${conversationId}`, {
    method: 'DELETE',
  })
}

export async function getConversationMessagesApi(
  conversationId: string
): Promise<ChatMessage[]> {
  return apiClient<ChatMessage[]>(`/copilot/conversations/${conversationId}/messages`)
}

export async function sendConversationMessageApi(
  conversationId: string,
  query: string
): Promise<CopilotTurnResponse> {
  return apiClient<CopilotTurnResponse>(
    `/copilot/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ query }),
    }
  )
}

// Legacy helpers
export async function getChatHistoryApi(): Promise<ChatMessage[]> {
  return apiClient<ChatMessage[]>('/copilot/history')
}

export async function askCopilotApi(query: string): Promise<CopilotResponse> {
  return apiClient<CopilotResponse>('/copilot/query', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}
