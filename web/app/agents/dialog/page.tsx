'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
  const [skipNextRefresh, setSkipNextRefresh] = useState(false);
  const [agentLimit, setAgentLimit] = useState(50);
  const [hasMoreAgents, setHasMoreAgents] = useState(false);

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
    enabled: Boolean(activeAgentId && activeSessionId),
    staleTime: Infinity, // 禁用自动刷新，只在切换会话时手动获取
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });

  // Handle messages data changes - 只在切换会话时加载历史消息
  useEffect(() => {
    // 流式传输中不处理
    if (isStreaming) {
      return;
    }
    // 如果刚完成流式传输，跳过这次刷新以保留本地内容
    if (skipNextRefresh) {
      setSkipNextRefresh(false);
      return;
    }
    // 只有当 messagesQuery 有数据时才更新
    if (messagesQuery.data) {
      setMessages(messagesQuery.data);
    }
  }, [messagesQuery.data, isStreaming, skipNextRefresh]);

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

  const handleSessionSwitch = (sessionId: string) => {
    if (sessionId === activeSessionId) {
      return;
    }
    setActiveSessionId(sessionId);
    setMessages([]);
    setMetrics({});
    setStreamError(null);
    setInputValue('');
    setSkipNextRefresh(false); // 切换会话时允许加载历史消息
    // 强制重新获取消息
    queryClient.invalidateQueries({ queryKey: ['dialog-messages', activeAgentId, sessionId] });
  };

  const handleAgentSwitch = (agentId: string) => {
    if (agentId === activeAgentId) {
      return;
    }
    setActiveAgentId(agentId);
    setActiveSessionId(null);
    setSessions([]);
    setMessages([]);
    setMetrics({});
    setStreamError(null);
    setInputValue('');
    setContext(null);
    setSkipNextRefresh(false); // 切换 Agent 时允许加载历史消息
  };

  const handleLoadMoreAgents = () => {
    setAgentLimit((prev) => prev + 50);
  };

  const handleSend = async () => {
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

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setStreamError(null);
    setIsStreaming(true);

    const assistantDraft = buildAssistantDraft();
    setMessages((prev) => [...prev, assistantDraft]);

    try {
      await streamAgentResponse(activeAgentId, activeSessionId, userMessage.content, assistantDraft.message_id);
      // 延迟刷新会话列表，不刷新消息（保留本地流式更新的内容）
      await queryClient.invalidateQueries({ queryKey: ['dialog-sessions', activeAgentId] });
      // 注意：不要立即刷新消息列表，否则会覆盖本地流式内容
      // 消息已经通过流式更新在本地状态中了
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
      // 设置跳过下次刷新标志，防止服务器数据覆盖本地流式内容
      setSkipNextRefresh(true);
      setIsStreaming(false);
    }
  };

  const streamAgentResponse = async (
    agentId: string,
    sessionId: string,
    message: string,
    assistantMessageId: string,
  ) => {
    const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
    const response = await fetch(
      `${baseUrl}/api/v1/agents/${encodeURIComponent(agentId)}/sessions/${encodeURIComponent(sessionId)}/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      },
    );

    if (!response.ok) {
      // 尝试解析错误信息
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
    let assistantContent = '';

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

          if (eventType === 'message') {
            const chunk = String(payload.data ?? '');
            assistantContent += chunk;
            setMessages((prev) =>
              prev.map((item) =>
                item.message_id === assistantMessageId
                  ? { ...item, content: assistantContent, metadata: { ...(item.metadata ?? {}), streaming: true } }
                  : item,
              ),
            );
          } else if (eventType === 'metrics') {
            const metricData = payload.data as StreamMetrics;
            setMetrics(metricData);
            setMessages((prev) =>
              prev.map((item) =>
                item.message_id === assistantMessageId ? { ...item, metadata: { ...(item.metadata ?? {}), metrics: metricData } } : item,
              ),
            );
          } else if (eventType === 'error') {
            throw new Error(String(payload.error ?? 'Agent Runtime Error'));
          }
        } catch (error) {
          console.warn('Failed to parse stream event', error);
        }
      }
    }

    setMessages((prev) =>
      prev.map((item) =>
        item.message_id === assistantMessageId
          ? { ...item, content: assistantContent || item.content, metadata: { ...(item.metadata ?? {}), streaming: false } }
          : item,
      ),
    );
  };

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

        <section className={styles.messageList}>
          {streamError ? <div className={styles.errorBanner}>{streamError}</div> : null}
          {messages.map((message) => (
            <div key={message.message_id} className={styles.messageRow}>
              <div
                className={`${styles.messageBubble} ${message.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant}`}
              >
                <div dangerouslySetInnerHTML={{ __html: message.content.replace(/\n/g, '<br/>') }} />
              </div>
              <div className={styles.messageMeta}>
                {message.role === 'user' ? '我' : 'Agent'} · {new Date(message.created_at).toLocaleTimeString()}
              </div>
              {message.metadata && typeof message.metadata.tool === 'string' ? (
                <div className={styles.toolCard}>
                  <div className={styles.toolTitle}>工具调用：{message.metadata.tool}</div>
                  <div>{JSON.stringify(message.metadata.result)}</div>
                </div>
              ) : null}
            </div>
          ))}
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
                className={`${styles.composerButton} ${styles.composerPrimary}`}
                onClick={handleSend}
                disabled={!inputValue.trim() || isStreaming || isComposerLocked}
              >
                {isStreaming ? '生成中…' : '发送'}
              </button>
            </div>
          </div>
          <div className={styles.statusBar}>
            <span>{statusText}</span>
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
