'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, Button, Badge, Empty } from '@/components/ui';
import { MessageContent } from '@components/viewer';
import { StatusBadge } from '@/components/status-badge';
import { useAgentDetailV2, useAgentSessionsV2, useCreateSessionV2 } from '@/hooks/use-agents-v2';
import { useSessionMessagesV2 } from '@/hooks/use-sessions-v2';
import { streamChat, type StreamEvent } from '@/lib/api-v2';
import { formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Bot,
  Send,
  Plus,
  MessageSquare,
  User,
  Loader2,
  RefreshCw,
  Wrench,
} from 'lucide-react';

interface PageProps {
  params: { id: string };
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  toolCalls?: Array<{
    name: string;
    id: string;
    input?: string;
  }>;
}

// 打字机效果 Hook - 实现类似 ChatGPT 的流畅打字效果
function useTypewriter(
  fullText: string,
  isActive: boolean,
  baseSpeed: number = 8 // 基础速度（毫秒/字符）
) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const indexRef = useRef(0);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateRef = useRef(0);

  useEffect(() => {
    if (!isActive) {
      // 流式结束，直接显示全部文本
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      setDisplayedText(fullText);
      indexRef.current = fullText.length;
      setIsTyping(false);
      return;
    }

    // 如果有未显示的内容，启动打字机效果
    if (indexRef.current < fullText.length) {
      setIsTyping(true);
      
      const animate = (timestamp: number) => {
        if (!lastUpdateRef.current) {
          lastUpdateRef.current = timestamp;
        }
        
        const elapsed = timestamp - lastUpdateRef.current;
        
        // 根据时间间隔决定显示多少字符
        if (elapsed >= baseSpeed) {
          const currentLength = fullText.length;
          const remaining = currentLength - indexRef.current;
          
          if (remaining > 0) {
            // 动态调整速度：积压越多，显示越快
            let charsToAdd = 1;
            if (remaining > 50) {
              charsToAdd = Math.min(5, Math.ceil(remaining / 20));
            } else if (remaining > 20) {
              charsToAdd = 3;
            } else if (remaining > 10) {
              charsToAdd = 2;
            }
            
            indexRef.current = Math.min(indexRef.current + charsToAdd, currentLength);
            setDisplayedText(fullText.slice(0, indexRef.current));
            lastUpdateRef.current = timestamp;
          }
        }
        
        // 继续动画
        if (indexRef.current < fullText.length || isActive) {
          animationFrameRef.current = requestAnimationFrame(animate);
        } else {
          setIsTyping(false);
        }
      };
      
      animationFrameRef.current = requestAnimationFrame(animate);
      
      return () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = null;
        }
      };
    }
  }, [fullText, isActive, baseSpeed]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return { displayedText, isTyping };
}

// 带打字机效果的消息组件
function TypewriterMessage({
  content,
  isStreaming,
  variant,
}: {
  content: string;
  isStreaming?: boolean;
  variant: 'user' | 'assistant';
}) {
  const { displayedText, isTyping } = useTypewriter(
    content,
    isStreaming || false,
    10 // 打字速度（毫秒/字符）
  );

  return (
    <MessageContent
      content={displayedText}
      isStreaming={isTyping || isStreaming}
      variant={variant}
    />
  );
}

export default function AgentChatPage({ params }: PageProps) {
  const { id: agentId } = params;
  const searchParams = useSearchParams();
  const initialSessionId = searchParams.get('session');

  const { data: agent, isLoading: isLoadingAgent } = useAgentDetailV2(agentId);
  const { data: sessions, refetch: refetchSessions } = useAgentSessionsV2(agentId, 20);
  const createSession = useCreateSessionV2();

  const [activeSessionId, setActiveSessionId] = useState<string | null>(initialSessionId);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentToolCall, setCurrentToolCall] = useState<{ name: string; id: string; input: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const { data: messages, isLoading: isLoadingMessages, refetch: refetchMessages } = useSessionMessagesV2(
    activeSessionId || '',
    100
  );

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Sync database messages to chat messages when session changes
  useEffect(() => {
    if (messages && messages.length > 0) {
      const dbMessages: ChatMessage[] = messages.map((msg) => ({
        id: msg.message_id,
        role: msg.role as 'user' | 'assistant' | 'system',
        content: msg.content,
        timestamp: msg.created_at,
      }));
      setChatMessages(dbMessages);
    } else {
      setChatMessages([]);
    }
  }, [messages]);

  // Set initial session if provided
  useEffect(() => {
    if (initialSessionId && !activeSessionId) {
      setActiveSessionId(initialSessionId);
    }
  }, [initialSessionId, activeSessionId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleCreateSession = useCallback(async () => {
    try {
      const session = await createSession.mutateAsync({
        agentId,
        displayName: `会话 ${new Date().toLocaleString('zh-CN')}`,
      });
      setActiveSessionId(session.session_id);
      refetchSessions();
      toast.success('新会话已创建');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建会话失败');
    }
  }, [agentId, createSession, refetchSessions]);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !activeSessionId || isStreaming) return;

    const content = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);

    // Add user message to chat
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMessage]);

    // Add placeholder for assistant message
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      toolCalls: [],
    };
    setChatMessages((prev) => [...prev, assistantMessage]);

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      // Use streaming chat
      for await (const event of streamChat(activeSessionId, content)) {
        if (event.event === 'message') {
          if (event.type === 'text' && event.data) {
            // Append text to assistant message
            setChatMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + event.data }
                  : msg
              )
            );
          } else if (event.type === 'tool_use') {
            // Track tool call
            setCurrentToolCall({
              name: event.tool_name || 'unknown',
              id: event.tool_id || '',
              input: '',
            });
            setChatMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      toolCalls: [
                        ...(msg.toolCalls || []),
                        { name: event.tool_name || 'unknown', id: event.tool_id || '' },
                      ],
                    }
                  : msg
              )
            );
          } else if (event.type === 'tool_input' && event.data) {
            // Accumulate tool input
            setCurrentToolCall((prev) =>
              prev ? { ...prev, input: prev.input + event.data } : null
            );
          } else if (event.type === 'tool_end') {
            // Tool call completed - Agent may continue with more text
            setCurrentToolCall(null);
          } else if (event.type === 'message_stop') {
            // Message stop - Agent may continue with another loop iteration
            // Don't mark as complete yet, wait for 'done' event
          }
        } else if (event.event === 'error') {
          toast.error(event.error || '对话出错');
          setChatMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content || `错误: ${event.error}`, isStreaming: false }
                : msg
            )
          );
        } else if (event.event === 'done') {
          // Mark streaming as complete
          setChatMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
            )
          );
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      toast.error(error instanceof Error ? error.message : '发送消息失败');
      // Update assistant message with error
      setChatMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: msg.content || '发送失败，请重试', isStreaming: false }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
      setCurrentToolCall(null);
      abortControllerRef.current = null;
      // Refresh messages from database
      refetchMessages();
    }
  }, [inputValue, activeSessionId, isStreaming, refetchMessages]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  if (isLoadingAgent) {
    return (
      <div className="page-container">
        <Header title="加载中..." />
        <div className="page-content">
          <div className="animate-pulse h-96 bg-gray-100 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="page-container">
        <Header title="Agent 对话" />
        <div className="page-content">
          <Empty
            icon={Bot}
            title="Agent 不存在"
            description="该 Agent 可能已被删除或您没有访问权限"
            action={
              <Link href="/agents">
                <Button variant="outline">
                  <ArrowLeft className="w-4 h-4" />
                  返回列表
                </Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <Header
        title={`与 ${agent.agent_name} 对话`}
        description={agent.description || 'AI Agent 对话'}
        actions={
          <div className="flex items-center gap-3">
            <Link href={`/agents/${agentId}`}>
              <Button variant="ghost">
                <ArrowLeft className="w-4 h-4" />
                返回详情
              </Button>
            </Link>
          </div>
        }
      />

      <div className="page-content">
        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-200px)]">
          {/* Sessions Sidebar */}
          <div className="col-span-3">
            <Card padding="none" className="h-full flex flex-col">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  会话列表
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCreateSession}
                  disabled={createSession.isPending}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex-1 overflow-auto divide-y divide-gray-100">
                {!sessions || sessions.length === 0 ? (
                  <div className="p-4 text-center text-gray-500 text-sm">
                    暂无会话
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2 w-full"
                      onClick={handleCreateSession}
                      disabled={createSession.isPending}
                    >
                      <Plus className="w-4 h-4" />
                      创建新会话
                    </Button>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <button
                      key={session.session_id}
                      onClick={() => setActiveSessionId(session.session_id)}
                      className={`w-full text-left p-4 transition-colors ${
                        activeSessionId === session.session_id
                          ? 'bg-primary-50 border-l-2 border-primary-500'
                          : 'hover:bg-gray-50 border-l-2 border-transparent'
                      }`}
                    >
                      <div className="font-medium text-gray-900 truncate text-sm">
                        {session.display_name || session.session_id.slice(0, 12)}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {formatRelativeTime(session.last_active_at || session.created_at)}
                        {session.message_count > 0 && (
                          <span className="ml-2">· {session.message_count} 条消息</span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Chat Area */}
          <div className="col-span-9">
            <Card padding="none" className="h-full flex flex-col">
              {/* Chat Header */}
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{agent.agent_name}</div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={agent.status} size="sm" />
                      {agent.deployment_type && (
                        <Badge variant="outline" size="sm">
                          {agent.deployment_type === 'agentcore' ? 'AgentCore' : 'Local'}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                {activeSessionId && (
                  <Button variant="ghost" size="sm" onClick={() => refetchMessages()}>
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-auto p-4 space-y-4">
                {!activeSessionId ? (
                  <div className="h-full flex items-center justify-center">
                    <Empty
                      icon={MessageSquare}
                      title="选择或创建会话"
                      description="从左侧选择一个会话，或创建新会话开始对话"
                      action={
                        <Button onClick={handleCreateSession} disabled={createSession.isPending}>
                          <Plus className="w-4 h-4" />
                          创建新会话
                        </Button>
                      }
                    />
                  </div>
                ) : isLoadingMessages ? (
                  <div className="h-full flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                  </div>
                ) : chatMessages.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-gray-500">
                    开始与 {agent.agent_name} 对话吧
                  </div>
                ) : (
                  chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {message.role !== 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0 mt-1">
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                      )}
                      <div
                        className={`max-w-[75%] rounded-2xl ${
                          message.role === 'user'
                            ? 'bg-primary-500 text-white px-4 py-3'
                            : 'bg-gray-50 border border-gray-100 px-4 py-3'
                        }`}
                      >
                        {/* Tool calls indicator */}
                        {message.toolCalls && message.toolCalls.length > 0 && (
                          <div className="mb-2 space-y-1">
                            {message.toolCalls.map((tool, idx) => (
                              <div
                                key={idx}
                                className="flex items-center gap-2 text-xs text-gray-500 bg-gray-200 rounded px-2 py-1"
                              >
                                <Wrench className="w-3 h-3" />
                                <span>调用工具: {tool.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {message.role === 'assistant' && message.isStreaming ? (
                          <TypewriterMessage
                            content={message.content}
                            isStreaming={message.isStreaming}
                            variant="assistant"
                          />
                        ) : (
                          <MessageContent
                            content={message.content}
                            isStreaming={false}
                            variant={message.role === 'user' ? 'user' : 'assistant'}
                          />
                        )}
                        <div
                          className={`text-xs mt-2 ${
                            message.role === 'user' ? 'text-primary-100' : 'text-gray-400'
                          }`}
                        >
                          {formatRelativeTime(message.timestamp)}
                        </div>
                      </div>
                      {message.role === 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center flex-shrink-0 mt-1">
                          <User className="w-4 h-4 text-gray-600" />
                        </div>
                      )}
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              {activeSessionId && (
                <div className="p-4 border-t border-gray-100">
                  {/* Current tool call indicator */}
                  {currentToolCall && (
                    <div className="mb-2 flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>正在执行工具: {currentToolCall.name}</span>
                    </div>
                  )}
                  <div className="flex gap-3">
                    <textarea
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="输入消息..."
                      className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
                      rows={1}
                      disabled={isStreaming}
                    />
                    <Button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isStreaming}
                      loading={isStreaming}
                    >
                      <Send className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
