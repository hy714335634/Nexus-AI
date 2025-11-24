'use client';

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import {
  fetchStatisticsOverview,
  fetchBuildStatistics,
  fetchInvocationStatistics,
  fetchTrendData,
} from '@/lib/statistics';
import type {
  StatisticsOverviewData,
  BuildStatisticsData,
  InvocationStatisticsData,
  TrendData,
} from '@/types/api';

/**
 * Hook to fetch overall statistics summary
 */
export function useStatisticsOverview(options?: Omit<UseQueryOptions<StatisticsOverviewData, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<StatisticsOverviewData>({
    queryKey: ['statistics', 'overview'],
    queryFn: fetchStatisticsOverview,
    staleTime: 60_000, // 1 minute
    refetchInterval: 300_000, // Refetch every 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch build statistics over a time period
 */
export function useBuildStatistics(days = 30, options?: Omit<UseQueryOptions<BuildStatisticsData[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<BuildStatisticsData[]>({
    queryKey: ['statistics', 'builds', days],
    queryFn: () => fetchBuildStatistics(days),
    staleTime: 300_000, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch agent invocation statistics over a time period
 */
export function useInvocationStatistics(days = 30, options?: Omit<UseQueryOptions<InvocationStatisticsData[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<InvocationStatisticsData[]>({
    queryKey: ['statistics', 'invocations', days],
    queryFn: () => fetchInvocationStatistics(days),
    staleTime: 300_000, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch trend data for a specific metric
 */
export function useTrendData(metric: string, days = 30, options?: Omit<UseQueryOptions<TrendData, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<TrendData>({
    queryKey: ['statistics', 'trends', metric, days],
    queryFn: () => fetchTrendData(metric, days),
    enabled: Boolean(metric),
    staleTime: 300_000, // 5 minutes
    ...options,
  });
}
