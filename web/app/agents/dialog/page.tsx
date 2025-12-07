'use client';

import { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import styles from './dialog.module.css';
import {
  createAgentSession,
  fetchAgentContext,
  fetchAgentMessages,
  fetchAgentSessions,
  fetchAgentsList,
} from '@/lib/agents';
import type {
  AgentDialogMessage,
  AgentDialogSession,
  AgentSummary,
  AgentContextResponseData,
} from '@/types/api';
import { toast } from 'sonner';

interface StreamMetrics {
  latency_ms?: number;
  input_tokens?: number;
  output_tokens?: number;
  tool_calls?: number;
  [key: string]: unknown;
}

interface ToolUseBlock {
  id: string;
  tool_name: string;
  tool_input: string;
  status: 'running' | 'completed';
}

interface StreamingState {
  textContent: string;
  toolBlocks: ToolUseBlock[];
  currentToolId: string | null;
}

/**
 * 解码 Unicode 转义序列
 */
function decodeUnicodeEscapes(text: string): string {
  if (!text) return text;
  try {
    // 处理 \uXXXX 格式的 Unicode 转义
    return text.replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) =>
      String.fromCharCode(parseInt(hex, 16))
    );
  } catch {
    return text;
  }
}

const TOOL_TIPS = ['解释当前步骤', '重试上一步', '列出生成的工具'];

function formatTime(value?: string) {
  if (!value) {
    return '';
  }
  return new Date(value).toLocaleTimeString();
}

function formatLatency(metrics: StreamMetrics) {
  if (metrics.latency_ms == null) {
    return '—';
  }
  return `${metrics.latency_ms.toFixed(0)} ms`;
}

function formatTokens(value?: number) {
  if (value == null) {
    return '—';
  }
  return value.toLocaleString();
}

function buildAssistantDraft(): AgentDialogMessage {
  return {
    message_id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
    metadata: { streaming: true },
  };
}

/**
 * 将字段名格式化为可读标题
 */
function formatFieldName(field: string): string {
  return field
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * 从 JSON 对象中提取可读的文本内容
 */
function extractReadableContent(obj: unknown, depth = 0): string {
  if (depth > 5) return ''; // 防止过深递归

  if (typeof obj === 'string') {
    return obj;
  }

  if (Array.isArray(obj)) {
    const items = obj
      .map((item) => {
        const itemContent = extractReadableContent(item, depth + 1);
        if (itemContent && itemContent.length > 5) {
          // 如果是简单字符串列表，添加列表标记
          if (typeof item === 'string') {
            return `- ${itemContent}`;
          }
          return itemContent;
        }
        return '';
      })
      .filter(Boolean);
    return items.join('\n');
  }

  if (typeof obj === 'object' && obj !== null) {
    const record = obj as Record<string, unknown>;
    const parts: string[] = [];

    // 定义友好的字段名映射
    const fieldLabels: Record<string, string> = {
      'research_summary': '## 研究摘要',
      'summary': '## 摘要',
      'conclusion': '## 结论',
      'conclusions': '## 结论',
      'result': '## 结果',
      'results': '## 结果',
      'analysis': '## 分析',
      'analysis_results': '## 分析结果',
      'findings': '## 发现',
      'key_findings': '## 关键发现',
      'recommendations': '## 建议',
      'suggestions': '## 建议',
      'suggestions_for_improvement': '## 改进建议',
      'additional_notes': '## 补充说明',
      'notes': '## 备注',
      'description': '## 描述',
      'content': '',
      'text': '',
      'message': '',
      'answer': '## 回答',
      'response': '',
      'output': '',
      'explanation': '## 解释',
      'details': '## 详情',
      'overview': '## 概述',
      'introduction': '## 简介',
      'background': '## 背景',
      'methodology': '## 方法',
      'data': '## 数据',
      'sources': '## 来源',
      'references': '## 参考资料',
      'limitations': '## 局限性',
      'future_work': '## 未来工作',
      'next_steps': '## 下一步',
      'action_items': '## 行动项',
      'tasks': '## 任务',
      'status': '**状态**',
      'error': '**错误**',
      'warning': '**警告**',
    };

    // 优先处理的字段顺序
    const priorityFields = [
      'summary', 'research_summary', 'overview', 'introduction',
      'content', 'text', 'message', 'answer', 'response', 'output',
      'analysis', 'analysis_results', 'findings', 'key_findings', 'results', 'result',
      'conclusion', 'conclusions',
      'recommendations', 'suggestions', 'suggestions_for_improvement',
      'additional_notes', 'notes',
      'explanation', 'details', 'description',
    ];

    // 首先按优先级处理字段
    const processedFields = new Set<string>();

    for (const field of priorityFields) {
      if (field in record && record[field] != null) {
        const value = record[field];
        const extracted = extractReadableContent(value, depth + 1);
        if (extracted && extracted.length > 5) {
          const label = fieldLabels[field] || `## ${formatFieldName(field)}`;
          if (label) {
            parts.push(`${label}\n${extracted}`);
          } else {
            parts.push(extracted);
          }
          processedFields.add(field);
        }
      }
    }

    // 然后处理其他字段
    for (const [key, value] of Object.entries(record)) {
      if (processedFields.has(key)) continue;

      // 跳过技术性字段
      if (['id', 'timestamp', 'created_at', 'updated_at', 'metadata', 'raw', 'debug', 'trace', 'logs'].includes(key)) {
        continue;
      }

      const extracted = extractReadableContent(value, depth + 1);
      if (extracted && extracted.length > 10) {
        const label = fieldLabels[key] || `## ${formatFieldName(key)}`;
        parts.push(`${label}\n${extracted}`);
      }
    }

    return parts.join('\n\n');
  }

  // 对于数字和布尔值
  if (typeof obj === 'number' || typeof obj === 'boolean') {
    return String(obj);
  }

  return '';
}

/**
 * 清理消息内容，处理 JSON 响应并提取可读文本
 */
function cleanMessageContent(content: string): string {
  if (!content) return content;

  // 首先处理转义字符：将字面量 \n \t 替换为真正的换行符
  let cleaned = content
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\"/g, '"');

  // 尝试解析为 JSON 并提取可读内容
  const trimmed = cleaned.trim();
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const json = JSON.parse(trimmed);
      const extractedText = extractReadableContent(json);
      if (extractedText && extractedText.length > 20) {
        return extractedText;
      }
    } catch {
      // 不是有效的 JSON，继续处理
    }
  }

  // 检查是否整个内容是被引号包裹的 JSON 字符串
  if ((trimmed.startsWith('"{') && trimmed.endsWith('}"')) ||
      (trimmed.startsWith("'{") && trimmed.endsWith("}'"))) {
    try {
      const unquoted = JSON.parse(trimmed);
      if (typeof unquoted === 'string') {
        const innerJson = JSON.parse(unquoted);
        const extractedText = extractReadableContent(innerJson);
        if (extractedText && extractedText.length > 20) {
          return extractedText;
        }
      }
    } catch {
      // 继续处理
    }
  }

  // 找到第一个 { 的位置（JSON 开始）
  const jsonStart = cleaned.indexOf('\n{');
  const jsonStart2 = cleaned.indexOf('\n\n{');
  const actualJsonStart = jsonStart2 !== -1 ? jsonStart2 : jsonStart;

  // 找到最后一个 } 的位置（JSON 结束）
  const jsonEnd = cleaned.lastIndexOf('}');

  // 如果找到了 JSON 块，尝试提取其中的可读内容
  if (actualJsonStart !== -1 && jsonEnd !== -1 && jsonEnd > actualJsonStart) {
    const beforeJson = cleaned.slice(0, actualJsonStart).trim();
    const jsonString = cleaned.slice(actualJsonStart, jsonEnd + 1).trim();
    const afterJson = cleaned.slice(jsonEnd + 1).trim();

    // 尝试解析嵌入的 JSON
    try {
      const json = JSON.parse(jsonString);
      const extractedFromJson = extractReadableContent(json);

      const textParts: string[] = [];
      if (beforeJson.length > 10) {
        textParts.push(beforeJson);
      }
      if (extractedFromJson && extractedFromJson.length > 20) {
        textParts.push(extractedFromJson);
      }
      if (afterJson.length > 10) {
        textParts.push(afterJson);
      }

      if (textParts.length > 0) {
        return textParts.join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
      }
    } catch {
      // JSON 解析失败，使用原有逻辑
      const textParts: string[] = [];
      if (beforeJson.length > 10) {
        textParts.push(beforeJson);
      }
      if (afterJson.length > 10) {
        textParts.push(afterJson);
      }

      if (textParts.length > 0) {
        cleaned = textParts.join('\n\n');
      }
    }
  }

  // 移除 markdown 代码块中的 JSON
  cleaned = cleaned.replace(/```json[\s\S]*?```/g, '');

  // 移除任何剩余的内联 JSON 对象
  cleaned = cleaned.replace(/\{[^{}]*"[^"]+"\s*:[^{}]*\}/g, '');

  // 清理多余的空行
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  return cleaned || content;
}

export default function AgentDialogPage() {
  const queryClient = useQueryClient();
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<AgentDialogSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentDialogMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [metrics, setMetrics] = useState<StreamMetrics>({});
  const [context, setContext] = useState<AgentContextResponseData | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [autoSessionRequested, setAutoSessionRequested] = useState(false);
  const [agentLimit, setAgentLimit] = useState(50);
  const [hasMoreAgents, setHasMoreAgents] = useState(false);

  // 使用 ref 来跟踪流式状态和消息版本，避免 useEffect 依赖问题
  const isStreamingRef = useRef(false);
  const messagesVersionRef = useRef(0);
  const lastLoadedSessionRef = useRef<string | null>(null);
  const messageListRef = useRef<HTMLElement>(null);


  // 自动滚动到底部
  useEffect(() => {
    if (messageListRef.current && isStreaming) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  // Load agents list
  const agentsQuery = useQuery({
    queryKey: ['dialog-agents', agentLimit],
    queryFn: () => fetchAgentsList(agentLimit),
  });

  // Check if there are more agents to load
  useEffect(() => {
    if (agentsQuery.data) {
      setHasMoreAgents(agentsQuery.data.length >= agentLimit);
    }
  }, [agentsQuery.data, agentLimit]);

  // Load sessions for active agent
  const sessionsQuery = useQuery({
    queryKey: ['dialog-sessions', activeAgentId],
    queryFn: () => fetchAgentSessions(activeAgentId as string),
    enabled: Boolean(activeAgentId),
    staleTime: 10_000,
  });

  // Load agent context
  const contextQuery = useQuery({
    queryKey: ['dialog-context', activeAgentId],
    queryFn: () => fetchAgentContext(activeAgentId as string),
    enabled: Boolean(activeAgentId),
  });

  // Handle sessions data changes
  useEffect(() => {
    if (sessionsQuery.data) {
      setSessions(sessionsQuery.data);
      if (!activeSessionId && sessionsQuery.data.length > 0) {
        setActiveSessionId(sessionsQuery.data[0].session_id);
      }
    }
  }, [sessionsQuery.data, activeSessionId]);

  // Handle context data changes
  useEffect(() => {
    if (contextQuery.data) {
      setContext(contextQuery.data);
    }
  }, [contextQuery.data]);

  const createSessionMutation = useMutation({
    mutationFn: (displayName?: string) => createAgentSession(activeAgentId as string, displayName),
    onSuccess: (session) => {
      toast.success('新建会话成功');
      setSessions((prev) => [
        {
          session_id: session.session_id,
          display_name: session.display_name,
          created_at: session.created_at,
          last_active_at: session.last_active_at,
        },
        ...prev,
      ]);
      setActiveSessionId(session.session_id);
      setMessages([]);
      setAutoSessionRequested(true);
      if (activeAgentId) {
        queryClient.invalidateQueries({ queryKey: ['dialog-sessions', activeAgentId] });
      }
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : '新建会话失败');
      setAutoSessionRequested(false);
    },
  });

  // Load messages when session changes
  const messagesQuery = useQuery({
    queryKey: ['dialog-messages', activeAgentId, activeSessionId],
    queryFn: () => fetchAgentMessages(activeAgentId as string, activeSessionId as string),
    enabled: Boolean(activeAgentId && activeSessionId) && !isStreamingRef.current,
    staleTime: Infinity, // 禁用自动刷新，只在切换会话时手动获取
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });

  // Handle messages data changes - 只在切换会话时加载历史消息
  useEffect(() => {
    // 流式传输中不处理（使用 ref 检查，确保最新状态）
    if (isStreamingRef.current) {
      return;
    }
    // 只有当切换了会话且有数据时才更新
    if (messagesQuery.data && activeSessionId && lastLoadedSessionRef.current !== activeSessionId) {
      setMessages(messagesQuery.data);
      lastLoadedSessionRef.current = activeSessionId;
    }
  }, [messagesQuery.data, activeSessionId]);

  const agentItems = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);

  useEffect(() => {
    if (sessionsQuery.data && sessionsQuery.data.length && !activeSessionId) {
      setActiveSessionId(sessionsQuery.data[0].session_id);
    }
  }, [sessionsQuery.data, activeSessionId]);

  useEffect(() => {
    setAutoSessionRequested(false);
  }, [activeAgentId]);

  useEffect(() => {
    if (!activeAgentId) {
      return;
    }
    if (sessionsQuery.isLoading || sessionsQuery.isFetching) {
      return;
    }
    if (createSessionMutation.isPending) {
      return;
    }
    const currentSessions = sessionsQuery.data ?? [];
    if (!currentSessions.length && !autoSessionRequested) {
      setAutoSessionRequested(true);
      createSessionMutation.mutate(undefined);
    }
  }, [
    activeAgentId,
    sessionsQuery.isLoading,
    sessionsQuery.isFetching,
    sessionsQuery.data,
    createSessionMutation,
    autoSessionRequested,
  ]);

  const handleSessionSwitch = useCallback((sessionId: string) => {
    if (sessionId === activeSessionId || isStreamingRef.current) {
      return;
    }
    // 重置 lastLoadedSessionRef 以允许加载新会话的消息
    lastLoadedSessionRef.current = null;
    setActiveSessionId(sessionId);
    setMessages([]);
    setMetrics({});
    setStreamError(null);
    setInputValue('');
    // 强制重新获取消息
    queryClient.invalidateQueries({ queryKey: ['dialog-messages', activeAgentId, sessionId] });
  }, [activeSessionId, activeAgentId, queryClient]);

  const handleAgentSwitch = useCallback((agentId: string) => {
    if (agentId === activeAgentId || isStreamingRef.current) {
      return;
    }
    // 重置 lastLoadedSessionRef 以允许加载新会话的消息
    lastLoadedSessionRef.current = null;
    setActiveAgentId(agentId);
    setActiveSessionId(null);
    setSessions([]);
    setMessages([]);
    setMetrics({});
    setStreamError(null);
    setInputValue('');
    setContext(null);
  }, [activeAgentId]);

  const handleLoadMoreAgents = () => {
    setAgentLimit((prev) => prev + 50);
  };

  // 流式响应处理函数 - 定义在 handleSend 之前以确保可用
  const streamAgentResponse = useCallback(async (
    agentId: string,
    sessionId: string,
    message: string,
    assistantMessageId: string,
  ) => {
    // Use relative path in browser to work with SSH tunnel
    // This ensures the request goes through the same tunnel as the frontend
    const response = await fetch(
      `/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(sessionId)}/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = '请求对话失败';

      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.error?.message || errorJson.detail || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }

      console.error('Stream request failed:', {
        status: response.status,
        statusText: response.statusText,
        error: errorMessage,
      });

      throw new Error(`${errorMessage} (HTTP ${response.status})`);
    }

    if (!response.body) {
      throw new Error('响应体为空，无法建立流式连接');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    // 使用 ref 风格的对象来存储可变状态，避免闭包问题
    const streamState = {
      assistantContent: '',
      toolBlocks: [] as ToolUseBlock[],
      currentToolId: null as string | null,
      currentToolInput: '',
      toolCallCount: 0,
    };

    // 辅助函数：更新消息状态 - 使用 flushSync 强制同步渲染
    const updateMessage = () => {
      const newContent = streamState.assistantContent;
      // 创建 toolBlocks 的深拷贝，确保 React 检测到变化
      const newToolBlocks = streamState.toolBlocks.map(t => ({ ...t }));

      // 使用 flushSync 强制 React 立即渲染，绕过 React 18 的自动批处理
      flushSync(() => {
        setMessages((prev) => {
          // 创建新数组
          const updated: AgentDialogMessage[] = [];
          for (const item of prev) {
            if (item.message_id === assistantMessageId) {
              // 为目标消息创建完全新的对象
              updated.push({
                message_id: item.message_id,
                role: item.role,
                content: newContent,
                created_at: item.created_at,
                metadata: {
                  streaming: true,
                  toolBlocks: newToolBlocks,
                },
              });
            } else {
              updated.push(item);
            }
          }
          return updated;
        });
      });
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf('\n\n');
      while (boundary >= 0) {
        const rawEvent = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf('\n\n');

        if (!rawEvent) {
          continue;
        }

        const dataLine = rawEvent
          .split('\n')
          .map((line) => line.trim())
          .find((line) => line.startsWith('data:'));
        if (!dataLine) {
          continue;
        }

        try {
          const payload = JSON.parse(dataLine.slice(5).trim());
          const eventType = payload.event;

          // 调试日志
          console.log('📥 SSE Event:', eventType, payload.type || '', payload);

          if (eventType === 'message') {
            const msgType = payload.type;

            if (msgType === 'text') {
              // 普通文本内容
              let chunk = String(payload.data ?? '');
              chunk = chunk.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
              streamState.assistantContent += chunk;
              console.log('📝 Text content updated, length:', streamState.assistantContent.length);

              // 立即更新 UI
              updateMessage();
              // 给浏览器一点时间来绘制更新
              await new Promise(r => setTimeout(r, 0));
            } else if (msgType === 'tool_use') {
              // 工具调用开始（可能包含初始 tool_input）
              const toolId = payload.tool_id || `tool-${Date.now()}`;
              const toolName = payload.tool_name || 'unknown';
              const initialInput = decodeUnicodeEscapes(payload.tool_input || '');

              // 检查是否已存在该工具（Strands SDK 可能发送多次更新）
              const existingIndex = streamState.toolBlocks.findIndex(t => t.tool_name === toolName && t.status === 'running');
              if (existingIndex >= 0) {
                // 更新现有工具的输入
                streamState.toolBlocks[existingIndex].tool_input += initialInput;
                streamState.currentToolInput = streamState.toolBlocks[existingIndex].tool_input;
              } else {
                // 新工具调用
                streamState.toolCallCount += 1;
                streamState.currentToolId = toolId;
                streamState.currentToolInput = initialInput;
                const newTool: ToolUseBlock = {
                  id: streamState.currentToolId,
                  tool_name: toolName,
                  tool_input: initialInput,
                  status: 'running',
                };
                streamState.toolBlocks.push(newTool);
              }
              // 立即更新 UI
              updateMessage();
            } else if (msgType === 'tool_input') {
              // 工具输入内容 - 解码 Unicode 转义
              const decodedInput = decodeUnicodeEscapes(payload.data || '');
              streamState.currentToolInput += decodedInput;

              // 找到当前正在运行的工具（通过 currentToolId 或最后一个 running 状态的工具）
              let toolIndex = -1;
              if (streamState.currentToolId) {
                toolIndex = streamState.toolBlocks.findIndex(t => t.id === streamState.currentToolId);
              }
              if (toolIndex < 0) {
                // fallback: 找最后一个 running 状态的工具
                toolIndex = streamState.toolBlocks.findLastIndex(t => t.status === 'running');
              }

              if (toolIndex >= 0) {
                streamState.toolBlocks[toolIndex].tool_input = streamState.currentToolInput;
              }

              // 立即更新 UI
              updateMessage();
            } else if (msgType === 'tool_end') {
              // 工具调用结束
              const endToolName = payload.tool_name;
              const endToolInput = decodeUnicodeEscapes(payload.tool_input || streamState.currentToolInput);

              // 找到对应的工具（通过 currentToolId 或 tool_name）
              let toolIndex = -1;
              if (streamState.currentToolId) {
                toolIndex = streamState.toolBlocks.findIndex(t => t.id === streamState.currentToolId);
              }
              if (toolIndex < 0 && endToolName) {
                // fallback: 找最后一个同名且 running 状态的工具
                toolIndex = streamState.toolBlocks.findLastIndex(t => t.tool_name === endToolName && t.status === 'running');
              }
              if (toolIndex < 0) {
                // fallback: 找最后一个 running 状态的工具
                toolIndex = streamState.toolBlocks.findLastIndex(t => t.status === 'running');
              }

              if (toolIndex >= 0) {
                streamState.toolBlocks[toolIndex].status = 'completed';
                streamState.toolBlocks[toolIndex].tool_input = endToolInput;
              }

              streamState.currentToolId = null;
              streamState.currentToolInput = '';

              // 立即更新 UI
              updateMessage();
            } else {
              // 兼容旧格式：直接是 data 字段
              let chunk = String(payload.data ?? '');
              chunk = chunk.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
              streamState.assistantContent += chunk;
              updateMessage();
            }
          } else if (eventType === 'metrics') {
            const metricData = payload.data as StreamMetrics;
            metricData.tool_calls = streamState.toolCallCount;
            setMetrics(metricData);
            setMessages((prev) =>
              prev.map((item) =>
                item.message_id === assistantMessageId
                  ? {
                      ...item,
                      metadata: {
                        ...(item.metadata ?? {}),
                        metrics: metricData,
                        toolBlocks: [...streamState.toolBlocks],
                      }
                    }
                  : item,
              ),
            );
          } else if (eventType === 'error') {
            throw new Error(String(payload.error ?? 'Agent Runtime Error'));
          }
        } catch (error) {
          if (error instanceof Error && error.message.includes('Agent Runtime Error')) {
            throw error;
          }
          console.warn('Failed to parse stream event', error);
        }
      }
    }

    // 流结束后的最终更新
    setMessages((prev) =>
      prev.map((item) =>
        item.message_id === assistantMessageId
          ? {
              ...item,
              content: streamState.assistantContent || item.content,
              metadata: {
                ...(item.metadata ?? {}),
                streaming: false,
                toolBlocks: [...streamState.toolBlocks],
                tool_calls: streamState.toolCallCount,
              }
            }
          : item,
      ),
    );

    // 更新 metrics 中的工具调用次数
    setMetrics(prev => ({ ...prev, tool_calls: streamState.toolCallCount }));
  }, []);

  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || !activeAgentId || !activeSessionId || isStreaming) {
      return;
    }

    const userMessage: AgentDialogMessage = {
      message_id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      created_at: new Date().toISOString(),
      metadata: {},
    };

    // 增加消息版本号，防止旧数据覆盖
    messagesVersionRef.current += 1;
    const currentVersion = messagesVersionRef.current;

    // 使用 flushSync 确保状态更新和渲染同步完成
    const assistantDraft = buildAssistantDraft();
    isStreamingRef.current = true;

    flushSync(() => {
      setMessages((prev) => [...prev, userMessage, assistantDraft]);
      setInputValue('');
      setStreamError(null);
      setIsStreaming(true);
    });

    try {
      await streamAgentResponse(activeAgentId, activeSessionId, userMessage.content, assistantDraft.message_id);
      // 只有当版本号匹配时才刷新会话列表（确保没有被新的请求覆盖）
      if (messagesVersionRef.current === currentVersion) {
        // 延迟刷新会话列表，不刷新消息（保留本地流式更新的内容）
        await queryClient.invalidateQueries({ queryKey: ['dialog-sessions', activeAgentId] });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '对话过程中出现问题';
      setStreamError(message);
      toast.error(message);
      setMessages((prev) =>
        prev.map((item) =>
          item.message_id === assistantDraft.message_id
            ? { ...item, metadata: { ...(item.metadata ?? {}), error: message }, content: item.content || '发生错误' }
            : item,
        ),
      );
    } finally {
      setIsStreaming(false);
      isStreamingRef.current = false;
      // 更新 lastLoadedSessionRef 以防止 useEffect 覆盖本地消息
      lastLoadedSessionRef.current = activeSessionId;
    }
  }, [inputValue, activeAgentId, activeSessionId, isStreaming, queryClient, streamAgentResponse]);

  const sessionMetrics = useMemo(() => ({
    latency: formatLatency(metrics),
    input: formatTokens(metrics.input_tokens as number | undefined),
    output: formatTokens(metrics.output_tokens as number | undefined),
    toolCalls: metrics.tool_calls != null ? String(metrics.tool_calls) : '—',
  }), [metrics]);

  const activeAgent = useMemo(
    () => agentItems.find((item) => item.agent_id === activeAgentId),
    [agentItems, activeAgentId],
  );

  const hasSelectedAgent = Boolean(activeAgentId);
  const hasActiveSession = Boolean(activeSessionId);
  const isComposerLocked = !hasSelectedAgent || !hasActiveSession;
  const composerPlaceholder = !hasSelectedAgent
    ? '请选择左侧 Agent 后开始对话。'
    : !hasActiveSession
      ? '请选择或新建一个会话。'
      : '描述你的问题，支持多轮上下文。';
  const messageEmptyHint = !hasSelectedAgent
    ? '请选择一个 Agent 查看对话历史。'
    : !hasActiveSession
      ? '请选择会话或点击“新建会话”后开始对话。'
      : '暂无消息，输入内容开始对话。';
  const statusText = !hasSelectedAgent
    ? '请先选择一个 Agent。'
    : !hasActiveSession
      ? '请选择或新建一个会话。'
      : isStreaming
        ? '流式生成中，请稍候…'
        : '提示：支持多轮提问，可切换会话记录。';
  const agentDisplayName = hasSelectedAgent ? (activeAgent?.agent_name ?? '未命名 Agent') : '请选择 Agent';
  const agentStatusLine = hasSelectedAgent
    ? `版本：${activeAgent?.version ?? 'N/A'} · 状态：${activeAgent?.status ?? 'unknown'}`
    : '从左侧列表或下拉框选择一个 Agent 开启对话。';
  const agentAvatarLabel = hasSelectedAgent
    ? (activeAgent?.agent_name ?? 'Agent').slice(0, 2).toUpperCase()
    : 'AG';
  const contextDescription = hasSelectedAgent
    ? context?.description ?? '该 Agent 尚未提供描述。'
    : '请选择 Agent 以查看配置详情。';
  const contextTags = hasSelectedAgent ? context?.tags ?? ['automation', 'agentcore'] : ['待选择'];

  return (
    <div className={styles.page}>
      <aside className={styles.sidebar}>
        <section className={styles.agentSection}>
          <div className={styles.sidebarHeader}>
            <div className={styles.sidebarTitle}>Agent 列表</div>
            {agentsQuery.isLoading ? (
              <div className={styles.loadingText}>加载中...</div>
            ) : (
              <div className={styles.agentCount}>
                共 {agentItems.length} 个
                {hasMoreAgents ? '+' : ''}
              </div>
            )}
          </div>
          <div className={styles.agentList}>
            {agentItems.map((agent) => (
              <button
                key={agent.agent_id}
                type="button"
                className={`${styles.agentItem} ${agent.agent_id === activeAgentId ? styles.agentItemActive : ''}`}
                onClick={() => handleAgentSwitch(agent.agent_id)}
              >
                <div className={styles.agentItemTitle}>{agent.agent_name || agent.agent_id}</div>
                <div className={styles.agentItemMeta}>
                  状态：{agent.status ?? 'unknown'} · 构建：{new Date(agent.created_at).toLocaleDateString()}
                </div>
              </button>
            ))}
            {!agentItems.length && !agentsQuery.isLoading ? (
              <div className={styles.emptyState}>暂无可用 Agent。</div>
            ) : null}
          </div>
          {hasMoreAgents && !agentsQuery.isFetching ? (
            <button
              type="button"
              className={styles.loadMoreButton}
              onClick={handleLoadMoreAgents}
            >
              加载更多
            </button>
          ) : null}
          {agentsQuery.isFetching && agentItems.length > 0 ? (
            <div className={styles.loadingText}>加载中...</div>
          ) : null}
        </section>

        <section className={styles.sessionSection}>
          <div className={styles.sessionHeader}>
            <div className={styles.sidebarTitle}>会话列表</div>
            <div className={styles.sessionActions}>
              <button
                type="button"
                className={styles.sessionActionButton}
                onClick={() => createSessionMutation.mutate(undefined)}
                disabled={!activeAgentId || createSessionMutation.isPending}
              >
                新建会话
              </button>
              <button
                type="button"
                className={styles.sessionActionButton}
                onClick={() => sessionsQuery.refetch()}
                disabled={sessionsQuery.isFetching}
              >
                刷新
              </button>
            </div>
          </div>

          <div className={styles.sessionList}>
            {sessions.map((session) => (
              <div
                key={session.session_id}
                role="button"
                tabIndex={0}
                className={`${styles.sessionItem} ${session.session_id === activeSessionId ? styles.sessionActive : ''}`}
                onClick={() => handleSessionSwitch(session.session_id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSessionSwitch(session.session_id);
                  }
                }}
              >
                <div className={styles.sessionTitle}>{session.display_name ?? session.session_id.slice(0, 8)}</div>
                <div className={styles.sessionMeta}>最近活跃：{formatTime(session.last_active_at)}</div>
              </div>
            ))}
            {sessions.length === 0 ? (
              <div className={styles.emptyState}>
                {hasSelectedAgent ? '暂无会话，点击“新建会话”开始对话。' : '请选择一个 Agent 以查看对应会话。'}
              </div>
            ) : null}
          </div>
        </section>
      </aside>

      <main className={styles.timeline}>
        <header className={styles.timelineHeader}>
          <div className={styles.agentInfo}>
            <div className={styles.agentAvatar}>{agentAvatarLabel}</div>
            <div>
              <div className={styles.agentName}>{agentDisplayName}</div>
              <div className={styles.agentDescription}>{agentStatusLine}</div>
              <div style={{ marginTop: 8 }}>
                <select
                  value={activeAgentId ?? ''}
                  onChange={(event) => handleAgentSwitch(event.target.value)}
                  disabled={!agentItems.length}
                  className={styles.agentSelect}
                >
                  <option value="" disabled>
                    {agentItems.length ? '请选择一个 Agent 开始对话' : '暂无可用 Agent'}
                  </option>
                  {agentItems.map((agent) => (
                    <option key={agent.agent_id} value={agent.agent_id}>
                      {agent.agent_name || agent.agent_id}
                    </option>
                  ))}
                </select>
                {!hasSelectedAgent ? (
                  <div className={styles.selectionPlaceholder}>从左侧列表或下拉框选择 Agent 即可开启一段新对话。</div>
                ) : null}
              </div>
            </div>
          </div>
          <div className={styles.metricBar}>
            <div className={styles.metricCard}>
              <div className={styles.metricLabel}>响应耗时</div>
              <div className={styles.metricValue}>{sessionMetrics.latency}</div>
            </div>
            <div className={styles.metricCard}>
              <div className={styles.metricLabel}>输入 Tokens</div>
              <div className={styles.metricValue}>{sessionMetrics.input}</div>
            </div>
            <div className={styles.metricCard}>
              <div className={styles.metricLabel}>输出 Tokens</div>
              <div className={styles.metricValue}>{sessionMetrics.output}</div>
            </div>
            <div className={styles.metricCard}>
              <div className={styles.metricLabel}>工具调用</div>
              <div className={styles.metricValue}>{sessionMetrics.toolCalls}</div>
            </div>
          </div>
        </header>

        <section ref={messageListRef} className={styles.messageList}>
          {streamError ? <div className={styles.errorBanner}>{streamError}</div> : null}
          {messages.map((message) => {
            const isMessageStreaming = message.metadata?.streaming === true;
            const hasContent = message.content && message.content.trim().length > 0;
            const toolBlocks = (message.metadata?.toolBlocks ?? []) as ToolUseBlock[];

            return (
              <div key={message.message_id} className={styles.messageRow}>
                <div
                  className={`${styles.messageBubble} ${message.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant} ${isMessageStreaming && hasContent ? styles.bubbleStreaming : ''}`}
                >
                  {isMessageStreaming && !hasContent && toolBlocks.length === 0 ? (
                    <div className={styles.streamingIndicator}>
                      <div className={styles.typingDots}>
                        <span className={styles.typingDot} />
                        <span className={styles.typingDot} />
                        <span className={styles.typingDot} />
                      </div>
                      <span className={styles.streamingText}>Agent 正在思考...</span>
                    </div>
                  ) : (
                    <>
                      {/* 渲染工具调用块 */}
                      {toolBlocks.length > 0 && (
                        <div className={styles.toolBlocksContainer}>
                          {toolBlocks.map((tool) => (
                            <div key={tool.id} className={styles.toolUseBlock}>
                              <div className={styles.toolUseHeader}>
                                <span className={styles.toolUseIcon}>🔧</span>
                                <span className={styles.toolUseName}>{tool.tool_name}</span>
                                <span className={styles.toolUseStatus}>
                                  {tool.status === 'running' ? '执行中...' : '已完成'}
                                </span>
                              </div>
                              {tool.tool_input && (
                                <div className={styles.toolUseContent}>
                                  {tool.tool_input.length > 500
                                    ? `${tool.tool_input.slice(0, 500)}...`
                                    : tool.tool_input}
                                </div>
                              )}
                              {tool.status === 'running' && (
                                <div className={styles.toolUseLoading}>
                                  <div className={styles.toolUseSpinner} />
                                  <span>正在执行工具...</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {/* 渲染文本内容 */}
                      {hasContent && (
                        <div className={styles.markdownContent}>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                          >
                            {message.role === 'assistant' ? cleanMessageContent(message.content) : message.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </>
                  )}
                </div>
                <div className={styles.messageMeta}>
                  {message.role === 'user' ? '我' : 'Agent'} · {new Date(message.created_at).toLocaleTimeString()}
                  {isMessageStreaming ? ' · 生成中' : ''}
                  {toolBlocks.length > 0 ? ` · ${toolBlocks.length} 次工具调用` : ''}
                </div>
                {message.metadata && typeof message.metadata.tool === 'string' ? (
                  <div className={styles.toolCard}>
                    <div className={styles.toolTitle}>工具调用：{message.metadata.tool}</div>
                    <div>{JSON.stringify(message.metadata.result)}</div>
                  </div>
                ) : null}
              </div>
            );
          })}
          {!messages.length ? <div className={styles.emptyState}>{messageEmptyHint}</div> : null}
        </section>

        <footer className={styles.composer}>
          <div className={styles.composerBox}>
            <textarea
              className={styles.composerInput}
              placeholder={composerPlaceholder}
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              disabled={isStreaming || isComposerLocked}
            />
            <div className={styles.composerActions}>
              <button
                type="button"
                className={`${styles.composerButton} ${styles.composerSecondary}`}
                onClick={() => setInputValue((prev) => `${prev}${prev ? '\n' : ''}${TOOL_TIPS[0]}`)}
                disabled={isStreaming || isComposerLocked}
              >
                快捷提示
              </button>
              <button
                type="button"
                className={`${styles.composerButton} ${styles.composerPrimary} ${isStreaming ? styles.composerButtonLoading : ''}`}
                onClick={handleSend}
                disabled={!inputValue.trim() || isStreaming || isComposerLocked}
              >
                {isStreaming ? '生成中' : '发送'}
              </button>
            </div>
          </div>
          <div className={styles.statusBar}>
            {isStreaming ? (
              <span className={styles.statusBarStreaming}>
                <span className={styles.progressDots}>
                  <span className={styles.progressDot} />
                  <span className={styles.progressDot} />
                  <span className={styles.progressDot} />
                </span>
                <span>Agent 正在生成回复，请稍候...</span>
              </span>
            ) : (
              <span>{statusText}</span>
            )}
            <span>当前会话：{activeSessionId ? activeSessionId.slice(0, 8) : '未选择'}</span>
          </div>
        </footer>
      </main>

      <aside className={styles.contextPanel}>
        <section className={styles.contextSection}>
          <div className={styles.contextTitle}>Agent 配置</div>
          <div className={styles.contextItem}>
            <span>系统 Prompt</span>
            <span className={styles.contextBadge}>{hasSelectedAgent ? context?.system_prompt_path ?? '未配置' : '请选择 Agent'}</span>
          </div>
          <div className={styles.contextItem}>
            <span>代码目录</span>
            <span className={styles.contextBadge}>{hasSelectedAgent ? context?.code_path ?? '未配置' : '请选择 Agent'}</span>
          </div>
          <div className={styles.contextItem}>
            <span>工具目录</span>
            <span className={styles.contextBadge}>{hasSelectedAgent ? context?.tools_path ?? '未配置' : '请选择 Agent'}</span>
          </div>
        </section>

        <section className={styles.contextSection}>
          <div className={styles.contextTitle}>说明</div>
          <div className={styles.contextItem}>{contextDescription}</div>
        </section>

        <section className={styles.contextSection}>
          <div className={styles.contextTitle}>标签</div>
          <div className={styles.tagList}>
            {contextTags.map((tag) => (
              <span key={tag} className={styles.tagChip}>
                #{tag}
              </span>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}
