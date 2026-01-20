/**
 * Nexus AI API v2 客户端
 */
import type {
  APIResponse,
  CreateProjectRequest,
  CreateProjectResponse,
  ProjectListResponse,
  ProjectDetailResponse,
  StageListResponse,
  BuildDashboardResponse,
  ProjectControlRequest,
  AgentListResponse,
  AgentDetailResponse,
  InvokeAgentRequest,
  InvokeAgentResponse,
  CreateSessionRequest,
  SessionListResponse,
  SessionDetailResponse,
  MessageListResponse,
  SendMessageRequest,
  SendMessageResponse,
  TaskStatusResponse,
  StatisticsOverviewResponse,
  BuildStatisticsResponse,
  InvocationStatisticsResponse,
} from '@/types/api-v2';

const API_BASE = '/api/v2';

/**
 * API 错误类
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly payload?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * 基础 fetch 封装
 */
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  
  const data = await response.json().catch(() => ({}));
  
  if (!response.ok) {
    const message = data?.message || data?.error?.message || '请求失败';
    throw new ApiError(response.status, message, data);
  }
  
  return data as T;
}

// ============== Projects API ==============

/**
 * 创建项目
 */
export async function createProject(
  request: CreateProjectRequest
): Promise<CreateProjectResponse> {
  return apiFetch<CreateProjectResponse>('/projects', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * 获取项目列表
 */
export async function listProjects(params?: {
  status?: string;
  user_id?: string;
  page?: number;
  limit?: number;
}): Promise<ProjectListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.user_id) searchParams.set('user_id', params.user_id);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.limit) searchParams.set('limit', String(params.limit));
  
  const query = searchParams.toString();
  return apiFetch<ProjectListResponse>(`/projects${query ? `?${query}` : ''}`);
}

/**
 * 获取项目详情
 */
export async function getProject(projectId: string): Promise<ProjectDetailResponse> {
  return apiFetch<ProjectDetailResponse>(`/projects/${projectId}`);
}

/**
 * 获取构建仪表板
 */
export async function getBuildDashboard(projectId: string): Promise<BuildDashboardResponse> {
  return apiFetch<BuildDashboardResponse>(`/projects/${projectId}/build`);
}

/**
 * 获取项目阶段列表
 */
export async function listProjectStages(projectId: string): Promise<StageListResponse> {
  return apiFetch<StageListResponse>(`/projects/${projectId}/stages`);
}

/**
 * 控制项目
 */
export async function controlProject(
  projectId: string,
  request: ProjectControlRequest
): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/projects/${projectId}/control`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * 删除项目
 */
export async function deleteProject(projectId: string): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/projects/${projectId}`, {
    method: 'DELETE',
  });
}

// ============== Agents API ==============

/**
 * 获取 Agent 列表
 */
export async function listAgents(params?: {
  status?: string;
  category?: string;
  page?: number;
  limit?: number;
}): Promise<AgentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.limit) searchParams.set('limit', String(params.limit));
  
  const query = searchParams.toString();
  return apiFetch<AgentListResponse>(`/agents${query ? `?${query}` : ''}`);
}

/**
 * 获取 Agent 详情
 */
export async function getAgent(agentId: string): Promise<AgentDetailResponse> {
  return apiFetch<AgentDetailResponse>(`/agents/${agentId}`);
}

/**
 * 调用 Agent
 */
export async function invokeAgent(
  agentId: string,
  request: InvokeAgentRequest
): Promise<InvokeAgentResponse> {
  return apiFetch<InvokeAgentResponse>(`/agents/${agentId}/invoke`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * 删除 Agent
 */
export async function deleteAgent(agentId: string): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/agents/${agentId}`, {
    method: 'DELETE',
  });
}

// ============== Sessions API ==============

/**
 * 创建会话
 */
export async function createSession(
  agentId: string,
  request?: CreateSessionRequest
): Promise<SessionDetailResponse> {
  return apiFetch<SessionDetailResponse>(`/agents/${agentId}/sessions`, {
    method: 'POST',
    body: JSON.stringify(request || {}),
  });
}

/**
 * 获取 Agent 的会话列表
 */
export async function listAgentSessions(
  agentId: string,
  limit?: number
): Promise<SessionListResponse> {
  const query = limit ? `?limit=${limit}` : '';
  return apiFetch<SessionListResponse>(`/agents/${agentId}/sessions${query}`);
}

/**
 * 获取会话详情
 */
export async function getSession(sessionId: string): Promise<SessionDetailResponse> {
  return apiFetch<SessionDetailResponse>(`/sessions/${sessionId}`);
}

/**
 * 获取会话消息列表
 */
export async function listMessages(
  sessionId: string,
  limit?: number
): Promise<MessageListResponse> {
  const query = limit ? `?limit=${limit}` : '';
  return apiFetch<MessageListResponse>(`/sessions/${sessionId}/messages${query}`);
}

/**
 * 发送消息
 */
export async function sendMessage(
  sessionId: string,
  request: SendMessageRequest
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * 流式对话事件类型
 */
export interface StreamEvent {
  event: 'connected' | 'message' | 'metrics' | 'error' | 'done' | 'heartbeat';
  type?: 'text' | 'tool_use' | 'tool_input' | 'tool_end' | 'message_stop';
  data?: string;
  tool_name?: string;
  tool_id?: string;
  tool_input?: string;
  tool_result?: string;
  stop_reason?: string;
  error?: string;
  session_id?: string;
}

/**
 * 流式对话
 */
export async function* streamChat(
  sessionId: string,
  content: string
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, role: 'user' }),
  });
  
  if (!response.ok) {
    throw new ApiError(response.status, '流式对话失败');
  }
  
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应流');
  }
  
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';
    
    for (const chunk of lines) {
      const dataLine = chunk.split('\n').find(line => line.startsWith('data: '));
      if (dataLine) {
        try {
          const data = JSON.parse(dataLine.slice(6));
          yield data as StreamEvent;
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}

/**
 * 关闭会话
 */
export async function closeSession(sessionId: string): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

// ============== Tasks API ==============

/**
 * 获取任务状态
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return apiFetch<TaskStatusResponse>(`/tasks/${taskId}`);
}

// ============== Statistics API ==============

/**
 * 获取统计概览
 */
export async function getStatisticsOverview(): Promise<StatisticsOverviewResponse> {
  return apiFetch<StatisticsOverviewResponse>('/statistics/overview');
}

/**
 * 获取构建统计
 */
export async function getBuildStatistics(days?: number): Promise<BuildStatisticsResponse> {
  const query = days ? `?days=${days}` : '';
  return apiFetch<BuildStatisticsResponse>(`/statistics/builds${query}`);
}

/**
 * 获取调用统计
 */
export async function getInvocationStatistics(days?: number): Promise<InvocationStatisticsResponse> {
  const query = days ? `?days=${days}` : '';
  return apiFetch<InvocationStatisticsResponse>(`/statistics/invocations${query}`);
}
