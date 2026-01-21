'use client';

import { useState, useRef, useEffect, useCallback, useMemo, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, Button, Badge, Input, Empty } from '@/components/ui';
import { MessageContent } from '@components/viewer';
import { StatusBadge } from '@/components/status-badge';
import { useAgentsV2, useAgentContextV2 } from '@/hooks/use-agents-v2';
import { useAgentSessionsV2, useCreateSessionV2 } from '@/hooks/use-sessions-v2';
import { useSessionMessagesV2 } from '@/hooks/use-sessions-v2';
import { streamChat, streamChatDirect, StreamEvent } from '@/lib/api-v2';
import { formatRelativeTime, truncate } from '@/lib/utils';
import { toast } from 'sonner';
import {
  Bot,
  Send,
  Plus,
  MessageSquare,
  User,
  Loader2,
  RefreshCw,
  Wrench,
  Search,
  ChevronDown,
  X,
  Trash2,
} from 'lucide-react';

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

// Typewriter effect hook
function useTypewriter(fullText: string, isActive: boolean, baseSpeed: number = 8) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const indexRef = useRef(0);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateRef = useRef(0);

  useEffect(() => {
    if (!isActive) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      setDisplayedText(fullText);
      indexRef.current = fullText.length;
      setIsTyping(false);
      return;
    }

    if (indexRef.current < fullText.length) {
      setIsTyping(true);
      
      const animate = (timestamp: number) => {
        if (!lastUpdateRef.current) {
          lastUpdateRef.current = timestamp;
        }
        
        const elapsed = timestamp - lastUpdateRef.current;
        
        if (elapsed >= baseSpeed) {
          const currentLength = fullText.length;
          const remaining = currentLength - indexRef.current;
          
          if (remaining > 0) {
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

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return { displayedText, isTyping };
}

function TypewriterMessage({
  content,
  isStreaming,
  variant,
}: {
  content: string;
  isStreaming?: boolean;
  variant: 'user' | 'assistant';
}) {
  const { displayedText, isTyping } = useTypewriter(content, isStreaming || false, 10);

  return (
    <MessageContent
      content={displayedText}
      isStreaming={isTyping || isStreaming}
      variant={variant}
    />
  );
}


export default function ChatPage() {
  return (
    <Suspense fallback={<ChatPageLoading />}>
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageLoading() {
  return (
    <div className="page-container">
      <Header title="会话" description="与 Agent 进行对话交互" />
      <div className="page-content">
        <div className="flex items-center justify-center h-[calc(100vh-180px)]">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </div>
    </div>
  );
}

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialAgentId = searchParams.get('agent');
  const initialSessionId = searchParams.get('session');

  const { data: agents, isLoading: isLoadingAgents } = useAgentsV2({ limit: 100 });
  
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(initialAgentId);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(initialSessionId);
  const [agentSearchQuery, setAgentSearchQuery] = useState('');
  const [showAgentDropdown, setShowAgentDropdown] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentToolCall, setCurrentToolCall] = useState<{ name: string; id: string; input: string } | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 获取选中 Agent 的上下文信息（包含 AgentCore 配置）
  const { data: agentContext } = useAgentContextV2(selectedAgentId || '');

  const selectedAgent = useMemo(() => {
    return agents?.find((a) => a.agent_id === selectedAgentId) || null;
  }, [agents, selectedAgentId]);

  const filteredAgents = useMemo(() => {
    if (!agents) return [];
    if (!agentSearchQuery) return agents;
    return agents.filter((a) =>
      a.agent_name.toLowerCase().includes(agentSearchQuery.toLowerCase())
    );
  }, [agents, agentSearchQuery]);

  const { data: sessions, refetch: refetchSessions } = useAgentSessionsV2(selectedAgentId || '');
  const createSession = useCreateSessionV2();

  const { data: messages, isLoading: isLoadingMessages, refetch: refetchMessages } = useSessionMessagesV2(
    activeSessionId || '',
    100
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowAgentDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
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

  // Set initial agent and session if provided
  useEffect(() => {
    if (initialAgentId && !selectedAgentId) {
      setSelectedAgentId(initialAgentId);
    }
    if (initialSessionId && !activeSessionId) {
      setActiveSessionId(initialSessionId);
    }
  }, [initialAgentId, initialSessionId, selectedAgentId, activeSessionId]);

  // Update URL when agent or session changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedAgentId) params.set('agent', selectedAgentId);
    if (activeSessionId) params.set('session', activeSessionId);
    const newUrl = params.toString() ? `/chat?${params.toString()}` : '/chat';
    router.replace(newUrl, { scroll: false });
  }, [selectedAgentId, activeSessionId, router]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSelectAgent = useCallback((agentId: string) => {
    setSelectedAgentId(agentId);
    setActiveSessionId(null);
    setChatMessages([]);
    setShowAgentDropdown(false);
    setAgentSearchQuery('');
  }, []);

  const handleCreateSession = useCallback(async () => {
    if (!selectedAgentId) return;
    try {
      const session = await createSession.mutateAsync({
        agentId: selectedAgentId,
        title: `会话 ${new Date().toLocaleString('zh-CN')}`,
      });
      setActiveSessionId(session.session_id);
      refetchSessions();
      toast.success('新会话已创建');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建会话失败');
    }
  }, [selectedAgentId, createSession, refetchSessions]);


  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !activeSessionId || isStreaming) return;

    const content = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMessage]);

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

    // 处理流式事件的通用函数
    const handleStreamEvent = (event: StreamEvent) => {
      if (event.event === 'message') {
        if (event.type === 'text' && event.data) {
          setChatMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + event.data }
                : msg
            )
          );
        } else if (event.type === 'tool_use') {
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
          setCurrentToolCall((prev) =>
            prev ? { ...prev, input: prev.input + event.data } : null
          );
        } else if (event.type === 'tool_end') {
          setCurrentToolCall(null);
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
        setChatMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
          )
        );
      }
    };

    try {
      abortControllerRef.current = new AbortController();

      // 根据 Agent 类型选择不同的流式调用方式
      // 如果有 AgentCore Runtime ARN，使用直连方式
      if (agentContext?.agentcore_runtime_arn) {
        console.log('Using AgentCore direct streaming:', agentContext.agentcore_runtime_arn);
        
        for await (const event of streamChatDirect(
          agentContext.agentcore_runtime_arn,
          activeSessionId,
          content,
          {
            runtimeAlias: agentContext.agentcore_runtime_alias || 'DEFAULT',
            region: agentContext.agentcore_region,
          }
        )) {
          handleStreamEvent(event);
        }
      } else {
        // 本地 Agent，使用后端代理流式调用
        console.log('Using local agent streaming via backend');
        
        for await (const event of streamChat(activeSessionId, content)) {
          handleStreamEvent(event);
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      toast.error(error instanceof Error ? error.message : '发送消息失败');
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
      refetchMessages();
    }
  }, [inputValue, activeSessionId, isStreaming, refetchMessages, agentContext]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );


  return (
    <div className="page-container">
      <Header
        title="会话"
        description="与 Agent 进行对话交互"
      />

      <div className="page-content">
        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-180px)]">
          {/* Left Panel - Agent Selection & Sessions */}
          <div className="col-span-3 flex flex-col gap-4 h-full">
            {/* Agent Selector */}
            <Card padding="none" className="flex-shrink-0">
              <div className="p-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-3">
                  <Bot className="w-4 h-4" />
                  选择 Agent
                </h3>
                <div className="relative" ref={dropdownRef}>
                  <button
                    onClick={() => setShowAgentDropdown(!showAgentDropdown)}
                    className="w-full flex items-center justify-between px-3 py-2 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors text-left"
                  >
                    {selectedAgent ? (
                      <div className="flex items-center gap-2 min-w-0">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          selectedAgent.status === 'running' ? 'bg-green-500' : 'bg-gray-300'
                        }`} />
                        <span className="truncate text-sm font-medium">{selectedAgent.agent_name}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">请选择 Agent</span>
                    )}
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showAgentDropdown ? 'rotate-180' : ''}`} />
                  </button>
                  
                  {showAgentDropdown && (
                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-hidden">
                      <div className="p-2 border-b border-gray-100">
                        <div className="relative">
                          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            type="text"
                            placeholder="搜索 Agent..."
                            value={agentSearchQuery}
                            onChange={(e) => setAgentSearchQuery(e.target.value)}
                            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
                          />
                        </div>
                      </div>
                      <div className="max-h-60 overflow-auto">
                        {isLoadingAgents ? (
                          <div className="p-4 text-center text-gray-500 text-sm">
                            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                            加载中...
                          </div>
                        ) : filteredAgents.length === 0 ? (
                          <div className="p-4 text-center text-gray-500 text-sm">
                            {agentSearchQuery ? '没有找到匹配的 Agent' : '暂无可用 Agent'}
                          </div>
                        ) : (
                          filteredAgents.map((agent) => (
                            <button
                              key={agent.agent_id}
                              onClick={() => handleSelectAgent(agent.agent_id)}
                              className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 transition-colors text-left ${
                                selectedAgentId === agent.agent_id ? 'bg-primary-50' : ''
                              }`}
                            >
                              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                agent.status === 'running' ? 'bg-green-500' : 'bg-gray-300'
                              }`} />
                              <div className="min-w-0 flex-1">
                                <div className="text-sm font-medium text-gray-900 truncate">{agent.agent_name}</div>
                                {agent.category && (
                                  <div className="text-xs text-gray-500">{agent.category}</div>
                                )}
                              </div>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Sessions List */}
            <Card padding="none" className="flex-1 flex flex-col min-h-0">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  会话列表
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCreateSession}
                  disabled={!selectedAgentId || createSession.isPending}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex-1 overflow-auto divide-y divide-gray-100">
                {!selectedAgentId ? (
                  <div className="p-4 text-center text-gray-500 text-sm">
                    请先选择一个 Agent
                  </div>
                ) : !sessions || sessions.length === 0 ? (
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


          {/* Right Panel - Chat Area */}
          <div className="col-span-9 h-full">
            <Card padding="none" className="h-full flex flex-col">
              {/* Chat Header */}
              <div className="p-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
                {selectedAgent ? (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-600 flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{selectedAgent.agent_name}</div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={selectedAgent.status as any} size="sm" />
                        {selectedAgent.deployment_type && (
                          <Badge variant="outline" size="sm">
                            {selectedAgent.deployment_type === 'agentcore' ? 'AgentCore' : 'Local'}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-gray-500">请选择 Agent 开始对话</div>
                )}
                {activeSessionId && (
                  <Button variant="ghost" size="sm" onClick={() => refetchMessages()}>
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {/* Messages - Fixed height with scroll */}
              <div 
                ref={messagesContainerRef}
                className="flex-1 overflow-y-auto p-4 space-y-4"
              >
                {!selectedAgentId ? (
                  <div className="h-full flex items-center justify-center">
                    <Empty
                      icon={Bot}
                      title="选择 Agent"
                      description="从左侧选择一个 Agent 开始对话"
                    />
                  </div>
                ) : !activeSessionId ? (
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
                    开始与 {selectedAgent?.agent_name} 对话吧
                  </div>
                ) : (
                  chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {message.role !== 'user' && (
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-600 flex items-center justify-center flex-shrink-0 mt-1">
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
                <div className="p-4 border-t border-gray-100 flex-shrink-0">
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
