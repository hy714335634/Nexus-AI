'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import {
  fetchSessionMessages,
  fetchSessionDetails,
  sendMessage,
  deleteSession,
} from '@/lib/sessions';
import type {
  AgentDialogMessage,
  SendMessageRequest,
  SendMessageResponseData,
} from '@/types/api';

/**
 * Hook to fetch messages for a session
 */
export function useSessionMessages(sessionId: string, options?: Omit<UseQueryOptions<AgentDialogMessage[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<AgentDialogMessage[]>({
    queryKey: ['sessions', 'messages', sessionId],
    queryFn: () => fetchSessionMessages(sessionId),
    enabled: Boolean(sessionId),
    staleTime: 5_000,
    ...options,
  });
}

/**
 * Hook to fetch session details
 */
export function useSessionDetails(
  sessionId: string,
  options?: Omit<UseQueryOptions<{
    session_id: string;
    agent_id: string;
    user_id?: string;
    status: string;
    metadata?: Record<string, unknown>;
    created_at: string;
    last_active_at?: string;
  }, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<{
    session_id: string;
    agent_id: string;
    user_id?: string;
    status: string;
    metadata?: Record<string, unknown>;
    created_at: string;
    last_active_at?: string;
  }>({
    queryKey: ['sessions', 'details', sessionId],
    queryFn: () => fetchSessionDetails(sessionId),
    enabled: Boolean(sessionId),
    staleTime: 10_000,
    ...options,
  });
}

/**
 * Hook to send a message to a session
 */
export function useSendMessage(
  options?: UseMutationOptions<
    SendMessageResponseData,
    Error,
    { sessionId: string; request: SendMessageRequest }
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    SendMessageResponseData,
    Error,
    { sessionId: string; request: SendMessageRequest }
  >({
    mutationFn: ({ sessionId, request }) => sendMessage(sessionId, request),
    onSuccess: (data, variables) => {
      // Invalidate session messages to refetch with new message
      queryClient.invalidateQueries({ queryKey: ['sessions', 'messages', variables.sessionId] });
      // Update session details (last_active_at might have changed)
      queryClient.invalidateQueries({ queryKey: ['sessions', 'details', variables.sessionId] });
    },
    ...options,
  });
}

/**
 * Hook to delete a session
 */
export function useDeleteSession(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>,
) {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; message?: string }, Error, string>({
    mutationFn: deleteSession,
    onSuccess: (data, sessionId) => {
      // Remove all cached data for this session
      queryClient.removeQueries({ queryKey: ['sessions', 'messages', sessionId] });
      queryClient.removeQueries({ queryKey: ['sessions', 'details', sessionId] });

      // Invalidate agent sessions lists (the session should no longer appear)
      queryClient.invalidateQueries({ queryKey: ['agents', 'sessions'] });
    },
    ...options,
  });
}
