'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import * as apiV2 from '@/lib/api-v2';
import type {
  AgentSummary,
  AgentRecord,
  InvokeAgentRequest,
  SessionRecord,
  AgentFilesData,
  FileInfo,
  ToolFileInfo,
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
  files: (id: string) => [...agentKeys.all, 'files', id] as const,
  fileCode: (id: string) => [...agentKeys.files(id), 'code'] as const,
  filePrompt: (id: string) => [...agentKeys.files(id), 'prompt'] as const,
  fileTools: (id: string) => [...agentKeys.files(id), 'tools'] as const,
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


// ============== Agent Files ==============
export function useAgentFilesV2(
  agentId: string,
  includeContent: boolean = true,
  options?: Omit<UseQueryOptions<AgentFilesData | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AgentFilesData | null>({
    queryKey: agentKeys.files(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgentFiles(agentId, includeContent);
      return response.data || null;
    },
    enabled: Boolean(agentId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Agent Code File ==============
export function useAgentCodeV2(
  agentId: string,
  options?: Omit<UseQueryOptions<FileInfo | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<FileInfo | null>({
    queryKey: agentKeys.fileCode(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgentCode(agentId);
      return response.data || null;
    },
    enabled: Boolean(agentId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Agent Prompt File ==============
export function useAgentPromptV2(
  agentId: string,
  options?: Omit<UseQueryOptions<FileInfo | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<FileInfo | null>({
    queryKey: agentKeys.filePrompt(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgentPrompt(agentId);
      return response.data || null;
    },
    enabled: Boolean(agentId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Agent Tool Files ==============
export function useAgentToolsV2(
  agentId: string,
  options?: Omit<UseQueryOptions<ToolFileInfo[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ToolFileInfo[]>({
    queryKey: agentKeys.fileTools(agentId),
    queryFn: async () => {
      const response = await apiV2.getAgentTools(agentId);
      return response.data || [];
    },
    enabled: Boolean(agentId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Save Agent Code ==============
export function useSaveAgentCodeV2(
  options?: Omit<UseMutationOptions<{ success: boolean; message?: string }, Error, { agentId: string; content: string }>, 'mutationFn'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, content }: { agentId: string; content: string }) => {
      const response = await apiV2.saveAgentCode(agentId, content);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.files(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.fileCode(variables.agentId) });
    },
    ...options,
  });
}

// ============== Save Agent Prompt ==============
export function useSaveAgentPromptV2(
  options?: Omit<UseMutationOptions<{ success: boolean; message?: string }, Error, { agentId: string; content: string }>, 'mutationFn'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, content }: { agentId: string; content: string }) => {
      const response = await apiV2.saveAgentPrompt(agentId, content);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.files(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.filePrompt(variables.agentId) });
    },
    ...options,
  });
}

// ============== Save Agent Tool ==============
export function useSaveAgentToolV2(
  options?: Omit<UseMutationOptions<
    { success: boolean; message?: string },
    Error,
    { agentId: string; toolName: string; content: string }
  >, 'mutationFn'>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ agentId, toolName, content }: { agentId: string; toolName: string; content: string }) => {
      const response = await apiV2.saveAgentTool(agentId, toolName, content);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.files(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.fileTools(variables.agentId) });
    },
    ...options,
  });
}


// ============== Tools Query Keys ==============
export const toolKeys = {
  all: ['v2', 'tools'] as const,
  lists: () => [...toolKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...toolKeys.lists(), filters] as const,
  details: () => [...toolKeys.all, 'detail'] as const,
  detail: (name: string) => [...toolKeys.details(), name] as const,
  categories: () => [...toolKeys.all, 'categories'] as const,
  mcp: () => [...toolKeys.all, 'mcp'] as const,
  mcpServers: () => [...toolKeys.mcp(), 'servers'] as const,
  mcpServer: (name: string) => [...toolKeys.mcp(), 'server', name] as const,
};

// ============== Tool Categories ==============
export function useToolCategories(
  options?: Omit<UseQueryOptions<{ categories: string[]; total: number } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: toolKeys.categories(),
    queryFn: async () => {
      const response = await apiV2.getToolCategories();
      return response.data || null;
    },
    staleTime: 60_000,
    ...options,
  });
}

// ============== Tool List ==============
export function useToolList(
  params?: { type?: string; category?: string; search?: string },
  options?: Omit<UseQueryOptions<{ tools: import('@/types/api-v2').ToolInfo[]; total: number; by_type: Record<string, number> } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: toolKeys.list(params || {}),
    queryFn: async () => {
      const response = await apiV2.listTools(params);
      return response.data || null;
    },
    staleTime: 30_000,
    ...options,
  });
}

// ============== Tool Detail ==============
export function useToolDetail(
  toolName: string,
  type?: string,
  options?: Omit<UseQueryOptions<import('@/types/api-v2').ToolInfo | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: toolKeys.detail(toolName),
    queryFn: async () => {
      const response = await apiV2.getToolDetail(toolName, type);
      return response.data || null;
    },
    enabled: Boolean(toolName),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Test Tool ==============
export function useTestTool(
  options?: UseMutationOptions<
    import('@/types/api-v2').ToolTestResult,
    Error,
    { toolName: string; parameters: Record<string, unknown> }
  >
) {
  return useMutation({
    mutationFn: async ({ toolName, parameters }) => {
      const response = await apiV2.testTool(toolName, { parameters });
      if (!response.data) throw new Error(response.message || 'Tool test failed');
      return response.data;
    },
    ...options,
  });
}

// ============== MCP Servers ==============
export function useMCPServers(
  options?: Omit<UseQueryOptions<{ servers: import('@/types/api-v2').MCPServerInfo[]; total: number; enabled: number; disabled: number } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: toolKeys.mcpServers(),
    queryFn: async () => {
      const response = await apiV2.listMCPServers();
      return response.data || null;
    },
    staleTime: 30_000,
    ...options,
  });
}

// ============== Update MCP Server ==============
export function useUpdateMCPServer(
  options?: UseMutationOptions<
    { success: boolean; message?: string },
    Error,
    { serverName: string; config: { disabled?: boolean; auto_approve?: string[] } }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ serverName, config }) => {
      const response = await apiV2.updateMCPServer(serverName, config);
      return { success: response.success, message: response.message };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.mcpServers() });
      queryClient.invalidateQueries({ queryKey: toolKeys.lists() });
    },
    ...options,
  });
}
