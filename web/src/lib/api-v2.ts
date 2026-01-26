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
  AgentFilesResponse,
  AgentFileResponse,
  AgentToolFilesResponse,
  SaveFileRequest,
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
 * 
 * @param agentId Agent ID
 * @param options 删除选项
 * @param options.deleteLocalFiles 是否删除本地文件
 * @param options.deleteCloudResources 是否删除云资源（AgentCore、ECR）
 */
export async function deleteAgent(
  agentId: string,
  options?: {
    deleteLocalFiles?: boolean;
    deleteCloudResources?: boolean;
  }
): Promise<APIResponse> {
  const searchParams = new URLSearchParams();
  if (options?.deleteLocalFiles) {
    searchParams.set('delete_local_files', 'true');
  }
  if (options?.deleteCloudResources) {
    searchParams.set('delete_cloud_resources', 'true');
  }
  
  const query = searchParams.toString();
  return apiFetch<APIResponse>(`/agents/${agentId}${query ? `?${query}` : ''}`, {
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
  type?: 'text' | 'tool_use' | 'tool_input' | 'tool_end' | 'message_stop' | 'content_block_stop';
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
 * Agent 上下文信息
 */
export interface AgentContext {
  agent_id: string;
  display_name?: string;
  system_prompt_path?: string;
  code_path?: string;
  tools_path?: string;
  description?: string;
  tags?: string[];
  runtime_model_id?: string;
  agentcore_runtime_arn?: string;
  agentcore_runtime_alias?: string;
  agentcore_region?: string;
}

/**
 * 获取 Agent 上下文信息
 */
export async function getAgentContext(agentId: string): Promise<APIResponse<AgentContext>> {
  return apiFetch<APIResponse<AgentContext>>(`/agents/${agentId}/context`);
}

/**
 * 解析 SSE 数据块并提取事件
 * 
 * @param chunk - SSE 数据块（可能包含多行）
 * @returns 解析出的事件数据，如果解析失败则返回 null
 */
function parseSSEChunk(chunk: string): StreamEvent | null {
  if (!chunk || !chunk.trim()) return null;
  
  // 查找 data: 开头的行
  const lines = chunk.split('\n');
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (trimmedLine.startsWith('data: ')) {
      try {
        const jsonStr = trimmedLine.slice(6);
        if (jsonStr) {
          return JSON.parse(jsonStr) as StreamEvent;
        }
      } catch {
        // 忽略解析错误
      }
    }
  }
  return null;
}

/**
 * 获取流式 API 的直接后端 URL
 * 绕过 Next.js rewrites 代理，避免响应被缓冲
 * 
 * 注意：Next.js 的 NEXT_PUBLIC_* 环境变量在构建时内联
 * 如果未设置，默认使用当前页面的 origin（同源）或 localhost:8000
 */
function getStreamApiUrl(path: string): string {
  // 优先使用环境变量（构建时内联）
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  
  if (envUrl) {
    return `${envUrl}/api/v2${path}`;
  }
  
  // 在浏览器端，尝试使用同源后端（如果前后端部署在同一域名下）
  // 否则回退到 localhost:8000
  if (typeof window !== 'undefined') {
    // 开发环境默认使用 localhost:8000
    // 生产环境如果前后端同源，可以使用 window.location.origin
    const backendUrl = 'http://localhost:8000';
    return `${backendUrl}/api/v2${path}`;
  }
  
  return `http://localhost:8000/api/v2${path}`;
}

/**
 * 流式对话（直接连接后端，绕过 Next.js 代理）
 */
export async function* streamChat(
  sessionId: string,
  content: string
): AsyncGenerator<StreamEvent> {
  // 直接访问后端 API，绕过 Next.js rewrites 代理
  // Next.js rewrites 会缓冲整个响应，导致无法实现真正的流式输出
  const streamUrl = getStreamApiUrl(`/sessions/${sessionId}/stream`);
  
  // 调试日志
  console.log('[streamChat] Connecting to:', streamUrl);
  
  const response = await fetch(streamUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, role: 'user' }),
  });
  
  console.log('[streamChat] Response status:', response.status);
  console.log('[streamChat] Response headers:', Object.fromEntries(response.headers.entries()));
  
  if (!response.ok) {
    throw new ApiError(response.status, '流式对话失败');
  }
  
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应流');
  }
  
  const decoder = new TextDecoder();
  let buffer = '';
  let eventCount = 0;
  
  while (true) {
    const { done, value } = await reader.read();
    
    if (value) {
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      console.log('[streamChat] Received chunk, buffer length:', buffer.length);
    }
    
    // 按双换行符分割 SSE 事件
    // SSE 格式: data: {...}\n\n
    let eventEndIndex: number;
    while ((eventEndIndex = buffer.indexOf('\n\n')) !== -1) {
      const chunk = buffer.slice(0, eventEndIndex);
      buffer = buffer.slice(eventEndIndex + 2);
      
      const event = parseSSEChunk(chunk);
      if (event) {
        eventCount++;
        console.log('[streamChat] Yielding event #' + eventCount + ':', event.event, event.type);
        yield event;
      }
    }
    
    if (done) {
      console.log('[streamChat] Stream done, remaining buffer:', buffer.length);
      // 流结束时，处理缓冲区中剩余的数据
      if (buffer.trim()) {
        const event = parseSSEChunk(buffer);
        if (event) {
          eventCount++;
          console.log('[streamChat] Yielding final event #' + eventCount + ':', event.event, event.type);
          yield event;
        }
      }
      console.log('[streamChat] Total events yielded:', eventCount);
      break;
    }
  }
}

/**
 * 直接调用 AgentCore 流式对话（前端直连）
 * 
 * 用于已部署到 AgentCore 的 Agent，前端直接与 AgentCore Runtime 交互
 * 需要 AWS 凭证配置
 */
export async function* streamChatDirect(
  runtimeArn: string,
  sessionId: string,
  content: string,
  options?: {
    runtimeAlias?: string;
    region?: string;
  }
): AsyncGenerator<StreamEvent> {
  // 直接访问后端 API，绕过 Next.js rewrites 代理
  const streamUrl = getStreamApiUrl('/agentcore/stream');
  
  const response = await fetch(streamUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      runtime_arn: runtimeArn,
      session_id: sessionId,
      content,
      runtime_alias: options?.runtimeAlias || 'DEFAULT',
      region: options?.region,
    }),
  });
  
  if (!response.ok) {
    throw new ApiError(response.status, 'AgentCore 流式对话失败');
  }
  
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应流');
  }
  
  const decoder = new TextDecoder();
  let buffer = '';
  
  while (true) {
    const { done, value } = await reader.read();
    
    if (value) {
      buffer += decoder.decode(value, { stream: true });
    }
    
    // 按双换行符分割 SSE 事件
    let eventEndIndex: number;
    while ((eventEndIndex = buffer.indexOf('\n\n')) !== -1) {
      const chunk = buffer.slice(0, eventEndIndex);
      buffer = buffer.slice(eventEndIndex + 2);
      
      const event = parseSSEChunk(chunk);
      if (event) {
        yield event;
      }
    }
    
    if (done) {
      // 流结束时，处理缓冲区中剩余的数据
      if (buffer.trim()) {
        const event = parseSSEChunk(buffer);
        if (event) {
          yield event;
        }
      }
      break;
    }
  }
}

/**
 * 删除会话及其所有消息
 */
export async function deleteSession(sessionId: string): Promise<APIResponse> {
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

// ============== Agent Files API ==============

/**
 * 获取 Agent 所有文件信息
 */
export async function getAgentFiles(
  agentId: string,
  includeContent: boolean = true
): Promise<AgentFilesResponse> {
  const query = `?include_content=${includeContent}`;
  return apiFetch<AgentFilesResponse>(`/agents/${agentId}/files${query}`);
}

/**
 * 获取 Agent 代码文件
 */
export async function getAgentCode(agentId: string): Promise<AgentFileResponse> {
  return apiFetch<AgentFileResponse>(`/agents/${agentId}/files/code`);
}

/**
 * 获取 Agent 提示词文件
 */
export async function getAgentPrompt(agentId: string): Promise<AgentFileResponse> {
  return apiFetch<AgentFileResponse>(`/agents/${agentId}/files/prompt`);
}

/**
 * 获取 Agent 工具文件列表
 */
export async function getAgentTools(agentId: string): Promise<AgentToolFilesResponse> {
  return apiFetch<AgentToolFilesResponse>(`/agents/${agentId}/files/tools`);
}

/**
 * 保存 Agent 代码文件
 */
export async function saveAgentCode(
  agentId: string,
  content: string
): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/agents/${agentId}/files/code`, {
    method: 'PUT',
    body: JSON.stringify({ content, file_type: 'code' }),
  });
}

/**
 * 保存 Agent 提示词文件
 */
export async function saveAgentPrompt(
  agentId: string,
  content: string
): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/agents/${agentId}/files/prompt`, {
    method: 'PUT',
    body: JSON.stringify({ content, file_type: 'prompt' }),
  });
}

/**
 * 保存 Agent 工具文件
 */
export async function saveAgentTool(
  agentId: string,
  toolName: string,
  content: string
): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/agents/${agentId}/files/tools/${toolName}`, {
    method: 'PUT',
    body: JSON.stringify({ content, file_type: 'tool' }),
  });
}


// ============== Agent Tools API ==============

import type {
  ToolListResponse,
  ToolDetailResponse,
  ToolTestResponse,
  ToolTestRequest,
  ToolCategoriesResponse,
  MCPServerListResponse,
  MCPServerDetailResponse,
} from '@/types/api-v2';

/**
 * 获取工具分类列表
 */
export async function getToolCategories(): Promise<ToolCategoriesResponse> {
  return apiFetch<ToolCategoriesResponse>('/tools/categories');
}

/**
 * 获取工具列表
 */
export async function listTools(params?: {
  type?: string;
  category?: string;
  search?: string;
}): Promise<ToolListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set('type', params.type);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.search) searchParams.set('search', params.search);
  
  const query = searchParams.toString();
  return apiFetch<ToolListResponse>(`/tools/list${query ? `?${query}` : ''}`);
}

/**
 * 获取工具详情
 */
export async function getToolDetail(
  toolName: string,
  type?: string
): Promise<ToolDetailResponse> {
  const query = type ? `?type=${type}` : '';
  return apiFetch<ToolDetailResponse>(`/tools/${encodeURIComponent(toolName)}${query}`);
}

/**
 * 测试工具
 */
export async function testTool(
  toolName: string,
  request: ToolTestRequest
): Promise<ToolTestResponse> {
  return apiFetch<ToolTestResponse>(`/tools/${encodeURIComponent(toolName)}/test`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * 获取 MCP 服务器列表
 */
export async function listMCPServers(): Promise<MCPServerListResponse> {
  return apiFetch<MCPServerListResponse>('/tools/mcp/servers');
}

/**
 * 获取 MCP 服务器详情
 */
export async function getMCPServer(serverName: string): Promise<MCPServerDetailResponse> {
  return apiFetch<MCPServerDetailResponse>(`/tools/mcp/servers/${encodeURIComponent(serverName)}`);
}

/**
 * 更新 MCP 服务器配置
 */
export async function updateMCPServer(
  serverName: string,
  config: { disabled?: boolean; auto_approve?: string[] }
): Promise<APIResponse> {
  return apiFetch<APIResponse>(`/tools/mcp/servers/${encodeURIComponent(serverName)}`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}
