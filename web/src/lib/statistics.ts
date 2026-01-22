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

// 额外的类型定义
export interface CategoryDistribution {
  category: string;
  count: number;
}

export interface TopAgent {
  agent_id: string;
  agent_name: string;
  category: string;
  total_invocations: number;
  status: string;
}

export interface RecentActivity {
  type: 'project' | 'agent';
  id: string;
  name: string;
  status: string;
  timestamp: string;
  action: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'warning' | 'critical';
  database: string;
  success_rate: number;
  active_agents: number;
  building_projects: number;
  last_check: string;
}

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

export async function fetchAgentCategoryDistribution(): Promise<CategoryDistribution[]> {
  const response = await apiFetch<{ success: boolean; data: CategoryDistribution[] }>('/api/v2/statistics/agent-categories');
  return response.data;
}

export async function fetchTopAgents(limit = 10): Promise<TopAgent[]> {
  const response = await apiFetch<{ success: boolean; data: TopAgent[] }>(`/api/v2/statistics/top-agents?limit=${limit}`);
  return response.data;
}

export async function fetchRecentActivities(limit = 10): Promise<RecentActivity[]> {
  const response = await apiFetch<{ success: boolean; data: RecentActivity[] }>(`/api/v2/statistics/recent-activities?limit=${limit}`);
  return response.data;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const response = await apiFetch<{ success: boolean; data: SystemHealth }>('/api/v2/statistics/system-health');
  return response.data;
}
