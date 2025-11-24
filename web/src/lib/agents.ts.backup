import { apiFetch } from '@/lib/api-client';
import type {
  AgentContextResponse,
  AgentDialogMessagesResponse,
  AgentDialogSessionsResponse,
  AgentListResponse,
  AgentSummary,
  CreateAgentRequest,
  CreateAgentResponse,
} from '@/types/api';

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

export async function fetchAgentSessions(agentId: string) {
  const response = await apiFetch<{
    success: boolean;
    data: AgentDialogSessionsResponse;
  }>(`/api/v1/agents/${encodeURIComponent(agentId)}/sessions`);

  if (!response.success) {
    throw new Error('Failed to load sessions');
  }
  return response.data.sessions;
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

export async function fetchAgentMessages(agentId: string, sessionId: string) {
  const response = await apiFetch<{
    success: boolean;
    data: AgentDialogMessagesResponse;
  }>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(sessionId)}/messages`,
  );

  if (!response.success) {
    throw new Error('Failed to load messages');
  }
  return response.data.messages;
}

export async function fetchAgentContext(agentId: string) {
  const response = await apiFetch<AgentContextResponse>(`/api/v1/agents/${encodeURIComponent(agentId)}/context`);
  if (!response.success) {
    throw new Error('Failed to load agent context');
  }
  return response.data;
}

export async function fetchAgentsList(limit = 100) {
  const response = await apiFetch<AgentListResponse>(`/api/v1/agents?limit=${limit}`);
  if (!response.success) {
    throw new Error('Failed to load agents');
  }
  return response.data.agents as AgentSummary[];
}
