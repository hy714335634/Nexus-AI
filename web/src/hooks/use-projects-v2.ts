'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import * as apiV2 from '@/lib/api-v2';
import type {
  ProjectSummary,
  ProjectDetail,
  StageRecord,
  BuildDashboardData,
  CreateProjectRequest,
  ProjectControlRequest,
} from '@/types/api-v2';

// ============== Query Keys ==============
export const projectKeys = {
  all: ['v2', 'projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...projectKeys.lists(), filters] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  stages: (id: string) => [...projectKeys.all, 'stages', id] as const,
  dashboard: (id: string) => [...projectKeys.all, 'dashboard', id] as const,
};

// ============== List Projects ==============
export function useProjectsV2(
  params?: { status?: string; user_id?: string; page?: number; limit?: number },
  options?: Omit<UseQueryOptions<ProjectSummary[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ProjectSummary[]>({
    queryKey: projectKeys.list(params || {}),
    queryFn: async () => {
      const response = await apiV2.listProjects(params);
      return response.data || [];
    },
    staleTime: 30_000,
    ...options,
  });
}

// ============== Project Detail ==============
export function useProjectDetailV2(
  projectId: string,
  options?: Omit<UseQueryOptions<ProjectDetail | null, Error>, 'queryKey' | 'queryFn'>
) {
  const pollAttemptRef = useRef(0);
  const lastFingerprintRef = useRef<string | null>(null);

  const query = useQuery<ProjectDetail | null>({
    queryKey: projectKeys.detail(projectId),
    queryFn: async () => {
      const response = await apiV2.getProject(projectId);
      return response.data || null;
    },
    enabled: Boolean(projectId),
    staleTime: 5_000,
    refetchOnReconnect: true,
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attempt) => Math.min(30_000, 1_000 * 2 ** attempt),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;

      const shouldPoll = data.status === 'building' || data.status === 'pending' || data.status === 'queued';
      if (!shouldPoll) {
        pollAttemptRef.current = 0;
        return false;
      }

      const interval = Math.min(30_000, 3_000 * (pollAttemptRef.current + 1));
      pollAttemptRef.current = Math.min(pollAttemptRef.current + 1, 10);
      return interval;
    },
    ...options,
  });

  useEffect(() => {
    const data = query.data;
    if (!data) return;

    const fingerprint = `${data.status}-${data.current_stage ?? 'none'}-${Math.round(data.progress)}`;
    if (fingerprint !== lastFingerprintRef.current) {
      lastFingerprintRef.current = fingerprint;
      pollAttemptRef.current = 0;
    }
  }, [query.data]);

  return query;
}

// ============== Project Stages ==============
export function useProjectStagesV2(
  projectId: string,
  options?: Omit<UseQueryOptions<StageRecord[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StageRecord[]>({
    queryKey: projectKeys.stages(projectId),
    queryFn: async () => {
      const response = await apiV2.listProjectStages(projectId);
      return response.data || [];
    },
    enabled: Boolean(projectId),
    staleTime: 10_000,
    ...options,
  });
}

// ============== Build Dashboard ==============
export function useBuildDashboardV2(
  projectId: string,
  options?: Omit<UseQueryOptions<BuildDashboardData | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<BuildDashboardData | null>({
    queryKey: projectKeys.dashboard(projectId),
    queryFn: async () => {
      const response = await apiV2.getBuildDashboard(projectId);
      return response.data || null;
    },
    enabled: Boolean(projectId),
    staleTime: 5_000,
    refetchOnReconnect: true,
    refetchOnWindowFocus: false,
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;

      const isBuilding = data.status === 'building' || data.status === 'pending' || data.status === 'queued';
      const hasRunningStage = data.stages.some((stage) => stage.status === 'running');

      if (!isBuilding && !hasRunningStage) return false;
      return 8_000; // Poll every 8 seconds during build
    },
    ...options,
  });
}

// ============== Create Project ==============
export function useCreateProjectV2(
  options?: UseMutationOptions<
    { project_id: string; task_id: string; project_name: string; status: string; message: string },
    Error,
    CreateProjectRequest
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateProjectRequest) => {
      const response = await apiV2.createProject(request);
      if (!response.data) throw new Error(response.message || '创建项目失败');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
    ...options,
  });
}

// ============== Control Project ==============
export function useControlProjectV2(
  options?: UseMutationOptions<
    { success: boolean; message?: string },
    Error,
    { projectId: string; request: ProjectControlRequest }
  >
) {
  const queryClient = useQueryClient();

  return useMutation<
    { success: boolean; message?: string },
    Error,
    { projectId: string; request: ProjectControlRequest }
  >({
    mutationFn: async ({ projectId, request }) => {
      const response = await apiV2.controlProject(projectId, request);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(variables.projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.dashboard(variables.projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
    ...options,
  });
}

// ============== Delete Project ==============
export function useDeleteProjectV2(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const response = await apiV2.deleteProject(projectId);
      return { success: response.success, message: response.message };
    },
    onSuccess: (_, projectId) => {
      queryClient.removeQueries({ queryKey: projectKeys.detail(projectId) });
      queryClient.removeQueries({ queryKey: projectKeys.dashboard(projectId) });
      queryClient.removeQueries({ queryKey: projectKeys.stages(projectId) });
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
    ...options,
  });
}


// ============== Project Files ==============
export function useProjectFilesV2(
  projectId: string,
  options?: Omit<UseQueryOptions<{ files: Array<{ name: string; path: string; size: number; type: string; modified_at: string }>; project_path: string } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: [...projectKeys.all, 'files', projectId] as const,
    queryFn: async () => {
      const response = await fetch(`/api/v2/projects/${projectId}/files`);
      if (!response.ok) throw new Error('获取项目文件列表失败');
      const data = await response.json();
      return data.data || null;
    },
    enabled: Boolean(projectId),
    staleTime: 30_000,
    ...options,
  });
}

// ============== Project File Content ==============
export function useProjectFileContentV2(
  projectId: string,
  filePath: string,
  options?: Omit<UseQueryOptions<{ filename: string; path: string; type: string; content: string; parsed_content?: unknown } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: [...projectKeys.all, 'file', projectId, filePath] as const,
    queryFn: async () => {
      const response = await fetch(`/api/v2/projects/${projectId}/files/${encodeURIComponent(filePath)}`);
      if (!response.ok) throw new Error('获取项目文件内容失败');
      const data = await response.json();
      return data.data || null;
    },
    enabled: Boolean(projectId) && Boolean(filePath),
    staleTime: 60_000,
    ...options,
  });
}

// ============== Workflow Report ==============
export function useWorkflowReportV2(
  projectId: string,
  options?: Omit<UseQueryOptions<{ exists: boolean; content: string | null; path?: string } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: [...projectKeys.all, 'workflow-report', projectId] as const,
    queryFn: async () => {
      const response = await fetch(`/api/v2/projects/${projectId}/workflow-report`);
      if (!response.ok) throw new Error('获取 workflow 报告失败');
      const data = await response.json();
      return data.data || null;
    },
    enabled: Boolean(projectId),
    staleTime: 60_000,
    ...options,
  });
}

// ============== Stage Document ==============
export function useStageDocumentV2(
  projectId: string,
  stageName: string,
  options?: Omit<UseQueryOptions<{ exists: boolean; stage_name: string; content: string | null; parsed_content?: any; path?: string } | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: [...projectKeys.all, 'stage-doc', projectId, stageName] as const,
    queryFn: async () => {
      const response = await fetch(`/api/v2/projects/${projectId}/stage-docs/${stageName}`);
      if (!response.ok) throw new Error('获取阶段文档失败');
      const data = await response.json();
      return data.data || null;
    },
    enabled: Boolean(projectId) && Boolean(stageName),
    staleTime: 60_000,
    ...options,
  });
}
