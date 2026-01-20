'use client';

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import * as apiV2 from '@/lib/api-v2';
import type {
  StatisticsOverview,
  BuildStatistics,
  InvocationStatistics,
} from '@/types/api-v2';

// ============== Query Keys ==============
export const statisticsKeys = {
  all: ['v2', 'statistics'] as const,
  overview: () => [...statisticsKeys.all, 'overview'] as const,
  builds: (days: number) => [...statisticsKeys.all, 'builds', days] as const,
  invocations: (days: number) => [...statisticsKeys.all, 'invocations', days] as const,
};

// ============== Statistics Overview ==============
export function useStatisticsOverviewV2(
  options?: Omit<UseQueryOptions<StatisticsOverview | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<StatisticsOverview | null>({
    queryKey: statisticsKeys.overview(),
    queryFn: async () => {
      const response = await apiV2.getStatisticsOverview();
      return response.data || null;
    },
    staleTime: 60_000, // 1 minute
    refetchInterval: 300_000, // Refetch every 5 minutes
    ...options,
  });
}

// ============== Build Statistics ==============
export function useBuildStatisticsV2(
  days = 30,
  options?: Omit<UseQueryOptions<BuildStatistics[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<BuildStatistics[]>({
    queryKey: statisticsKeys.builds(days),
    queryFn: async () => {
      const response = await apiV2.getBuildStatistics(days);
      return response.data || [];
    },
    staleTime: 300_000, // 5 minutes
    ...options,
  });
}

// ============== Invocation Statistics ==============
export function useInvocationStatisticsV2(
  days = 30,
  options?: Omit<UseQueryOptions<InvocationStatistics[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<InvocationStatistics[]>({
    queryKey: statisticsKeys.invocations(days),
    queryFn: async () => {
      const response = await apiV2.getInvocationStatistics(days);
      return response.data || [];
    },
    staleTime: 300_000, // 5 minutes
    ...options,
  });
}
