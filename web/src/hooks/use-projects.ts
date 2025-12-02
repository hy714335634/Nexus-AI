'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import {
  fetchProjectSummaries,
  fetchProjectDetail,
  fetchBuildDashboard,
  createProject,
  controlProject,
  deleteProject,
  fetchProjectStageDetail,
} from '@/lib/projects';
import type { ProjectDetail, ProjectSummary, BuildDashboard } from '@/types/projects';
import type {
  CreateProjectRequest,
  CreateProjectResponseData,
  ProjectControlAction,
  ProjectControlResponseData,
  StageData,
} from '@/types/api';

export function useProjectSummaries(options?: Omit<UseQueryOptions<ProjectSummary[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<ProjectSummary[]>({
    queryKey: ['projects', 'summaries'],
    queryFn: fetchProjectSummaries,
    staleTime: 30_000,
    ...options,
  });
}

export function useProjectDetail(projectId: string, options?: Omit<UseQueryOptions<ProjectDetail | undefined, Error>, 'queryKey' | 'queryFn'>) {
  const pollAttemptRef = useRef(0);
  const lastFingerprintRef = useRef<string | null>(null);

  const query = useQuery<ProjectDetail | undefined>({
    queryKey: ['projects', 'detail', projectId],
    queryFn: () => fetchProjectDetail(projectId),
    enabled: Boolean(projectId),
    staleTime: 5_000,
    refetchOnReconnect: true,
    refetchOnWindowFocus: false,
    retry: 5,
    retryDelay: (attempt) => Math.min(60_000, 1_000 * 2 ** attempt),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) {
        return false;
      }

      const shouldPoll = data.status === 'building' || data.status === 'pending';
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
    if (!data) {
      return;
    }

    const fingerprint = `${data.status}-${data.currentStage ?? 'none'}-${Math.round(data.progressPercentage)}`;
    if (fingerprint !== lastFingerprintRef.current) {
      lastFingerprintRef.current = fingerprint;
      pollAttemptRef.current = 0;
    }
  }, [query.data]);

  return query;
}

export function useBuildDashboard(
  projectId: string,
  options?: Omit<UseQueryOptions<BuildDashboard | null, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<BuildDashboard | null>({
    queryKey: ['projects', 'build-dashboard', projectId],
    queryFn: () => fetchBuildDashboard(projectId),
    enabled: Boolean(projectId),
    staleTime: 5_000,
    refetchOnReconnect: true,
    refetchOnWindowFocus: false,
    // 不重试，因为 fetchBuildDashboard 返回 null 而不是抛出错误
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) {
        return false;
      }

      const isBuilding = data.status === 'building' || data.status === 'pending';
      const hasRunningStage = data.stages.some((stage) => stage.status === 'running');
      const hasRecentCompletion =
        data.latestTask?.status === 'completed' && (data.progressPercentage ?? 0) >= 100;

      if (!isBuilding && !hasRunningStage) {
        return false;
      }

      if (hasRecentCompletion) {
        return false;
      }

      // Increased from 5s to 10s to reduce server load
      return 10_000;
    },
    ...options,
  });
}

export function useProjectStageDetail(
  projectId: string,
  stageName: string,
  options?: Omit<UseQueryOptions<StageData, Error>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<StageData>({
    queryKey: ['projects', 'stage-detail', projectId, stageName],
    queryFn: () => fetchProjectStageDetail(projectId, stageName),
    enabled: Boolean(projectId && stageName),
    staleTime: 10_000,
    ...options,
  });
}

export function useCreateProject(
  options?: UseMutationOptions<CreateProjectResponseData, Error, CreateProjectRequest>,
) {
  const queryClient = useQueryClient();

  return useMutation<CreateProjectResponseData, Error, CreateProjectRequest>({
    mutationFn: createProject,
    onSuccess: () => {
      // Invalidate project lists to refetch with new project
      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });
    },
    ...options,
  });
}

export function useControlProject(
  options?: UseMutationOptions<
    ProjectControlResponseData,
    Error,
    { projectId: string; action: ProjectControlAction }
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    ProjectControlResponseData,
    Error,
    { projectId: string; action: ProjectControlAction }
  >({
    mutationFn: ({ projectId, action }) => controlProject(projectId, action),
    onSuccess: (data, variables) => {
      // Invalidate all project-related queries for this project
      queryClient.invalidateQueries({ queryKey: ['projects', 'detail', variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects', 'build-dashboard', variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });
    },
    ...options,
  });
}

export function useDeleteProject(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>,
) {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; message?: string }, Error, string>({
    mutationFn: deleteProject,
    onSuccess: (data, projectId) => {
      // Remove all cached data for this project
      queryClient.removeQueries({ queryKey: ['projects', 'detail', projectId] });
      queryClient.removeQueries({ queryKey: ['projects', 'build-dashboard', projectId] });
      queryClient.removeQueries({ queryKey: ['projects', 'stage-detail', projectId] });
      // Invalidate project lists
      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });
    },
    ...options,
  });
}
