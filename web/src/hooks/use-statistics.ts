'use client';

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import {
  fetchStatisticsOverview,
  fetchBuildStatistics,
  fetchInvocationStatistics,
  fetchTrendData,
  fetchAgentCategoryDistribution,
  fetchTopAgents,
  fetchRecentActivities,
  fetchSystemHealth,
  CategoryDistribution,
  TopAgent,
  RecentActivity,
  SystemHealth,
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

/**
 * Hook to fetch agent category distribution
 */
export function useAgentCategoryDistribution(options?: Omit<UseQueryOptions<CategoryDistribution[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<CategoryDistribution[]>({
    queryKey: ['statistics', 'agent-categories'],
    queryFn: fetchAgentCategoryDistribution,
    staleTime: 300_000,
    ...options,
  });
}

/**
 * Hook to fetch top agents by invocation count
 */
export function useTopAgents(limit = 10, options?: Omit<UseQueryOptions<TopAgent[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<TopAgent[]>({
    queryKey: ['statistics', 'top-agents', limit],
    queryFn: () => fetchTopAgents(limit),
    staleTime: 300_000,
    ...options,
  });
}

/**
 * Hook to fetch recent activities
 */
export function useRecentActivities(limit = 10, options?: Omit<UseQueryOptions<RecentActivity[], Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<RecentActivity[]>({
    queryKey: ['statistics', 'recent-activities', limit],
    queryFn: () => fetchRecentActivities(limit),
    staleTime: 60_000,
    ...options,
  });
}

/**
 * Hook to fetch system health status
 */
export function useSystemHealth(options?: Omit<UseQueryOptions<SystemHealth, Error>, 'queryKey' | 'queryFn'>) {
  return useQuery<SystemHealth>({
    queryKey: ['statistics', 'system-health'],
    queryFn: fetchSystemHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
    ...options,
  });
}
