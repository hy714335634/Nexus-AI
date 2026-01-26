'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import * as apiV2 from '@/lib/api-v2';
import type { SessionRecord, MessageRecord, SendMessageRequest } from '@/types/api-v2';

// ============== Query Keys ==============
export const sessionKeys = {
  all: ['v2', 'sessions'] as const,
  lists: () => [...sessionKeys.all, 'list'] as const,
  detail: (id: string) => [...sessionKeys.all, 'detail', id] as const,
  messages: (id: string) => [...sessionKeys.all, 'messages', id] as const,
};

// ============== Session Detail ==============
export function useSessionDetailV2(
  sessionId: string,
  options?: Omit<UseQueryOptions<SessionRecord | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SessionRecord | null>({
    queryKey: sessionKeys.detail(sessionId),
    queryFn: async () => {
      const response = await apiV2.getSession(sessionId);
      return response.data || null;
    },
    enabled: Boolean(sessionId),
    staleTime: 10_000,
    ...options,
  });
}

// ============== Session Messages ==============
export function useSessionMessagesV2(
  sessionId: string,
  limit?: number,
  options?: Omit<UseQueryOptions<MessageRecord[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<MessageRecord[]>({
    queryKey: sessionKeys.messages(sessionId),
    queryFn: async () => {
      const response = await apiV2.listMessages(sessionId, limit);
      return response.data || [];
    },
    enabled: Boolean(sessionId) && sessionId.length > 0,
    staleTime: 5_000, // 减少 stale time 到 5 秒，确保切换会话时能更快获取新数据
    refetchInterval: false, // 禁用自动轮询，由前端手动控制刷新时机
    ...options,
  });
}

// ============== Send Message ==============
export function useSendMessageV2(
  options?: UseMutationOptions<MessageRecord, Error, { sessionId: string; content: string; role?: 'user' | 'assistant' | 'system' }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sessionId, content, role = 'user' }) => {
      const response = await apiV2.sendMessage(sessionId, { content, role });
      if (!response.data) throw new Error(response.message || '发送消息失败');
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.messages(variables.sessionId) });
      queryClient.invalidateQueries({ queryKey: sessionKeys.detail(variables.sessionId) });
    },
    ...options,
  });
}

// ============== Delete Session ==============
export function useDeleteSessionV2(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await apiV2.deleteSession(sessionId);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, sessionId) => {
      queryClient.removeQueries({ queryKey: sessionKeys.detail(sessionId) });
      queryClient.removeQueries({ queryKey: sessionKeys.messages(sessionId) });
      // 同时刷新会话列表
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() });
    },
    ...options,
  });
}


// ============== Agent Sessions List ==============
export function useAgentSessionsV2(
  agentId: string,
  options?: Omit<UseQueryOptions<SessionRecord[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SessionRecord[]>({
    queryKey: [...sessionKeys.lists(), agentId],
    queryFn: async () => {
      const response = await apiV2.listAgentSessions(agentId);
      return response.data || [];
    },
    enabled: Boolean(agentId),
    staleTime: 10_000,
    ...options,
  });
}

// ============== Create Session ==============
export function useCreateSessionV2(
  options?: UseMutationOptions<SessionRecord, Error, { agentId: string; title?: string }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, title }) => {
      const response = await apiV2.createSession(agentId, title ? { display_name: title } : undefined);
      if (!response.data) throw new Error(response.message || '创建会话失败');
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [...sessionKeys.lists(), variables.agentId] });
    },
    ...options,
  });
}

// ============== Streaming Chat ==============
export interface StreamingState {
  isStreaming: boolean;
  content: string;
  error?: string;
}

export function useStreamingChatV2() {
  // This is a placeholder - streaming is typically handled differently
  // The actual implementation would use EventSource or fetch with streaming
  return {
    startStream: async (_sessionId: string, _message: string) => {
      // Implementation would go here
    },
    stopStream: () => {
      // Implementation would go here
    },
    state: { isStreaming: false, content: '', error: undefined } as StreamingState,
  };
}
