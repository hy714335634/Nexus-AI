import type { AgentSummary, BuildStage, ProjectStatus, StageData, StageStatus } from '@/types/api';

export interface ProjectArtifacts {
  requirementMarkdown?: string;
  architectureJson?: Record<string, unknown>;
  toolsJson?: Record<string, unknown>;
  promptText?: string;
  agentCode?: string;
  deploymentNotes?: string;
}

export interface ProjectSummary {
  projectId: string;
  projectName?: string;
  status: ProjectStatus;
  progressPercentage: number;
  currentStage?: BuildStage;
  updatedAt?: string;
  agentCount?: number;
  ownerName?: string;
  tags?: string[];
}

export interface ProjectDetail extends ProjectSummary {
  stages: StageData[];
  agents: AgentSummary[];
  startedAt?: string;
  estimatedCompletion?: string;
  lastError?: string;
  artifacts?: ProjectArtifacts;
  errorContext?: string[];
}

export interface StageLogDescriptor {
  stage: BuildStage;
  displayName: string;
  logPath: string;
}

export interface BuildDashboardStage {
  name: string;
  displayName?: string;
  order: number;
  status: StageStatus;
  startedAt?: string;
  completedAt?: string;
  durationSeconds?: number;
  error?: string;
  inputTokens?: number;
  outputTokens?: number;
  toolCalls?: number;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboardTaskSnapshot {
  taskId: string;
  status: string;
  startedAt?: string;
  finishedAt?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboardMetrics {
  totalDurationSeconds?: number;
  inputTokens?: number;
  outputTokens?: number;
  toolCalls?: number;
  costEstimate?: Record<string, unknown>;
  totalTools?: number;
}

export interface BuildDashboardResource {
  id: string;
  label: string;
  owner?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboardAlert {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboardGraphNode {
  id: string;
  label: string;
  type?: string;
  status?: StageStatus;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboardGraphEdge {
  source: string;
  target: string;
  kind?: string;
  metadata?: Record<string, unknown>;
}

export interface BuildDashboard {
  projectId: string;
  projectName?: string;
  status: ProjectStatus;
  progressPercentage: number;
  requirement?: string;
  stages: BuildDashboardStage[];
  totalStages: number;
  completedStages: number;
  updatedAt?: string;
  latestTask?: BuildDashboardTaskSnapshot;
  metrics?: BuildDashboardMetrics;
  resources: BuildDashboardResource[];
  alerts: BuildDashboardAlert[];
  workflowGraphNodes: BuildDashboardGraphNode[];
  workflowGraphEdges: BuildDashboardGraphEdge[];
  errorInfo?: Record<string, unknown> | null;
}
