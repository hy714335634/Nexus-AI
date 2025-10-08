'use client';

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { fetchProjectSummaries, fetchProjectDetail } from '@/lib/projects';
import type { ProjectDetail, ProjectSummary } from '@/types/projects';

export function useProjectSummaries(options?: UseQueryOptions<ProjectSummary[]>) {
  return useQuery<ProjectSummary[]>({
    queryKey: ['projects', 'summaries'],
    queryFn: fetchProjectSummaries,
    staleTime: 30_000,
    ...options,
  });
}

export function useProjectDetail(projectId: string, options?: UseQueryOptions<ProjectDetail | undefined>) {
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
