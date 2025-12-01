'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import {
  fetchAgentsList,
  fetchAgentDetails,
  fetchAgentContext,
  fetchAgentSessions,
  createAgentSession,
  invokeAgent,
  updateAgent,
  updateAgentStatus,
  deleteAgent,
} from '@/lib/agents';
import type {
  AgentSummary,
  AgentDetails,
  AgentContextResponseData,
  AgentDialogSession,
  AgentInvocationRequest,
  AgentInvocationResponseData,
  UpdateAgentRequest,
  AgentStatus,
} from '@/types/api';

/**
 * Hook to fetch list of all agents
 */
export function useAgentsList(limit = 100, options?: Omit<UseQueryOptions<AgentSummary[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<AgentSummary[]>({
    queryKey: ['agents', 'list', limit],
    queryFn: () => fetchAgentsList(limit),
    staleTime: 30_000,
    ...options,
  });
}

/**
 * Hook to fetch detailed information about a specific agent
 */
export function useAgentDetails(agentId: string, options?: Omit<UseQueryOptions<AgentDetails | null, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<AgentDetails | null>({
    queryKey: ['agents', 'details', agentId],
    queryFn: () => fetchAgentDetails(agentId),
    enabled: Boolean(agentId),
    staleTime: 10_000,
    ...options,
  });
}

/**
 * Hook to fetch agent context (system prompt, code path, tools path)
 */
export function useAgentContext(agentId: string, options?: Omit<UseQueryOptions<AgentContextResponseData | null, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<AgentContextResponseData | null>({
    queryKey: ['agents', 'context', agentId],
    queryFn: () => fetchAgentContext(agentId),
    enabled: Boolean(agentId),
    staleTime: 60_000,
    ...options,
  });
}

/**
 * Hook to fetch all sessions for an agent
 */
export function useAgentSessions(agentId: string, options?: Omit<UseQueryOptions<AgentDialogSession[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<AgentDialogSession[]>({
    queryKey: ['agents', 'sessions', agentId],
    queryFn: () => fetchAgentSessions(agentId),
    enabled: Boolean(agentId),
    staleTime: 10_000,
    ...options,
  });
}

/**
 * Hook to create a new session for an agent
 */
export function useCreateAgentSession(
  options?: UseMutationOptions<
    {
      session_id: string;
      display_name?: string;
      created_at: string;
      last_active_at?: string;
    },
    Error,
    { agentId: string; displayName?: string }
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    {
      session_id: string;
      display_name?: string;
      created_at: string;
      last_active_at?: string;
    },
    Error,
    { agentId: string; displayName?: string }
  >({
    mutationFn: ({ agentId, displayName }) => createAgentSession(agentId, displayName),
    onSuccess: (data, variables) => {
      // Invalidate agent sessions list
      queryClient.invalidateQueries({ queryKey: ['agents', 'sessions', variables.agentId] });
    },
    ...options,
  });
}

/**
 * Hook to invoke an agent with input text
 */
export function useInvokeAgent(
  options?: UseMutationOptions<
    AgentInvocationResponseData,
    Error,
    { agentId: string; request: AgentInvocationRequest }
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    AgentInvocationResponseData,
    Error,
    { agentId: string; request: AgentInvocationRequest }
  >({
    mutationFn: ({ agentId, request }) => invokeAgent(agentId, request),
    onSuccess: (data, variables) => {
      // Invalidate agent details to update runtime stats
      queryClient.invalidateQueries({ queryKey: ['agents', 'details', variables.agentId] });
      // If session_id is provided, invalidate session messages
      if (data.session_id) {
        queryClient.invalidateQueries({ queryKey: ['sessions', 'messages', data.session_id] });
      }
    },
    ...options,
  });
}

/**
 * Hook to update agent configuration
 */
export function useUpdateAgent(
  options?: UseMutationOptions<AgentDetails, Error, { agentId: string; request: UpdateAgentRequest }>,
) {
  const queryClient = useQueryClient();

  return useMutation<AgentDetails, Error, { agentId: string; request: UpdateAgentRequest }>({
    mutationFn: ({ agentId, request }) => updateAgent(agentId, request),
    onSuccess: (data, variables) => {
      // Update cached agent details
      queryClient.setQueryData(['agents', 'details', variables.agentId], data);
      // Invalidate agent list
      queryClient.invalidateQueries({ queryKey: ['agents', 'list'] });
    },
    ...options,
  });
}

/**
 * Hook to update agent status
 */
export function useUpdateAgentStatus(
  options?: UseMutationOptions<
    AgentDetails,
    Error,
    { agentId: string; status: AgentStatus; errorMessage?: string }
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    AgentDetails,
    Error,
    { agentId: string; status: AgentStatus; errorMessage?: string }
  >({
    mutationFn: ({ agentId, status, errorMessage }) => updateAgentStatus(agentId, status, errorMessage),
    onSuccess: (data, variables) => {
      // Update cached agent details
      queryClient.setQueryData(['agents', 'details', variables.agentId], data);
      // Invalidate agent list
      queryClient.invalidateQueries({ queryKey: ['agents', 'list'] });
    },
    ...options,
  });
}

/**
 * Hook to delete an agent
 */
export function useDeleteAgent(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>,
) {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; message?: string }, Error, string>({
    mutationFn: deleteAgent,
    onSuccess: (data, agentId) => {
      // Remove all cached data for this agent
      queryClient.removeQueries({ queryKey: ['agents', 'details', agentId] });
      queryClient.removeQueries({ queryKey: ['agents', 'context', agentId] });
      queryClient.removeQueries({ queryKey: ['agents', 'sessions', agentId] });
      // Invalidate agent list
      queryClient.invalidateQueries({ queryKey: ['agents', 'list'] });
    },
    ...options,
  });
}
