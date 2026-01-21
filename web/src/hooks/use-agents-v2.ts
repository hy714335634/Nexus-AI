'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import * as apiV2 from '@/lib/api-v2';
import type {
  AgentSummary,
  AgentRecord,
  InvokeAgentRequest,
  SessionRecord,
} from '@/types/api-v2';
import type { AgentContext } from '@/lib/api-v2';

// ============== Query Keys ==============
export const agentKeys = {
  all: ['v2', 'agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...agentKeys.lists(), filters] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
  context: (id: string) => [...agentKeys.all, 'context', id] as const,
  sessions: (id: string) => [...agentKeys.all, 'sessions', id] as const,
};

// ============== List Agents ==============
export function useAgentsV2(
  params?: { status?: string; category?: string; page?: number; limit?: number },
  options?: Omit<UseQueryOptions<AgentSummary[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AgentSummary[]>({
    queryKey: agentKeys.list(params || {}),
    queryFn: async () => {
      const response = await apiV2.listAgents(params);
      return response.data || [];
    },
    staleTime: 30_000,
    ...options,
  });
}

// ============== Agent Detail ==============
export function useAgentDetailV2(
  agentId: string,
  options?: Omit<UseQueryOptions<AgentRecord | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AgentRecord | null>({
    queryKey: agentKeys.detail(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgent(agentId);
      return response.data || null;
    },
    enabled: Boolean(agentId),
    staleTime: 10_000,
    ...options,
  });
}

// ============== Agent Context ==============
export function useAgentContextV2(
  agentId: string,
  options?: Omit<UseQueryOptions<AgentContext | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AgentContext | null>({
    queryKey: agentKeys.context(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgentContext(agentId);
      return response.data || null;
    },
    enabled: Boolean(agentId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Invoke Agent ==============
export function useInvokeAgentV2(
  options?: UseMutationOptions<
    { invocation_id: string; session_id?: string; output: string; duration_ms: number; status: string },
    Error,
    { agentId: string; request: InvokeAgentRequest }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, request }) => {
      const response = await apiV2.invokeAgent(agentId, request);
      if (!response.data) throw new Error(response.message || '调用 Agent 失败');
      return response.data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentId) });
      if (data.session_id) {
        queryClient.invalidateQueries({ queryKey: ['v2', 'sessions', 'messages', data.session_id] });
      }
    },
    ...options,
  });
}

// ============== Delete Agent ==============
export function useDeleteAgentV2(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await apiV2.deleteAgent(agentId);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, agentId) => {
      queryClient.removeQueries({ queryKey: agentKeys.detail(agentId) });
      queryClient.removeQueries({ queryKey: agentKeys.sessions(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
    ...options,
  });
}

// ============== Agent Sessions ==============
export function useAgentSessionsV2(
  agentId: string,
  limit?: number,
  options?: Omit<UseQueryOptions<SessionRecord[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SessionRecord[]>({
    queryKey: agentKeys.sessions(agentId),
    queryFn: async () => {
      const response = await apiV2.listAgentSessions(agentId, limit);
      return response.data || [];
    },
    enabled: Boolean(agentId),
    staleTime: 10_000,
    ...options,
  });
}

// ============== Create Session ==============
export function useCreateSessionV2(
  options?: UseMutationOptions<
    SessionRecord,
    Error,
    { agentId: string; displayName?: string }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, displayName }) => {
      const response = await apiV2.createSession(agentId, { display_name: displayName });
      if (!response.data) throw new Error(response.message || '创建会话失败');
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.sessions(variables.agentId) });
    },
    ...options,
  });
}
