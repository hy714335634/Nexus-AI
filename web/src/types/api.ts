export type ProjectStatus = 'pending' | 'building' | 'completed' | 'failed' | 'paused';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';
export type AgentStatus = 'running' | 'building' | 'offline';

export type BuildStage =
  | 'orchestrator'
  | 'requirements_analyzer'
  | 'requirements_analysis'
  | 'system_architect'
  | 'system_architecture'
  | 'agent_designer'
  | 'agent_design'
  | 'prompt_engineer'
  | 'tools_developer'
  | 'agent_code_developer'
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
  agent_name?: string;
  priority?: number;
  tags?: string[];
}

export interface CreateAgentResponseData {
  task_id: string;
  session_id: string;
  project_id: string;
  agent_name?: string;
  status: string;
  message: string;
}

export type CreateAgentResponse = ApiResponse<CreateAgentResponseData>;

export interface AgentDialogSession {
  session_id: string;
  display_name?: string;
  created_at: string;
  last_active_at?: string;
}

export interface AgentDialogSessionsResponse {
  sessions: AgentDialogSession[];
}

export interface AgentDialogMessage {
  message_id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface AgentDialogMessagesResponse {
  messages: AgentDialogMessage[];
}

export interface AgentContextResponseData {
  agent_id: string;
  display_name?: string;
  system_prompt_path?: string;
  code_path?: string;
  tools_path?: string;
  description?: string;
  tags?: string[];
}

export type AgentContextResponse = ApiResponse<AgentContextResponseData>;

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

export interface ProjectListItemRecord {
  project_id: string;
  project_name?: string | null;
  status: ProjectStatus;
  progress_percentage: number;
  current_stage?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  user_id?: string | null;
  user_name?: string | null;
  agent_count?: number | null;
  tags?: string[] | null;
}

export interface ProjectListResponseData {
  projects: ProjectListItemRecord[];
  pagination: PaginationMeta;
}

export type ProjectListResponse = ApiResponse<ProjectListResponseData>;

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

export interface BuildDashboardStageRecord {
  name: string;
  display_name?: string | null;
  order: number;
  status: StageStatus;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  error?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  tool_calls?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface BuildDashboardTaskRecord {
  task_id: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface BuildDashboardMetricsRecord {
  total_duration_seconds?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  tool_calls?: number | null;
  cost_estimate?: Record<string, unknown> | null;
  total_tools?: number | null;
}

export interface BuildDashboardDataRecord {
  project_id: string;
  project_name?: string | null;
  status: ProjectStatus;
  progress_percentage: number;
  requirement?: string | null;
  stages: BuildDashboardStageRecord[];
  total_stages: number;
  completed_stages: number;
  updated_at?: string | null;
  latest_task?: BuildDashboardTaskRecord | null;
  metrics?: BuildDashboardMetricsRecord | null;
  resources?: Array<Record<string, unknown>>;
  alerts?: Array<Record<string, unknown>>;
  workflow_graph_nodes?: Array<Record<string, unknown>>;
  workflow_graph_edges?: Array<Record<string, unknown>>;
  error_info?: Record<string, unknown> | null;
}

export type BuildDashboardResponse = ApiResponse<BuildDashboardDataRecord>;
