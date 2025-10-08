export type ProjectStatus = 'pending' | 'building' | 'completed' | 'failed' | 'paused';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';
export type AgentStatus = 'running' | 'building' | 'offline';

export type BuildStage =
  | 'orchestrator'
  | 'requirements_analysis'
  | 'system_architecture'
  | 'agent_design'
  | 'agent_developer_manager'
  | 'agent_deployer';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  timestamp: string;
  request_id: string;
}

export interface CreateAgentRequest {
  requirement: string;
  user_id: string;
  user_name?: string;
  priority?: number;
  tags?: string[];
}

export interface CreateAgentResponseData {
  task_id: string;
  session_id: string;
  project_id: string;
  status: string;
  message: string;
}

export type CreateAgentResponse = ApiResponse<CreateAgentResponseData>;

export interface TaskStatusData {
  task_id: string;
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  date_done?: string | null;
}

export type TaskStatusResponse = ApiResponse<TaskStatusData>;

export interface StageData {
  stage: BuildStage;
  stage_number: number;
  stage_name: string;
  stage_name_cn: string;
  status: StageStatus;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  agent_name?: string | null;
  output_data?: Record<string, unknown> | null;
  error_message?: string | null;
  logs?: string[] | null;
}

export interface StageTimelineResponseData {
  project_id: string;
  total_stages: number;
  completed_stages: number;
  stages: StageData[];
  overall_progress: number;
}

export type StageTimelineResponse = ApiResponse<StageTimelineResponseData>;

export interface AgentSummary {
  agent_id: string;
  project_id: string;
  agent_name: string;
  category?: string | null;
  status: AgentStatus;
  version?: string | null;
  created_at: string;
  call_count: number;
  success_rate: number;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AgentListData {
  agents: AgentSummary[];
  pagination: PaginationMeta;
}

export type AgentListResponse = ApiResponse<AgentListData>;

export interface AgentDetails {
  agent_id: string;
  project_id: string;
  agent_name: string;
  description?: string | null;
  category?: string | null;
  version?: string | null;
  status: AgentStatus;
  script_path?: string | null;
  prompt_path?: string | null;
  tools_count: number;
  dependencies: string[];
  supported_models: string[];
  tags: string[];
  call_count: number;
  success_rate: number;
  last_called_at?: string | null;
  created_at: string;
}

export type AgentDetailsResponse = ApiResponse<AgentDetails>;

export interface ProjectStatusData {
  project_id: string;
  project_name?: string | null;
  status: ProjectStatus;
  current_stage?: BuildStage | null;
  stage_number?: number | null;
  stage_name?: string | null;
  progress_percentage: number;
  started_at?: string | null;
  estimated_completion?: string | null;
  current_agent?: string | null;
  current_work?: string | null;
  error_info?: Record<string, unknown> | null;
}

export type ProjectStatusResponse = ApiResponse<ProjectStatusData>;

export interface ArtifactRecord {
  artifact_id: string;
  agent_id?: string | null;
  project_id: string;
  stage: string;
  type?: string | null;
  file_path?: string | null;
  doc_path?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ArtifactListResponse extends ApiResponse<ArtifactRecord[]> {}

export interface DeploymentTriggerRequest {
  region: string;
  project_id: string;
  agent_id?: string;
  parameters?: Record<string, string | number | boolean>;
}

export interface DeploymentStatus {
  build_id: string;
  status: 'QUEUED' | 'BUILD' | 'COMPLETED' | 'FAILED';
  current_phase?: string;
  started_at?: string;
  completed_at?: string;
  logs_url?: string;
  error?: string;
}

export interface DeploymentStatusResponse extends ApiResponse<DeploymentStatus> {}
