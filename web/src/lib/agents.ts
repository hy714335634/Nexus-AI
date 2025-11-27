import { apiFetch } from '@/lib/api-client';
import {
  fetchSessionMessages as fetchSessionMessagesFromSessions,
  sendMessage as sendMessageToSession,
  fetchSessionDetails as fetchSessionDetailsFromSessions,
  deleteSession as deleteSessionFromSessions,
} from '@/lib/sessions';
import type {
  AgentContextResponse,
  AgentDialogMessagesResponse,
  AgentDialogSessionsResponse,
  AgentListResponse,
  AgentSummary,
  AgentDetailsResponse,
  CreateAgentRequest,
  CreateAgentResponse,
  AgentInvocationRequest,
  AgentInvocationResponse,
  UpdateAgentRequest,
  UpdateAgentStatusRequest,
  SendMessageRequest,
  AgentStatus,
} from '@/types/api';

/**
 * Create a new agent project (legacy endpoint - prefer createProject from projects.ts)
 * @deprecated Use createProject from projects.ts instead
 */
export async function createAgent(request: CreateAgentRequest) {
  const response = await apiFetch<CreateAgentResponse>(
    '/api/v1/agents/create',
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to submit agent build request');
  }

  return response.data;
}

/**
 * Invoke a deployed agent with input text
 * @param agentId - Agent ID
 * @param request - Invocation parameters
 * @returns Invocation result with output and metadata
 */
export async function invokeAgent(agentId: string, request: AgentInvocationRequest) {
  const response = await apiFetch<AgentInvocationResponse>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/invoke`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to invoke agent');
  }

  return response.data;
}

/**
 * Update agent configuration
 * @param agentId - Agent ID
 * @param request - Fields to update
 * @returns Updated agent data
 */
export async function updateAgent(agentId: string, request: UpdateAgentRequest) {
  const response = await apiFetch<AgentDetailsResponse>(
    `/api/v1/agents/${encodeURIComponent(agentId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to update agent');
  }

  return response.data;
}

/**
 * Update agent status
 * @param agentId - Agent ID
 * @param status - New status
 * @param errorMessage - Optional error message if status is 'error'
 * @returns Updated agent data
 */
export async function updateAgentStatus(
  agentId: string,
  status: AgentStatus,
  errorMessage?: string
) {
  const response = await apiFetch<AgentDetailsResponse>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/status`,
    {
      method: 'PUT',
      body: JSON.stringify({ status, error_message: errorMessage }),
    },
  );

  if (!response.success) {
    throw new Error('Failed to update agent status');
  }

  return response.data;
}

/**
 * Delete an agent and all associated resources
 * @param agentId - Agent ID to delete
 */
export async function deleteAgent(agentId: string) {
  const response = await apiFetch<{ success: boolean; message?: string }>(
    `/api/v1/agents/${encodeURIComponent(agentId)}`,
    {
      method: 'DELETE',
    },
  );

  if (!response.success) {
    throw new Error('Failed to delete agent');
  }

  return response;
}

/**
 * Get detailed agent information
 * @param agentId - Agent ID
 * @returns Agent details including runtime stats
 */
export async function fetchAgentDetails(agentId: string) {
  try {
    const response = await apiFetch<AgentDetailsResponse>(
      `/api/v1/agents/${encodeURIComponent(agentId)}`
    );

    if (!response.success) {
      return null; // 返回 null 而不是抛出错误
    }

    return response.data ?? null;
  } catch {
    // API 错误时返回 null，避免 React Query 报错
    return null;
  }
}

export async function fetchAgentSessions(agentId: string) {
  try {
    const response = await apiFetch<{
      success: boolean;
      data: AgentDialogSessionsResponse;
    }>(`/api/v1/agents/${encodeURIComponent(agentId)}/sessions`);

    if (!response.success) {
      return []; // 返回空数组而不是抛出错误
    }
    return response.data?.sessions ?? [];
  } catch {
    // API 错误时返回空数组，避免 React Query 报错
    return [];
  }
}

export async function createAgentSession(agentId: string, displayName?: string) {
  const response = await apiFetch<{
    success: boolean;
    data: {
      session_id: string;
      display_name?: string;
      created_at: string;
      last_active_at?: string;
    };
  }>(`/api/v1/agents/${encodeURIComponent(agentId)}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName }),
  });

  if (!response.success) {
    throw new Error('Failed to create session');
  }
  return response.data;
}

/**
 * Fetch messages for a session
 * @param sessionId - Session ID
 * @returns List of messages
 */
export async function fetchSessionMessages(sessionId: string) {
  return fetchSessionMessagesFromSessions(sessionId);
}

/**
 * Fetch messages for a session (legacy endpoint)
 * @deprecated Use fetchSessionMessages instead
 */
export async function fetchAgentMessages(agentId: string, sessionId: string) {
  // For backwards compatibility, try the new endpoint first
  try {
    const messages = await fetchSessionMessagesFromSessions(sessionId);
    return messages ?? [];
  } catch {
    // Fallback to old endpoint pattern
    try {
      const response = await apiFetch<{
        success: boolean;
        data: AgentDialogMessagesResponse;
      }>(
        `/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(sessionId)}/messages`,
      );

      if (!response.success) {
        return []; // 返回空数组而不是抛出错误
      }
      return response.data?.messages ?? [];
    } catch {
      // 所有 API 都失败时返回空数组
      return [];
    }
  }
}

/**
 * Send a message to a session
 * @param sessionId - Session ID
 * @param request - Message content and metadata
 * @returns Assistant's response message
 */
export async function sendMessage(sessionId: string, request: SendMessageRequest) {
  return sendMessageToSession(sessionId, request);
}

/**
 * Get session details
 * @param sessionId - Session ID
 * @returns Session details
 */
export async function fetchSessionDetails(sessionId: string) {
  return fetchSessionDetailsFromSessions(sessionId);
}

/**
 * Delete a session and all its messages
 * @param sessionId - Session ID to delete
 */
export async function deleteSession(sessionId: string) {
  return deleteSessionFromSessions(sessionId);
}

export async function fetchAgentContext(agentId: string) {
  try {
    const response = await apiFetch<AgentContextResponse>(`/api/v1/agents/${encodeURIComponent(agentId)}/context`);
    if (!response.success) {
      return null; // 返回 null 而不是抛出错误
    }
    return response.data ?? null;
  } catch {
    // API 错误时返回 null，避免 React Query 报错
    return null;
  }
}

export async function fetchAgentsList(limit = 100) {
  try {
    const response = await apiFetch<AgentListResponse>(`/api/v1/agents?limit=${limit}`);
    if (!response.success) {
      return []; // 返回空数组而不是抛出错误
    }
    return (response.data?.agents ?? []) as AgentSummary[];
  } catch {
    // API 错误时返回空数组，避免 React Query 报错
    return [];
  }
}
