import type { AgentSummary, BuildStage, ProjectStatus, StageData } from '@/types/api';

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
