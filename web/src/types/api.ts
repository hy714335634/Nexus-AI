export type ProjectStatus = 'pending' | 'building' | 'completed' | 'failed' | 'paused';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed';
export type AgentStatus = 'running' | 'offline' | 'error';

// BuildStage enum - matches backend exactly
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
  request_id?: string;
}

// AgentCore configuration for deployed agents
export interface AgentCoreConfig {
  agent_arn: string;
  agent_alias_id: string;
  agent_alias_arn: string;
}

// Runtime statistics for agent invocations
export interface RuntimeStats {
  total_invocations: number;
  successful_invocations: number;
  failed_invocations: number;
  avg_duration_ms: number;
  last_invoked_at?: string;
}

// Create Project Request (replaces CreateAgentRequest)
export interface CreateProjectRequest {
  requirement: string;
  user_id?: string;
  project_name?: string;
  agent_name_map?: Record<string, string>;
}

export interface CreateProjectResponseData {
  project_id: string;
  project_name?: string;
  status: ProjectStatus;
  progress: number;
  created_at: string;
  updated_at: string;
}

export type CreateProjectResponse = ApiResponse<CreateProjectResponseData>;

// Legacy CreateAgentRequest (may be deprecated)
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
  call_count?: number;
  success_rate?: number;
  capabilities?: string[];
  region?: string;
  agentcore_config?: AgentCoreConfig;
  runtime_stats?: RuntimeStats;
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
  items: ProjectListItemRecord[];
  last_evaluated_key?: string | null;
  count: number;
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
  tools_count?: number;
  dependencies?: string[];
  supported_models?: string[];
  tags?: string[];
  call_count?: number;
  success_rate?: number;
  last_called_at?: string | null;
  created_at: string;
  updated_at?: string;
  capabilities?: string[];
  region?: string;
  agentcore_config?: AgentCoreConfig;
  runtime_stats?: RuntimeStats;
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

// Project Control Operations
export type ProjectControlAction = 'pause' | 'resume' | 'stop' | 'restart';

export interface ProjectControlRequest {
  action: ProjectControlAction;
}

export interface ProjectControlResponseData {
  project_id: string;
  action: ProjectControlAction;
  new_status: ProjectStatus;
  message: string;
}

export type ProjectControlResponse = ApiResponse<ProjectControlResponseData>;

// Agent Invocation
export interface AgentInvocationRequest {
  input_text: string;
  session_id?: string;
  enable_trace?: boolean;
  end_session?: boolean;
  session_state?: Record<string, unknown>;
}

export interface AgentInvocationResponseData {
  invocation_id: string;
  session_id?: string;
  output: string;
  duration_ms: number;
  status: 'success' | 'failed';
  trace?: Record<string, unknown>;
  created_at: string;
}

export type AgentInvocationResponse = ApiResponse<AgentInvocationResponseData>;

// Session Message Send
export interface SendMessageRequest {
  content: string;
  role?: 'user' | 'assistant';
  metadata?: Record<string, unknown>;
}

export interface SendMessageResponseData {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type SendMessageResponse = ApiResponse<SendMessageResponseData>;

// Agent Update
export interface UpdateAgentRequest {
  description?: string;
  status?: AgentStatus;
  metadata?: Record<string, unknown>;
}

export interface UpdateAgentStatusRequest {
  status: AgentStatus;
  error_message?: string;
}

// Statistics Types
export interface StatisticsOverviewData {
  total_agents: number;
  running_agents: number;
  building_agents: number;
  offline_agents: number;
  total_builds: number;
  success_rate: number;
  avg_build_time_minutes: number;
  today_calls: number;
}

export type StatisticsOverviewResponse = ApiResponse<StatisticsOverviewData>;

export interface BuildStatisticsData {
  date: string;
  total_builds: number;
  successful_builds: number;
  failed_builds: number;
  avg_duration_minutes: number;
  builds_by_stage?: Record<string, number>;
}

export type BuildStatisticsResponse = ApiResponse<BuildStatisticsData[]>;

export interface InvocationStatisticsData {
  date: string;
  total_invocations: number;
  successful_invocations: number;
  failed_invocations: number;
  success_rate: number;
  avg_duration_ms: number;
}

export type InvocationStatisticsResponse = ApiResponse<InvocationStatisticsData[]>;

export interface TrendDataPoint {
  date: string;
  value: number;
}

export interface TrendData {
  metric: string;
  data_points: TrendDataPoint[];
}

export type TrendDataResponse = ApiResponse<TrendData>;
