import { apiFetch } from '@/lib/api-client';

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
