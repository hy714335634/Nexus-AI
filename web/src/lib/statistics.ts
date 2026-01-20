import { apiFetch } from './api-client';
import type {
  StatisticsOverviewResponse,
  BuildStatisticsResponse,
  InvocationStatisticsResponse,
  TrendDataResponse,
  StatisticsOverviewData,
  BuildStatisticsData,
  InvocationStatisticsData,
  TrendData,
} from '@/types/api';

export async function fetchStatisticsOverview(): Promise<StatisticsOverviewData> {
  const response = await apiFetch<StatisticsOverviewResponse>('/api/v2/statistics/overview');
  return response.data;
}

export async function fetchBuildStatistics(days = 30): Promise<BuildStatisticsData[]> {
  const response = await apiFetch<BuildStatisticsResponse>(`/api/v2/statistics/builds?days=${days}`);
  return response.data;
}

export async function fetchInvocationStatistics(days = 30): Promise<InvocationStatisticsData[]> {
  const response = await apiFetch<InvocationStatisticsResponse>(`/api/v2/statistics/invocations?days=${days}`);
  return response.data;
}

export async function fetchTrendData(metric: string, days = 30): Promise<TrendData> {
  const response = await apiFetch<TrendDataResponse>(`/api/v2/statistics/trends/${metric}?days=${days}`);
  return response.data;
}
