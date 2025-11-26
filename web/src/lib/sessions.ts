import { apiFetch } from '@/lib/api-client';
import type {
  AgentDialogMessagesResponse,
  SendMessageRequest,
  SendMessageResponse,
} from '@/types/api';

/**
 * Fetch messages for a session
 * @param sessionId - Session ID
 * @returns List of messages in the session
 */
export async function fetchSessionMessages(sessionId: string) {
  const response = await apiFetch<{
    success: boolean;
    data: AgentDialogMessagesResponse;
  }>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/messages`);

  if (!response.success) {
    throw new Error('Failed to load messages');
  }
  return response.data.messages;
}

/**
 * Send a message to a session
 * @param sessionId - Session ID
 * @param request - Message content and metadata
 * @returns Assistant's response message
 */
export async function sendMessage(sessionId: string, request: SendMessageRequest) {
  const response = await apiFetch<SendMessageResponse>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/messages`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to send message');
  }

  return response.data;
}

/**
 * Get session details
 * @param sessionId - Session ID
 * @returns Session details including agent_id, status, and metadata
 */
export async function fetchSessionDetails(sessionId: string) {
  const response = await apiFetch<{
    success: boolean;
    data: {
      session_id: string;
      agent_id: string;
      user_id?: string;
      status: string;
      metadata?: Record<string, unknown>;
      created_at: string;
      last_active_at?: string;
    };
  }>(`/api/v1/sessions/${encodeURIComponent(sessionId)}`);

  if (!response.success) {
    throw new Error('Failed to fetch session details');
  }

  return response.data;
}

/**
 * Delete a session and all its messages
 * @param sessionId - Session ID to delete
 */
export async function deleteSession(sessionId: string) {
  const response = await apiFetch<{ success: boolean; message?: string }>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: 'DELETE',
    },
  );

  if (!response.success) {
    throw new Error('Failed to delete session');
  }

  return response;
}
