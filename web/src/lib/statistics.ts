import { apiFetch } from '@/lib/api-client';
import type {
  StatisticsOverviewResponse,
  BuildStatisticsResponse,
  InvocationStatisticsResponse,
  TrendDataResponse,
} from '@/types/api';

/**
 * Fetch overall statistics summary
 * @returns Overview statistics including agent counts, build metrics, and today's activity
 */
export async function fetchStatisticsOverview() {
  const response = await apiFetch<StatisticsOverviewResponse>('/api/v1/statistics/overview');

  if (!response.success) {
    throw new Error('Failed to fetch statistics overview');
  }

  return response.data;
}

/**
 * Fetch build statistics over a time period
 * @param days - Number of days to look back (default: 30)
 * @returns Daily build statistics including success/failure counts and durations
 */
export async function fetchBuildStatistics(days = 30) {
  const response = await apiFetch<BuildStatisticsResponse>(
    `/api/v1/statistics/builds?days=${days}`
  );

  if (!response.success) {
    throw new Error('Failed to fetch build statistics');
  }

  return response.data;
}

/**
 * Fetch agent invocation statistics over a time period
 * @param days - Number of days to look back (default: 30)
 * @returns Daily invocation statistics including success rates and durations
 */
export async function fetchInvocationStatistics(days = 30) {
  const response = await apiFetch<InvocationStatisticsResponse>(
    `/api/v1/statistics/invocations?days=${days}`
  );

  if (!response.success) {
    throw new Error('Failed to fetch invocation statistics');
  }

  return response.data;
}

/**
 * Fetch trend data for a specific metric
 * @param metric - Metric name (e.g., 'build_count', 'success_rate', 'avg_duration')
 * @param days - Number of days to look back (default: 30)
 * @returns Trend data points for the specified metric
 */
export async function fetchTrendData(metric: string, days = 30) {
  const response = await apiFetch<TrendDataResponse>(
    `/api/v1/statistics/trends/${encodeURIComponent(metric)}?days=${days}`
  );

  if (!response.success) {
    throw new Error(`Failed to fetch trend data for metric: ${metric}`);
  }

  return response.data;
}
