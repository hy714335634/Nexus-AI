import { apiFetch } from './api-client';
import type {
  ProjectListResponse,
  ProjectStatusResponse,
  BuildDashboardResponse,
  CreateProjectRequest,
  CreateProjectResponse,
  ProjectControlAction,
  ProjectControlResponse,
  StageTimelineResponse,
  ProjectListItemRecord,
  ProjectStatusData,
  BuildDashboardDataRecord,
  CreateProjectResponseData,
  ProjectControlResponseData,
  StageData,
} from '@/types/api';
import type { 
  BuildDashboard,
  BuildDashboardGraphNode, 
  BuildDashboardGraphEdge, 
  BuildDashboardResource, 
  BuildDashboardAlert, 
  BuildDashboardStage,
  BuildDashboardTaskSnapshot,
  BuildDashboardMetrics,
} from '@/types/projects';
import type { StageStatus } from '@/types/api';

// Re-export BuildDashboard type
export type { BuildDashboard };

// Simplified types for frontend use
export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  progress: number;
  currentStage?: string;
  createdAt?: string;
  updatedAt?: string;
  agentCount?: number;
  tags?: string[];
}

export interface ProjectDetail extends ProjectSummary {
  requirement?: string;
  userId?: string;
  userName?: string;
  startedAt?: string;
  estimatedCompletion?: string;
  currentAgent?: string;
  currentWork?: string;
  errorInfo?: Record<string, unknown>;
}

function mapProjectListItem(item: ProjectListItemRecord): ProjectSummary {
  return {
    id: item.project_id,
    name: item.project_name || item.project_id,
    status: item.status,
    progress: item.progress_percentage,
    currentStage: item.current_stage || undefined,
    createdAt: item.created_at || undefined,
    updatedAt: item.updated_at || undefined,
    agentCount: item.agent_count || 0,
    tags: item.tags || [],
  };
}

function mapProjectStatus(data: ProjectStatusData): ProjectDetail {
  return {
    id: data.project_id,
    name: data.project_name || data.project_id,
    status: data.status,
    progress: data.progress_percentage,
    currentStage: data.current_stage || undefined,
    startedAt: data.started_at || undefined,
    estimatedCompletion: data.estimated_completion || undefined,
    currentAgent: data.current_agent || undefined,
    currentWork: data.current_work || undefined,
    errorInfo: data.error_info || undefined,
  };
}

function mapBuildDashboard(data: BuildDashboardDataRecord): BuildDashboard {
  return {
    projectId: data.project_id,
    projectName: data.project_name || undefined,
    status: data.status,
    progressPercentage: data.progress_percentage,
    requirement: data.requirement || undefined,
    stages: data.stages.map((stage): BuildDashboardStage => ({
      name: stage.name,
      displayName: stage.display_name || undefined,
      order: stage.order,
      status: stage.status as StageStatus,
      startedAt: stage.started_at || undefined,
      completedAt: stage.completed_at || undefined,
      durationSeconds: stage.duration_seconds || undefined,
      error: stage.error || undefined,
      inputTokens: stage.input_tokens || undefined,
      outputTokens: stage.output_tokens || undefined,
      toolCalls: stage.tool_calls || undefined,
    })),
    totalStages: data.total_stages,
    completedStages: data.completed_stages,
    updatedAt: data.updated_at || undefined,
    latestTask: data.latest_task ? {
      taskId: data.latest_task.task_id,
      status: data.latest_task.status,
      startedAt: data.latest_task.started_at || undefined,
      finishedAt: data.latest_task.finished_at || undefined,
      error: data.latest_task.error || undefined,
    } : undefined,
    metrics: data.metrics ? {
      totalDurationSeconds: data.metrics.total_duration_seconds || undefined,
      inputTokens: data.metrics.input_tokens || undefined,
      outputTokens: data.metrics.output_tokens || undefined,
      toolCalls: data.metrics.tool_calls || undefined,
      totalTools: data.metrics.total_tools || undefined,
    } : undefined,
    errorInfo: data.error_info || undefined,
    resources: (data.resources || []).map((r): BuildDashboardResource => ({
      id: String(r.id || ''),
      label: String(r.label || ''),
      owner: r.owner ? String(r.owner) : undefined,
      status: r.status ? String(r.status) : undefined,
    })),
    alerts: (data.alerts || []).map((a): BuildDashboardAlert => ({
      id: String(a.id || ''),
      level: (a.level as 'info' | 'warning' | 'error') || 'info',
      message: String(a.message || ''),
      createdAt: a.timestamp ? String(a.timestamp) : new Date().toISOString(),
    })),
    workflowGraphNodes: (data.workflow_graph_nodes || []).map((n): BuildDashboardGraphNode => ({
      id: String(n.id || ''),
      label: String(n.label || ''),
      type: n.type ? String(n.type) : undefined,
      status: n.status as StageStatus | undefined,
    })),
    workflowGraphEdges: (data.workflow_graph_edges || []).map((e): BuildDashboardGraphEdge => ({
      source: String(e.source || ''),
      target: String(e.target || ''),
      kind: e.kind ? String(e.kind) : undefined,
    })),
  };
}

export async function fetchProjectSummaries(limit = 100): Promise<ProjectSummary[]> {
  const response = await apiFetch<ProjectListResponse>(`/api/v1/projects?limit=${limit}`);
  return response.data.items.map(mapProjectListItem);
}

export async function fetchProjectDetail(projectId: string): Promise<ProjectDetail | undefined> {
  try {
    const response = await apiFetch<ProjectStatusResponse>(`/api/v1/projects/${projectId}`);
    return mapProjectStatus(response.data);
  } catch (error) {
    console.error('Failed to fetch project detail:', error);
    return undefined;
  }
}

export async function fetchBuildDashboard(projectId: string): Promise<BuildDashboard | null> {
  try {
    const response = await apiFetch<BuildDashboardResponse>(`/api/v1/projects/${projectId}/build`);
    return mapBuildDashboard(response.data);
  } catch (error) {
    console.error('Failed to fetch build dashboard:', error);
    return null;
  }
}

export async function fetchProjectStageDetail(projectId: string, stageName: string): Promise<StageData> {
  const response = await apiFetch<StageTimelineResponse>(`/api/v1/projects/${projectId}/stages`);
  const stage = response.data.stages.find((s) => s.stage === stageName);
  if (!stage) {
    throw new Error(`Stage ${stageName} not found`);
  }
  return stage;
}

export async function createProject(request: CreateProjectRequest): Promise<CreateProjectResponseData> {
  const response = await apiFetch<CreateProjectResponse>('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(request),
  });
  return response.data;
}

export async function controlProject(
  projectId: string,
  action: ProjectControlAction
): Promise<ProjectControlResponseData> {
  const response = await apiFetch<ProjectControlResponse>(`/api/v1/projects/${projectId}/control`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
  return response.data;
}

export async function deleteProject(projectId: string): Promise<{ success: boolean; message?: string }> {
  return apiFetch<{ success: boolean; message?: string }>(`/api/v1/projects/${projectId}`, {
    method: 'DELETE',
  });
}
