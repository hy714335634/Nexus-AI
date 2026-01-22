/**
 * Nexus AI API v2 类型定义
 */

// ============== 枚举类型 ==============

export type ProjectStatus = 'pending' | 'queued' | 'building' | 'completed' | 'failed' | 'paused' | 'cancelled';
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type AgentStatus = 'running' | 'offline' | 'error' | 'deploying';
export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
export type TaskType = 'build_agent' | 'deploy_agent' | 'invoke_agent';

export type BuildStage =
  | 'orchestrator'
  | 'requirements_analysis'
  | 'system_architecture'
  | 'agent_design'
  | 'prompt_engineer'
  | 'tools_developer'
  | 'agent_code_developer'
  | 'agent_developer_manager'
  | 'agent_deployer';

// ============== 基础类型 ==============

export interface APIResponse<T = unknown> {
  success: boolean;
  message?: string;
  data?: T;
  timestamp?: string;
  request_id?: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> extends APIResponse<T[]> {
  pagination?: PaginationMeta;
}

// ============== Project 类型 ==============

export interface CreateProjectRequest {
  requirement: string;
  project_name?: string;
  user_id?: string;
  user_name?: string;
  priority?: number;
  tags?: string[];
}

export interface ProjectRecord {
  project_id: string;
  project_name?: string;
  status: ProjectStatus;
  requirement: string;
  user_id?: string;
  user_name?: string;
  priority: number;
  tags: string[];
  progress: number;
  current_stage?: string;
  error_info?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
  metrics?: Record<string, unknown>;
}

export interface ProjectSummary {
  project_id: string;
  project_name?: string;
  status: ProjectStatus;
  progress: number;
  current_stage?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectDetail extends ProjectRecord {
  stages?: StageRecord[];
  completed_stages?: number;
  total_stages?: number;
}

export interface ProjectControlRequest {
  action: 'pause' | 'resume' | 'stop' | 'restart' | 'cancel';
  reason?: string;
}

// ============== Stage 类型 ==============

export interface StageRecord {
  project_id: string;
  stage_name: string;
  stage_number: number;
  display_name: string;
  status: StageStatus;
  agent_name?: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  input_tokens?: number;
  output_tokens?: number;
  tool_calls?: number;
  output_data?: Record<string, unknown>;
  error_message?: string;
  logs?: string[];
}

// ============== Agent 类型 ==============

export interface AgentCoreConfig {
  agent_arn?: string;
  agent_alias_id?: string;
  agent_alias_arn?: string;
}

// AgentCore 运行时信息
export interface AgentCoreRuntimeInfo {
  runtime_id?: string;
  runtime_arn?: string;
  runtime_alias?: string;
  region?: string;
  // AWS Console 链接
  console_url?: string;
  logs_url?: string;
  trace_url?: string;
}

export interface AgentRecord {
  agent_id: string;
  project_id?: string;
  agent_name: string;
  description?: string;
  category?: string;
  version: string;
  status: AgentStatus;
  deployment_type: string;
  agentcore_config?: AgentCoreConfig;
  // AgentCore 运行时扩展信息
  agentcore_runtime_arn?: string;
  agentcore_runtime_alias?: string;
  agentcore_region?: string;
  capabilities: string[];
  tools: string[];
  prompt_path?: string;
  code_path?: string;
  created_at?: string;
  updated_at?: string;
  deployed_at?: string;
  total_invocations: number;
  successful_invocations: number;
  failed_invocations: number;
  avg_duration_ms: number;
  last_invoked_at?: string;
}

export type AgentDeploymentType = 'local' | 'agentcore';

export interface AgentSummary {
  agent_id: string;
  agent_name: string;
  status: AgentStatus;
  category?: string;
  version?: string;
  deployment_type?: AgentDeploymentType;
  total_invocations: number;
  created_at?: string;
}

export interface InvokeAgentRequest {
  input_text: string;
  session_id?: string;
  enable_trace?: boolean;
  metadata?: Record<string, unknown>;
}

// ============== Session 类型 ==============

export interface SessionRecord {
  session_id: string;
  agent_id: string;
  user_id?: string;
  display_name?: string;
  status: string;
  message_count: number;
  created_at?: string;
  last_active_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateSessionRequest {
  display_name?: string;
  user_id?: string;
  metadata?: Record<string, unknown>;
}

export interface MessageRecord {
  session_id: string;
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface SendMessageRequest {
  content: string;
  role?: 'user' | 'assistant' | 'system';
  metadata?: Record<string, unknown>;
}

// ============== Task 类型 ==============

export interface TaskRecord {
  task_id: string;
  task_type: TaskType;
  project_id?: string;
  status: TaskStatus;
  priority: number;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error_message?: string;
  retry_count: number;
  created_at?: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
  worker_id?: string;
}

// ============== Statistics 类型 ==============

export interface StatisticsOverview {
  total_projects: number;
  building_projects: number;
  completed_projects: number;
  failed_projects: number;
  total_agents: number;
  running_agents: number;
  total_invocations: number;
  today_invocations: number;
  success_rate: number;
  avg_build_time_minutes: number;
}

export interface BuildStatistics {
  date: string;
  total_builds: number;
  successful_builds: number;
  failed_builds: number;
  avg_duration_minutes: number;
}

export interface InvocationStatistics {
  date: string;
  total_invocations: number;
  successful_invocations: number;
  failed_invocations: number;
  avg_duration_ms: number;
}

// ============== Build Dashboard 类型 ==============

export interface BuildDashboardStage {
  name: string;
  display_name: string;
  order: number;
  status: StageStatus;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error?: string;
  input_tokens?: number;
  output_tokens?: number;
  tool_calls?: number;
  doc_path?: string;
  artifact_paths?: string[];
}

export interface BuildDashboardMetrics {
  total_duration_seconds?: number;
  input_tokens?: number;
  output_tokens?: number;
  tool_calls?: number;
  total_tools?: number;
}

export interface BuildDashboardData {
  project_id: string;
  project_name?: string;
  status: ProjectStatus;
  progress: number;
  requirement?: string;
  stages: BuildDashboardStage[];
  total_stages: number;
  completed_stages: number;
  updated_at?: string;
  metrics?: BuildDashboardMetrics;
  error_info?: Record<string, unknown>;
  has_workflow_report?: boolean;
  source?: 'database' | 'local';
}

// ============== API 响应类型 ==============

export type CreateProjectResponse = APIResponse<{
  project_id: string;
  task_id: string;
  project_name: string;
  status: ProjectStatus;
  message: string;
}>;

export type ProjectListResponse = PaginatedResponse<ProjectSummary>;
export type ProjectDetailResponse = APIResponse<ProjectDetail>;
export type StageListResponse = APIResponse<StageRecord[]>;
export type BuildDashboardResponse = APIResponse<BuildDashboardData>;

export type AgentListResponse = PaginatedResponse<AgentSummary>;
export type AgentDetailResponse = APIResponse<AgentRecord>;
export type InvokeAgentResponse = APIResponse<{
  invocation_id: string;
  session_id?: string;
  output: string;
  duration_ms: number;
  status: string;
}>;

export type SessionListResponse = APIResponse<SessionRecord[]>;
export type SessionDetailResponse = APIResponse<SessionRecord>;
export type MessageListResponse = APIResponse<MessageRecord[]>;
export type SendMessageResponse = APIResponse<MessageRecord>;

export type TaskStatusResponse = APIResponse<TaskRecord>;

export type StatisticsOverviewResponse = APIResponse<StatisticsOverview>;
export type BuildStatisticsResponse = APIResponse<BuildStatistics[]>;
export type InvocationStatisticsResponse = APIResponse<InvocationStatistics[]>;

// ============== Agent Files 类型 ==============

export interface FileInfo {
  path: string;
  name: string;
  language: string;
  content?: string;
  size?: number;
  exists: boolean;
}

export interface ToolFileInfo {
  path: string;
  name: string;
  language: string;
  content?: string;
  size?: number;
  exists: boolean;
}

export interface AgentFilesData {
  agent_id: string;
  agent_name?: string;
  code_file?: FileInfo;
  prompt_file?: FileInfo;
  tool_files: ToolFileInfo[];
}

export interface SaveFileRequest {
  content: string;
  file_type: 'code' | 'prompt' | 'tool';
  tool_path?: string;
}

export type AgentFilesResponse = APIResponse<AgentFilesData>;
export type AgentFileResponse = APIResponse<FileInfo>;
export type AgentToolFilesResponse = APIResponse<ToolFileInfo[]>;


// ============== Agent Tools 类型 ==============

export interface ToolParameter {
  name: string;
  type: string;
  description?: string;
  required: boolean;
  default?: unknown;
}

export interface ToolInfo {
  name: string;
  type: 'builtin' | 'generated' | 'system' | 'template' | 'mcp';
  category?: string;
  description?: string;
  file_path?: string;
  parameters: ToolParameter[];
  package?: string;
  enabled: boolean;
  mcp_server?: string;
  source_code?: string;
  return_type?: string;  // 返回值类型
}

export interface MCPServerInfo {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  disabled: boolean;
  auto_approve: string[];
  tools: string[];
}

export interface ToolTestRequest {
  parameters: Record<string, unknown>;
}

export interface ToolTestResult {
  success: boolean;
  output?: string;
  error?: string;
  duration_ms?: number;
}

export interface ToolListData {
  tools: ToolInfo[];
  total: number;
  by_type: {
    builtin: number;
    generated: number;
    system: number;
    template: number;
    mcp: number;
  };
}

export interface MCPServerListData {
  servers: MCPServerInfo[];
  total: number;
  enabled: number;
  disabled: number;
}

export interface ToolCategoriesData {
  categories: string[];
  total: number;
}

export type ToolListResponse = APIResponse<ToolListData>;
export type ToolDetailResponse = APIResponse<ToolInfo>;
export type ToolTestResponse = APIResponse<ToolTestResult>;
export type ToolCategoriesResponse = APIResponse<ToolCategoriesData>;
export type MCPServerListResponse = APIResponse<MCPServerListData>;
export type MCPServerDetailResponse = APIResponse<MCPServerInfo>;
