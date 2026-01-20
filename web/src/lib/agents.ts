import { apiFetch } from './api-client';
import type {
  AgentListResponse,
  AgentDetailsResponse,
  AgentContextResponse,
  AgentDialogSessionsResponse,
  AgentInvocationRequest,
  AgentInvocationResponse,
  UpdateAgentRequest,
  UpdateAgentStatusRequest,
  AgentSummary,
  AgentDetails,
  AgentContextResponseData,
  AgentDialogSession,
  AgentInvocationResponseData,
  AgentStatus,
} from '@/types/api';

export async function fetchAgentsList(limit = 100): Promise<AgentSummary[]> {
  const response = await apiFetch<AgentListResponse>(`/api/v1/agents?limit=${limit}`);
  return response.data.agents;
}

export async function fetchAgentDetails(agentId: string): Promise<AgentDetails | null> {
  try {
    const response = await apiFetch<AgentDetailsResponse>(`/api/v1/agents/${agentId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch agent details:', error);
    return null;
  }
}

export async function fetchAgentContext(agentId: string): Promise<AgentContextResponseData | null> {
  try {
    const response = await apiFetch<AgentContextResponse>(`/api/v1/agents/${agentId}/context`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch agent context:', error);
    return null;
  }
}

export async function fetchAgentSessions(agentId: string): Promise<AgentDialogSession[]> {
  try {
    const response = await apiFetch<AgentDialogSessionsResponse>(`/api/v1/agents/${agentId}/sessions`);
    return response.sessions;
  } catch (error) {
    console.error('Failed to fetch agent sessions:', error);
    return [];
  }
}

export async function createAgentSession(
  agentId: string,
  displayName?: string
): Promise<{ session_id: string; display_name?: string; created_at: string; last_active_at?: string }> {
  const response = await apiFetch<{
    success: boolean;
    data: { session_id: string; display_name?: string; created_at: string; last_active_at?: string };
  }>(`/api/v1/agents/${agentId}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName }),
  });
  return response.data;
}

export async function invokeAgent(
  agentId: string,
  request: AgentInvocationRequest
): Promise<AgentInvocationResponseData> {
  const response = await apiFetch<AgentInvocationResponse>(`/api/v1/agents/${agentId}/invoke`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
  return response.data;
}

export async function updateAgent(agentId: string, request: UpdateAgentRequest): Promise<AgentDetails> {
  const response = await apiFetch<AgentDetailsResponse>(`/api/v1/agents/${agentId}`, {
    method: 'PATCH',
    body: JSON.stringify(request),
  });
  return response.data;
}

export async function updateAgentStatus(
  agentId: string,
  status: AgentStatus,
  errorMessage?: string
): Promise<AgentDetails> {
  const request: UpdateAgentStatusRequest = { status, error_message: errorMessage };
  const response = await apiFetch<AgentDetailsResponse>(`/api/v1/agents/${agentId}/status`, {
    method: 'PUT',
    body: JSON.stringify(request),
  });
  return response.data;
}

export async function deleteAgent(agentId: string): Promise<{ success: boolean; message?: string }> {
  return apiFetch<{ success: boolean; message?: string }>(`/api/v1/agents/${agentId}`, {
    method: 'DELETE',
  });
}

export async function fetchAgentMessages(
  agentId: string,
  sessionId: string
): Promise<Array<{ message_id: string; role: string; content: string; created_at: string; metadata?: Record<string, unknown> }>> {
  try {
    const response = await apiFetch<{
      success: boolean;
      data: { messages: Array<{ message_id: string; role: string; content: string; created_at: string; metadata?: Record<string, unknown> }> };
    }>(`/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(sessionId)}/messages`);
    return response.data.messages;
  } catch (error) {
    console.error('Failed to fetch agent messages:', error);
    return [];
  }
}


// 创建 Agent (v1 API 兼容)
export async function createAgent(request: {
  requirement: string;
  agent_name?: string;
  user_id?: string;
  user_name?: string;
  priority?: number;
  tags?: string[];
}): Promise<{ task_id: string; agent_id: string; agent_name?: string; project_id?: string }> {
  const response = await apiFetch<{
    success: boolean;
    data: { task_id: string; agent_id: string; agent_name?: string; project_id?: string };
  }>('/api/v1/agents', {
    method: 'POST',
    body: JSON.stringify(request),
  });
  return response.data;
}
