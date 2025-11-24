import { apiFetch } from '@/lib/api-client';
import type {
  AgentListResponse,
  AgentSummary,
  AgentDetailsResponse,
  StageTimelineResponse,
  StageTimelineResponseData,
  BuildDashboardResponse,
  BuildDashboardStageRecord,
  ProjectListResponse,
  CreateProjectRequest,
  CreateProjectResponse,
  ProjectControlRequest,
  ProjectControlResponse,
  BuildStage,
} from '@/types/api';
import type {
  BuildDashboard,
  BuildDashboardAlert,
  BuildDashboardGraphEdge,
  BuildDashboardGraphNode,
  BuildDashboardMetrics,
  BuildDashboardResource,
  BuildDashboardStage,
  BuildDashboardTaskSnapshot,
  ProjectDetail,
  ProjectSummary,
} from '@/types/projects';

const EMPTY_TIMELINE: StageTimelineResponseData = {
  project_id: '',
  total_stages: 0,
  completed_stages: 0,
  stages: [],
  overall_progress: 0,
};

function normalizeStage(stage?: string | null): BuildStage | undefined {
  if (!stage) {
    return undefined;
  }

  // Map legacy/alternative stage names to correct BuildStage enum values
  const aliases: Record<string, BuildStage> = {
    requirements_analyzer: 'requirements_analysis',
    system_architect: 'system_architecture',
    agent_designer: 'agent_design',
    prompt_engineer: 'agent_developer_manager',
    tools_developer: 'agent_developer_manager',
    agent_code_developer: 'agent_developer_manager',
  };

  return aliases[stage] ?? (stage as BuildStage);
}

export async function fetchProjectSummaries(): Promise<ProjectSummary[]> {
  const response = await apiFetch<ProjectListResponse>('/api/v1/projects?limit=100').catch(() => undefined);

  if (!response?.success) {
    return [];
  }

  const projects = response.data.items.map((project) => {
    const updatedAt = project.updated_at ?? project.created_at ?? undefined;
    return {
      projectId: project.project_id,
      projectName: project.project_name ?? project.project_id,
      status: project.status,
      progressPercentage: project.progress_percentage ?? 0,
      currentStage: normalizeStage(project.current_stage ?? undefined),
      updatedAt,
      agentCount: project.agent_count ?? 0,
      ownerName: project.user_name ?? undefined,
      tags: project.tags ?? undefined,
    } satisfies ProjectSummary;
  });

  return projects.sort((a, b) => {
    const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
    const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
    return timeB - timeA;
  });
}

async function fetchProjectStages(projectId: string): Promise<StageTimelineResponseData | undefined> {
  const response = await apiFetch<StageTimelineResponse>(`/api/v1/projects/${projectId}/stages`).catch(() => undefined);
  if (!response?.success) {
    return undefined;
  }
  return response.data;
}

async function fetchAgentsForProject(projectId: string): Promise<AgentSummary[]> {
  const response = await apiFetch<AgentListResponse>('/api/v1/agents?limit=100').catch(() => undefined);
  if (!response?.success) {
    return [];
  }
  return response.data.agents.filter((agent) => agent.project_id === projectId);
}

async function fetchPrimaryAgent(projectId: string, agentId?: string) {
  if (!agentId) {
    return undefined;
  }
  const response = await apiFetch<AgentDetailsResponse>(`/api/v1/agents/${agentId}`).catch(() => undefined);
  if (!response?.success || response.data.project_id !== projectId) {
    return undefined;
  }
  return response.data;
}

export async function fetchProjectDetail(projectId: string): Promise<ProjectDetail> {
  const [summaries, stagePayload, agents, dashboard] = await Promise.all([
    fetchProjectSummaries().catch(() => []),
    fetchProjectStages(projectId).catch(() => undefined),
    fetchAgentsForProject(projectId).catch(() => []),
    fetchBuildDashboard(projectId).catch(() => undefined),
  ]);

  if (!dashboard) {
    throw new Error('项目不存在或尚未产生构建数据');
  }

  const summary = summaries.find((project) => project.projectId === projectId);

  const baseSummary: ProjectSummary = summary ?? {
    projectId,
    projectName: dashboard.projectName ?? projectId,
    status: dashboard.status,
    progressPercentage: dashboard.progressPercentage ?? 0,
    currentStage: undefined,
    updatedAt: dashboard.updatedAt ?? new Date().toISOString(),
    agentCount: agents.length,
    ownerName: undefined,
    tags: undefined,
  };

  const timeline = stagePayload ?? { ...EMPTY_TIMELINE, project_id: projectId };
  const stageList = (timeline.stages ?? []).length
    ? timeline.stages
    : dashboard.stages.map((stage, index) => ({
        stage: stage.name as StageTimelineResponseData['stages'][number]['stage'],
        stage_number: index + 1,
        stage_name: stage.name,
        stage_name_cn: stage.displayName ?? stage.name,
        status: stage.status,
        started_at: stage.startedAt ?? null,
        completed_at: stage.completedAt ?? null,
        duration_seconds: stage.durationSeconds ?? undefined,
        agent_name: undefined,
        output_data: stage.metadata ?? undefined,
        error_message: stage.error ?? undefined,
        logs: undefined,
      }));

  const failedStage = stageList.find((stage) => stage.status === 'failed');
  const runningStage = stageList.find((stage) => stage.status === 'running');
  const pendingStage = stageList.find((stage) => stage.status === 'pending');

  const progress = dashboard.progressPercentage ?? timeline.overall_progress ?? baseSummary.progressPercentage;

  let latestTimestamp: string | undefined = dashboard.updatedAt ?? baseSummary.updatedAt;
  for (const stage of stageList) {
    const candidate = stage.completed_at ?? stage.started_at;
    if (candidate && (!latestTimestamp || Date.parse(candidate) > Date.parse(latestTimestamp))) {
      latestTimestamp = candidate;
    }
  }

  const startedStage = stageList.find((stage) => stage.started_at);

  return {
    ...baseSummary,
    progressPercentage: progress,
    currentStage: baseSummary.currentStage ?? (runningStage?.stage ?? pendingStage?.stage),
    updatedAt: latestTimestamp ?? baseSummary.updatedAt,
    stages: stageList,
    agents,
    agentCount: agents.length,
    startedAt: startedStage?.started_at ?? baseSummary.updatedAt,
    estimatedCompletion: runningStage?.completed_at ?? pendingStage?.started_at ?? undefined,
    lastError: failedStage?.error_message ?? dashboard.errorInfo?.error?.toString() ?? undefined,
    artifacts: undefined,
    errorContext:
      failedStage?.error_message
        ? [failedStage.error_message]
        : dashboard.errorInfo
        ? Object.values(dashboard.errorInfo).map((value) => String(value))
        : undefined,
  };
}

function asStageStatus(value: unknown): BuildDashboardStage['status'] | undefined {
  if (value === 'pending' || value === 'running' || value === 'completed' || value === 'failed') {
    return value;
  }
  return undefined;
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function toStringValue(value: unknown): string | undefined {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  }
  return undefined;
}

function toRecord(value: unknown): Record<string, unknown> | undefined {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return undefined;
}

function mapStage(record: BuildDashboardStageRecord): BuildDashboardStage {
  return {
    name: record.name,
    displayName: toStringValue(record.display_name),
    order: record.order ?? 0,
    status: asStageStatus(record.status) ?? 'pending',
    startedAt: toStringValue(record.started_at),
    completedAt: toStringValue(record.completed_at),
    durationSeconds: toNumber(record.duration_seconds),
    error: toStringValue(record.error),
    inputTokens: toNumber(record.input_tokens),
    outputTokens: toNumber(record.output_tokens),
    toolCalls: toNumber(record.tool_calls),
    metadata: toRecord(record.metadata) ?? {},
  };
}

function mapTaskSnapshot(task?: BuildDashboardResponse['data']['latest_task']): BuildDashboardTaskSnapshot | undefined {
  if (!task) {
    return undefined;
  }

  return {
    taskId: task.task_id,
    status: task.status,
    startedAt: toStringValue(task.started_at),
    finishedAt: toStringValue(task.finished_at),
    error: toStringValue(task.error),
    metadata: toRecord(task.metadata),
  };
}

function mapMetrics(metrics?: BuildDashboardResponse['data']['metrics']): BuildDashboardMetrics | undefined {
  if (!metrics) {
    return undefined;
  }

  const output: BuildDashboardMetrics = {};
  const duration = toNumber(metrics.total_duration_seconds);
  if (duration !== undefined) {
    output.totalDurationSeconds = duration;
  }
  const inputTokens = toNumber(metrics.input_tokens);
  if (inputTokens !== undefined) {
    output.inputTokens = inputTokens;
  }
  const outputTokens = toNumber(metrics.output_tokens);
  if (outputTokens !== undefined) {
    output.outputTokens = outputTokens;
  }
  const toolCalls = toNumber(metrics.tool_calls);
  if (toolCalls !== undefined) {
    output.toolCalls = toolCalls;
  }
  const totalTools = toNumber(metrics.total_tools);
  if (totalTools !== undefined) {
    output.totalTools = totalTools;
  }
  const costEstimate = toRecord(metrics.cost_estimate);
  if (costEstimate) {
    output.costEstimate = costEstimate;
  }
  return Object.keys(output).length ? output : undefined;
}

function mapResource(resource: Record<string, unknown>, index: number): BuildDashboardResource {
  const id = toStringValue(resource.id) ?? `resource-${index}`;
  const label = toStringValue(resource.label) ?? id;
  const owner = toStringValue(resource.owner);
  const status = toStringValue(resource.status);

  return {
    id,
    label,
    owner,
    status,
    metadata: resource,
  };
}

function mapAlert(alert: Record<string, unknown>, index: number): BuildDashboardAlert | null {
  const id = toStringValue(alert.id) ?? `alert-${index}`;
  const level = toStringValue(alert.level);
  const message = toStringValue(alert.message);
  const createdAt = toStringValue(alert.created_at);

  if (!message || !createdAt) {
    return null;
  }

  const alertLevel = level === 'info' || level === 'warning' || level === 'error' ? level : 'info';

  return {
    id,
    level: alertLevel,
    message,
    createdAt,
    metadata: alert,
  };
}

function mapGraphNode(node: Record<string, unknown>, index: number): BuildDashboardGraphNode {
  const id = toStringValue(node.id) ?? `node-${index}`;
  const label = toStringValue(node.label) ?? id;
  const status = asStageStatus(node.status);

  return {
    id,
    label,
    type: toStringValue(node.type),
    status,
    metadata: node,
  };
}

function mapGraphEdge(edge: Record<string, unknown>, index: number): BuildDashboardGraphEdge {
  const source = toStringValue(edge.source) ?? `node-${index}-source`;
  const target = toStringValue(edge.target) ?? `node-${index}-target`;

  return {
    source,
    target,
    kind: toStringValue(edge.kind),
    metadata: edge,
  };
}

function mapBuildDashboard(data: BuildDashboardResponse['data']): BuildDashboard {
  const stages = Array.isArray(data.stages) ? data.stages.map(mapStage) : [];
  const resourcesRaw = Array.isArray(data.resources) ? data.resources : [];
  const alertsRaw = Array.isArray(data.alerts) ? data.alerts : [];
  const nodesRaw = Array.isArray(data.workflow_graph_nodes) ? data.workflow_graph_nodes : [];
  const edgesRaw = Array.isArray(data.workflow_graph_edges) ? data.workflow_graph_edges : [];

  const resources = resourcesRaw.map((resource, index) => mapResource(resource, index));
  const alerts = alertsRaw
    .map((alert, index) => mapAlert(alert, index))
    .filter((alert): alert is BuildDashboardAlert => Boolean(alert));
  const workflowGraphNodes = nodesRaw.map((node, index) => mapGraphNode(node, index));
  const workflowGraphEdges = edgesRaw.map((edge, index) => mapGraphEdge(edge, index));

  return {
    projectId: data.project_id,
    projectName: toStringValue(data.project_name),
    status: data.status,
    progressPercentage: data.progress_percentage ?? 0,
    requirement: toStringValue(data.requirement),
    stages,
    totalStages: data.total_stages ?? stages.length,
    completedStages: data.completed_stages ?? 0,
    updatedAt: toStringValue(data.updated_at),
    latestTask: mapTaskSnapshot(data.latest_task ?? undefined),
    metrics: mapMetrics(data.metrics ?? undefined),
    resources,
    alerts,
    workflowGraphNodes,
    workflowGraphEdges,
    errorInfo: toRecord(data.error_info) ?? null,
  };
}

export async function fetchBuildDashboard(projectId: string): Promise<BuildDashboard | undefined> {
  const response = await apiFetch<BuildDashboardResponse>(`/api/v1/projects/${projectId}/build`).catch(() => undefined);
  if (!response?.success) {
    return undefined;
  }

  return mapBuildDashboard(response.data);
}

/**
 * Create a new project
 * @param request - Project creation parameters
 * @returns Created project data
 */
export async function createProject(request: CreateProjectRequest) {
  const response = await apiFetch<CreateProjectResponse>(
    '/api/v1/projects',
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to create project');
  }

  return response.data;
}

/**
 * Control project execution (pause, resume, stop, restart)
 * @param projectId - Project ID
 * @param action - Control action to perform
 * @returns Control operation result
 */
export async function controlProject(projectId: string, action: ProjectControlRequest['action']) {
  const response = await apiFetch<ProjectControlResponse>(
    `/api/v1/projects/${projectId}/control`,
    {
      method: 'PUT',
      body: JSON.stringify({ action }),
    },
  );

  if (!response.success) {
    throw new Error(`Failed to ${action} project`);
  }

  return response.data;
}

/**
 * Delete a project and all associated resources
 * @param projectId - Project ID to delete
 */
export async function deleteProject(projectId: string) {
  const response = await apiFetch<{ success: boolean; message?: string }>(
    `/api/v1/projects/${projectId}`,
    {
      method: 'DELETE',
    },
  );

  if (!response.success) {
    throw new Error('Failed to delete project');
  }

  return response;
}

/**
 * Get detailed information for a specific project stage
 * @param projectId - Project ID
 * @param stageName - Stage name
 * @returns Stage details including logs and output data
 */
export async function fetchProjectStageDetail(projectId: string, stageName: string) {
  const response = await apiFetch<{
    success: boolean;
    data: StageTimelineResponseData['stages'][number];
  }>(`/api/v1/projects/${projectId}/stages/${stageName}`);

  if (!response.success) {
    throw new Error(`Failed to fetch stage ${stageName}`);
  }

  return response.data;
}
