'use client';

import { useState, useRef, useEffect, useCallback, useMemo, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, Button, Badge, Input, Empty } from '@/components/ui';
import { MessageContent } from '@components/viewer';
import { StatusBadge } from '@/components/status-badge';
import { useAgentsV2, useAgentContextV2 } from '@/hooks/use-agents-v2';
import { useAgentSessionsV2, useCreateSessionV2, useDeleteSessionV2 } from '@/hooks/use-sessions-v2';
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
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Code,
} from 'lucide-react';

// 工具调用状态
type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

// 工具调用信息
interface ToolCallInfo {
  name: string;
  id: string;
  input: string;
  result?: string;
  status: ToolCallStatus;
}

// 内容块类型 - 用于保持文本和工具调用的顺序
type ContentBlockType = 'text' | 'tool';

interface ContentBlock {
  type: ContentBlockType;
  id: string;
  // 文本块
  text?: string;
  // 工具块
  toolCall?: ToolCallInfo;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;  // 保留用于兼容性（用户消息和数据库加载）
  timestamp: string;
  isStreaming?: boolean;
  toolCalls?: ToolCallInfo[];  // 保留用于兼容性（数据库加载）
  // 新增：有序内容块数组，用于保持文本和工具调用的交替顺序
  contentBlocks?: ContentBlock[];
}

// 工具调用卡片组件
function ToolCallCard({ toolCall, isExpanded, onToggle }: { 
  toolCall: ToolCallInfo; 
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const statusConfig = {
    pending: { icon: Loader2, color: 'text-gray-400', bg: 'bg-gray-50', label: '等待中' },
    running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50', label: '执行中' },
    success: { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50', label: '完成' },
    error: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50', label: '失败' },
  };
  
  const config = statusConfig[toolCall.status];
  const StatusIcon = config.icon;
  
  // 尝试格式化 JSON 输入
  const formatInput = (input: string) => {
    try {
      const parsed = JSON.parse(input);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return input;
    }
  };
  
  // 截断结果显示
  const truncateResult = (result: string, maxLength: number = 500) => {
    if (result.length <= maxLength) return result;
    return result.slice(0, maxLength) + '...';
  };

  return (
    <div className={`rounded-lg border ${config.bg} border-gray-200 overflow-hidden my-2`}>
      {/* 工具调用头部 */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-100/50 transition-colors"
      >
        <StatusIcon className={`w-4 h-4 ${config.color} ${toolCall.status === 'running' ? 'animate-spin' : ''}`} />
        <Wrench className="w-3.5 h-3.5 text-gray-500" />
        <span className="text-sm font-medium text-gray-700 flex-1 text-left truncate">
          {toolCall.name}
        </span>
        <span className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
          {config.label}
        </span>
        <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
      </button>
      
      {/* 展开的详情 */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-white">
          {/* 输入参数 */}
          {toolCall.input && (
            <div className="p-3 border-b border-gray-100">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1.5">
                <Code className="w-3 h-3" />
                <span>输入参数</span>
              </div>
              <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto text-gray-700 max-h-40 overflow-y-auto">
                {formatInput(toolCall.input)}
              </pre>
            </div>
          )}
          
          {/* 执行结果 */}
          {toolCall.result && (
            <div className="p-3">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1.5">
                <CheckCircle2 className="w-3 h-3" />
                <span>执行结果</span>
              </div>
              <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto text-gray-700 max-h-60 overflow-y-auto whitespace-pre-wrap break-words">
                {truncateResult(toolCall.result)}
              </pre>
            </div>
          )}
          
          {/* 执行中状态 */}
          {toolCall.status === 'running' && !toolCall.result && (
            <div className="p-3 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>正在执行...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// 工具调用列表组件
function ToolCallsList({ toolCalls }: { toolCalls: ToolCallInfo[] }) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  
  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  
  if (!toolCalls || toolCalls.length === 0) return null;
  
  return (
    <div className="space-y-1">
      {toolCalls.map((tool) => (
        <ToolCallCard
          key={tool.id}
          toolCall={tool}
          isExpanded={expandedIds.has(tool.id)}
          onToggle={() => toggleExpand(tool.id)}
        />
      ))}
    </div>
  );
}

// 内容块列表组件 - 按顺序渲染文本和工具调用
function ContentBlocksList({ 
  blocks, 
  isStreaming 
}: { 
  blocks: ContentBlock[]; 
  isStreaming?: boolean;
}) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  
  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  
  // 调试日志：查看 blocks 的内容
  console.log('[ContentBlocksList] Rendering blocks:', blocks?.length, blocks?.map(b => ({ type: b.type, id: b.id, hasText: !!b.text, textLen: b.text?.length })));
  
  if (!blocks || blocks.length === 0) return null;
  
  return (
    <>
      {blocks.map((block, blockIndex) => {
        if (block.type === 'text' && block.text) {
          // 判断是否是最后一个文本块且正在流式输出
          const isLastTextBlock = blocks
            .slice(blockIndex + 1)
            .every(b => b.type !== 'text');
          const shouldStream = isStreaming && isLastTextBlock;
          
          return (
            <div key={block.id} className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3">
              {shouldStream ? (
                <TypewriterMessage
                  content={block.text}
                  isStreaming={true}
                  variant="assistant"
                />
              ) : (
                <MessageContent
                  content={block.text}
                  isStreaming={false}
                  variant="assistant"
                />
              )}
            </div>
          );
        } else if (block.type === 'tool' && block.toolCall) {
          return (
            <ToolCallCard
              key={block.id}
              toolCall={block.toolCall}
              isExpanded={expandedIds.has(block.id)}
              onToggle={() => toggleExpand(block.id)}
            />
          );
        }
        return null;
      })}
    </>
  );
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
  // 使用 ref 跟踪当前工具调用 ID，避免 useCallback 依赖问题
  const currentToolCallIdRef = useRef<string | null>(null);
  // 使用 ref 跟踪当前文本块 ID 和工具调用结束状态，确保在异步事件处理中保持同步
  const currentTextBlockIdRef = useRef<string | null>(null);
  const justEndedToolCallRef = useRef<boolean>(false);
  // 使用 ref 同步跟踪 contentBlocks，避免 React 状态更新的竞态条件
  const contentBlocksRef = useRef<ContentBlock[]>([]);
  const toolCallsRef = useRef<ToolCallInfo[]>([]);
  const messageContentRef = useRef<string>('');

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
  const deleteSession = useDeleteSessionV2();
  
  // 删除会话相关状态
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  // 消息存储优化：禁用自动轮询，只在会话切换时从数据库加载
  // 聊天过程中的消息存储在组件状态中，流式结束后延迟同步
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

  // 消息同步：只在会话切换时从数据库加载消息
  // 流式输出过程中的消息保存在组件状态中，不会被数据库消息覆盖
  // 使用 Map 存储流式消息的 contentBlocks，key 为消息内容的前100字符哈希
  const streamContentBlocksMapRef = useRef<Map<string, ContentBlock[]>>(new Map());
  // 跟踪是否刚完成流式输出，用于决定是否跳过数据库同步
  const justFinishedStreamingRef = useRef<boolean>(false);
  // 跟踪当前流式消息的 ID，用于在同步时保护该消息
  const streamingMessageIdRef = useRef<string | null>(null);
  
  useEffect(() => {
    // 流式输出时完全不同步数据库消息，避免覆盖正在显示的内容
    if (isStreaming) {
      return;
    }
    
    // 如果刚完成流式输出，跳过这次同步，保留流式消息的 contentBlocks
    if (justFinishedStreamingRef.current) {
      justFinishedStreamingRef.current = false;
      return;
    }
    
    if (messages && messages.length > 0) {
      setChatMessages((prevMessages) => {
        // 如果有正在流式输出的消息，保护它不被覆盖
        const streamingMsgId = streamingMessageIdRef.current;
        const streamingMsg = streamingMsgId ? prevMessages.find(m => m.id === streamingMsgId) : null;
        
        // 收集当前所有有 contentBlocks 的流式消息
        prevMessages.forEach(m => {
          if (m.contentBlocks && m.contentBlocks.length > 0 && m.content) {
            // 使用内容前100字符作为 key
            const contentKey = m.content.slice(0, 100);
            streamContentBlocksMapRef.current.set(contentKey, m.contentBlocks);
          }
        });
        
        // 从数据库消息构建新的消息列表
        const dbMessages: ChatMessage[] = messages.map((msg) => {
          const toolCalls = msg.metadata?.tool_calls as ToolCallInfo[] | undefined;
          // 从数据库 metadata 中获取 content_blocks
          const dbContentBlocks = msg.metadata?.content_blocks as ContentBlock[] | undefined;
          
          const baseMsg: ChatMessage = {
            id: msg.message_id,
            role: msg.role as 'user' | 'assistant' | 'system',
            content: msg.content,
            timestamp: msg.created_at,
            toolCalls: toolCalls?.map(tc => ({
              name: tc.name,
              id: tc.id,
              input: tc.input || '',
              result: tc.result,
              status: (tc.status || 'success') as ToolCallStatus,
            })),
          };
          
          // 尝试恢复 contentBlocks
          if (msg.role === 'assistant') {
            // 优先从缓存中恢复（流式输出的完整数据）
            if (msg.content) {
              const contentKey = msg.content.slice(0, 100);
              const cachedBlocks = streamContentBlocksMapRef.current.get(contentKey);
              if (cachedBlocks && cachedBlocks.length > 0) {
                baseMsg.contentBlocks = cachedBlocks;
              }
            }
            
            // 如果缓存中没有，从数据库 metadata 恢复
            if (!baseMsg.contentBlocks && dbContentBlocks && dbContentBlocks.length > 0) {
              // 重建完整的 contentBlocks，合并 toolCalls 的完整数据
              const rebuiltBlocks: ContentBlock[] = dbContentBlocks.map(block => {
                if (block.type === 'tool') {
                  // 从 toolCalls 中找到对应的完整工具调用数据
                  const fullToolCall = baseMsg.toolCalls?.find(tc => tc.id === block.id);
                  if (fullToolCall) {
                    return {
                      type: 'tool' as ContentBlockType,
                      id: block.id,
                      toolCall: fullToolCall,
                    };
                  }
                }
                return block;
              });
              baseMsg.contentBlocks = rebuiltBlocks;
            }
          }
          
          return baseMsg;
        });
        
        // 如果有正在流式输出的消息，将其添加回列表末尾
        if (streamingMsg && streamingMsg.isStreaming) {
          // 检查数据库消息中是否已有该消息（通过内容匹配）
          const existsInDb = dbMessages.some(m => 
            m.role === 'assistant' && 
            m.content && 
            streamingMsg.content && 
            m.content.startsWith(streamingMsg.content.slice(0, 50))
          );
          
          if (!existsInDb) {
            dbMessages.push(streamingMsg);
          }
        }
        
        return dbMessages;
      });
    } else {
      setChatMessages([]);
    }
  }, [messages, isStreaming]);

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

  // 删除会话处理函数
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession.mutateAsync(sessionId);
      // 如果删除的是当前活动会话，清空选择
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setChatMessages([]);
      }
      refetchSessions();
      toast.success('会话已删除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除会话失败');
    } finally {
      setSessionToDelete(null);
    }
  }, [activeSessionId, deleteSession, refetchSessions]);


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
      contentBlocks: [],  // 初始化有序内容块数组
    };
    setChatMessages((prev) => [...prev, assistantMessage]);

    // 重置 ref 状态
    currentTextBlockIdRef.current = null;
    justEndedToolCallRef.current = false;
    // 重置内容跟踪 ref
    contentBlocksRef.current = [];
    toolCallsRef.current = [];
    messageContentRef.current = '';
    // 记录当前流式消息 ID，用于保护该消息不被数据库同步覆盖
    streamingMessageIdRef.current = assistantMessageId;

    // 处理流式事件的通用函数
    const handleStreamEvent = (event: StreamEvent) => {
      // 调试日志
      console.log('[handleStreamEvent] Received event:', event.event, event.type, event.data?.slice(0, 50));
      
      if (event.event === 'message') {
        if (event.type === 'text' && event.data) {
          // 使用 ref 同步更新，避免 React 状态竞态条件
          messageContentRef.current += event.data;
          
          // 如果刚结束工具调用或没有当前文本块，创建新的文本块
          if (justEndedToolCallRef.current || !currentTextBlockIdRef.current) {
            const newBlockId = `text-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            currentTextBlockIdRef.current = newBlockId;
            justEndedToolCallRef.current = false;
            
            const newBlock: ContentBlock = {
              type: 'text',
              id: newBlockId,
              text: event.data,
            };
            
            // 同步更新 ref - 这是关键！
            const prevLength = contentBlocksRef.current.length;
            contentBlocksRef.current = [...contentBlocksRef.current, newBlock];
            console.log('[handleStreamEvent] Creating new text block:', newBlockId, 'blocks before:', prevLength, 'blocks after:', contentBlocksRef.current.length);
          } else {
            // 追加到现有文本块
            const targetBlockId = currentTextBlockIdRef.current;
            contentBlocksRef.current = contentBlocksRef.current.map(block =>
              block.id === targetBlockId && block.type === 'text'
                ? { ...block, text: (block.text || '') + event.data }
                : block
            );
          }
          
          // 更新 React 状态以触发渲染
          setChatMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMessageId) return msg;
              return {
                ...msg,
                content: messageContentRef.current,
                contentBlocks: [...contentBlocksRef.current],
              };
            })
          );
        } else if (event.type === 'tool_use') {
          // 工具调用开始 - 使用 tool_id 作为唯一标识
          const toolId = event.tool_id || `tool-${Date.now()}`;
          const toolName = event.tool_name || 'unknown';
          
          console.log('[handleStreamEvent] tool_use event, toolId:', toolId, 'toolName:', toolName, 'currentTextBlockId:', currentTextBlockIdRef.current);
          
          // 重置当前文本块，下次文本会创建新块
          currentTextBlockIdRef.current = null;
          
          // 更新 ref 和 state
          currentToolCallIdRef.current = toolId;
          setCurrentToolCall({
            name: toolName,
            id: toolId,
            input: '',
          });
          
          // 检查是否已存在相同 tool_id 的工具调用
          const existingIndex = toolCallsRef.current.findIndex(tc => tc.id === toolId);
          if (existingIndex >= 0) {
            // 已存在，不重复添加
            return;
          }
          
          // 添加新的工具调用到 ref
          const newToolCall: ToolCallInfo = {
            name: toolName,
            id: toolId,
            input: '',
            status: 'running',
          };
          toolCallsRef.current = [...toolCallsRef.current, newToolCall];
          
          // 添加工具块到 contentBlocks ref
          const newBlock: ContentBlock = {
            type: 'tool',
            id: toolId,
            toolCall: newToolCall,
          };
          contentBlocksRef.current = [...contentBlocksRef.current, newBlock];
          
          console.log('[handleStreamEvent] Adding tool block, existing blocks:', contentBlocksRef.current.length - 1, contentBlocksRef.current.map(b => ({ type: b.type, id: b.id })));
          
          // 更新 React 状态
          setChatMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMessageId) return msg;
              return {
                ...msg,
                toolCalls: [...toolCallsRef.current],
                contentBlocks: [...contentBlocksRef.current],
              };
            })
          );
        } else if (event.type === 'tool_input' && event.data) {
          // 工具输入增量 - 使用 ref 同步更新
          const targetId = event.tool_id || currentToolCallIdRef.current;
          
          setCurrentToolCall((prev) =>
            prev ? { ...prev, input: prev.input + event.data } : null
          );
          
          // 更新 ref 中的 toolCalls
          toolCallsRef.current = toolCallsRef.current.map(tc =>
            (targetId && tc.id === targetId) || (!targetId && tc.status === 'running')
              ? { ...tc, input: tc.input + event.data }
              : tc
          );
          
          // 更新 ref 中的 contentBlocks
          contentBlocksRef.current = contentBlocksRef.current.map(block => {
            if (block.type === 'tool' && block.toolCall) {
              const isTarget = (targetId && block.id === targetId) || 
                               (!targetId && block.toolCall.status === 'running');
              if (isTarget) {
                return {
                  ...block,
                  toolCall: { ...block.toolCall, input: block.toolCall.input + event.data },
                };
              }
            }
            return block;
          });
          
          // 更新 React 状态
          setChatMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMessageId) return msg;
              return {
                ...msg,
                toolCalls: [...toolCallsRef.current],
                contentBlocks: [...contentBlocksRef.current],
              };
            })
          );
        } else if (event.type === 'tool_end') {
          // 工具调用结束 - 使用 ref 同步更新
          const toolResult = event.tool_result || event.tool_input || '';
          const targetToolId = event.tool_id || currentToolCallIdRef.current;
          
          // 标记刚结束工具调用，下次文本需要创建新块
          justEndedToolCallRef.current = true;
          
          // 更新 ref 中的 toolCalls
          toolCallsRef.current = toolCallsRef.current.map(tc => {
            if (targetToolId && tc.id === targetToolId) {
              return {
                ...tc,
                status: 'success' as ToolCallStatus,
                result: toolResult,
                input: event.tool_input || tc.input,
              };
            }
            return tc;
          });
          
          // 更新 ref 中的 contentBlocks
          contentBlocksRef.current = contentBlocksRef.current.map(block => {
            if (block.type === 'tool' && block.toolCall && targetToolId && block.id === targetToolId) {
              return {
                ...block,
                toolCall: {
                  ...block.toolCall,
                  status: 'success' as ToolCallStatus,
                  result: toolResult,
                  input: event.tool_input || block.toolCall.input,
                },
              };
            }
            return block;
          });
          
          // 更新 React 状态
          setChatMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMessageId) return msg;
              return {
                ...msg,
                toolCalls: [...toolCallsRef.current],
                contentBlocks: [...contentBlocksRef.current],
              };
            })
          );
          
          // 清空工具调用状态
          currentToolCallIdRef.current = null;
          setCurrentToolCall(null);
        }
      } else if (event.event === 'error') {
        toast.error(event.error || '对话出错');
        // 如果有正在执行的工具调用，标记为失败
        // 更新 ref
        toolCallsRef.current = toolCallsRef.current.map((tc) =>
          tc.status === 'running' ? { ...tc, status: 'error' as ToolCallStatus, result: event.error } : tc
        );
        contentBlocksRef.current = contentBlocksRef.current.map(block => {
          if (block.type === 'tool' && block.toolCall && block.toolCall.status === 'running') {
            return {
              ...block,
              toolCall: { ...block.toolCall, status: 'error' as ToolCallStatus, result: event.error },
            };
          }
          return block;
        });
        
        setChatMessages((prev) =>
          prev.map((msg) => {
            if (msg.id !== assistantMessageId) return msg;
            return {
              ...msg,
              content: messageContentRef.current || `错误: ${event.error}`,
              isStreaming: false,
              toolCalls: [...toolCallsRef.current],
              contentBlocks: [...contentBlocksRef.current],
            };
          })
        );
      } else if (event.event === 'done') {
        console.log('[handleStreamEvent] Stream done, finalizing message');
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
      // 清空工具调用状态和文本块跟踪状态
      currentToolCallIdRef.current = null;
      currentTextBlockIdRef.current = null;
      justEndedToolCallRef.current = false;
      setCurrentToolCall(null);
      abortControllerRef.current = null;
      
      // 标记刚完成流式输出，跳过下一次数据库同步
      justFinishedStreamingRef.current = true;
      
      // 延迟刷新消息，给足够时间让 contentBlocks 被缓存
      // 第一次 refetch 会被 justFinishedStreamingRef 跳过
      // 第二次 refetch 会从缓存中恢复 contentBlocks
      setTimeout(() => {
        refetchMessages();
      }, 1000);
    }
  }, [inputValue, activeSessionId, isStreaming, refetchMessages, agentContext]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Shift+Enter 发送消息，单独 Enter 换行
      if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );


  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        title="会话"
        description="与 Agent 进行对话交互"
      />

      <div className="flex-1 p-6 overflow-hidden">
        <div className="grid grid-cols-12 gap-6 h-full">
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
                    <div
                      key={session.session_id}
                      className={`relative flex items-center justify-between w-full text-left p-4 transition-colors ${
                        activeSessionId === session.session_id
                          ? 'bg-primary-50 border-l-2 border-primary-500'
                          : 'hover:bg-gray-50 border-l-2 border-transparent'
                      }`}
                    >
                      <button
                        onClick={() => setActiveSessionId(session.session_id)}
                        className="flex-1 text-left min-w-0"
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
                      {/* 删除按钮 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSessionToDelete(session.session_id);
                        }}
                        className="flex-shrink-0 ml-2 p-1.5 rounded-md text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors"
                        title="删除会话"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>


          {/* Right Panel - Chat Area */}
          <div className="col-span-9 h-full min-h-0">
            <Card padding="none" className="h-full flex flex-col min-h-0">
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
                className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4"
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
                        className={`max-w-[75%] ${
                          message.role === 'user'
                            ? 'bg-primary-500 text-white rounded-2xl px-4 py-3'
                            : ''
                        }`}
                      >
                        {/* 用户消息 */}
                        {message.role === 'user' && (
                          <>
                            <MessageContent
                              content={message.content}
                              isStreaming={false}
                              variant="user"
                            />
                            <div className="text-xs mt-2 text-primary-100">
                              {formatRelativeTime(message.timestamp)}
                            </div>
                          </>
                        )}
                        
                        {/* 助手消息 */}
                        {message.role === 'assistant' && (
                          <div className="space-y-2">
                            {/* 思考中状态 - 流式输出但还没有内容和工具调用时显示 */}
                            {message.isStreaming && !message.content && (!message.contentBlocks || message.contentBlocks.length === 0) && (
                              <div className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3">
                                <div className="flex items-center gap-2 text-gray-500">
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  <span className="text-sm">思考中...</span>
                                </div>
                              </div>
                            )}
                            
                            {/* 按顺序渲染内容块 */}
                            {message.contentBlocks && message.contentBlocks.length > 0 ? (
                              // 使用 ContentBlocksList 组件保持顺序并管理展开状态
                              <ContentBlocksList 
                                blocks={message.contentBlocks} 
                                isStreaming={message.isStreaming} 
                              />
                            ) : (
                              // 回退：使用旧的渲染方式（用于从数据库加载的消息）
                              <>
                                {/* 工具调用列表 */}
                                {message.toolCalls && message.toolCalls.length > 0 && (
                                  <ToolCallsList toolCalls={message.toolCalls} />
                                )}
                                
                                {/* 文本内容 */}
                                {message.content && (
                                  <div className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3">
                                    {message.isStreaming ? (
                                      <TypewriterMessage
                                        content={message.content}
                                        isStreaming={message.isStreaming}
                                        variant="assistant"
                                      />
                                    ) : (
                                      <MessageContent
                                        content={message.content}
                                        isStreaming={false}
                                        variant="assistant"
                                      />
                                    )}
                                  </div>
                                )}
                              </>
                            )}
                            
                            {/* 时间戳 */}
                            {(message.content || (message.contentBlocks && message.contentBlocks.length > 0)) && (
                              <div className="text-xs text-gray-400 px-1">
                                {formatRelativeTime(message.timestamp)}
                              </div>
                            )}
                          </div>
                        )}
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
                <div className="p-4 border-t border-gray-100 flex-shrink-0 bg-white">
                  <div className="flex gap-3 items-end">
                    <div className="flex-1 relative">
                      <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入消息..."
                        className="w-full resize-none rounded-xl border border-gray-200 px-4 py-3 pr-20 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-100 outline-none transition-all min-h-[52px]"
                        rows={1}
                        disabled={isStreaming}
                        style={{ height: 'auto', maxHeight: '120px' }}
                        onInput={(e) => {
                          const target = e.target as HTMLTextAreaElement;
                          target.style.height = 'auto';
                          target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                        }}
                      />
                      <div className="absolute right-3 bottom-3 text-[10px] text-gray-400 pointer-events-none">
                        ⇧+↵ 发送
                      </div>
                    </div>
                    <button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isStreaming}
                      title="Shift+Enter 发送"
                      className="flex items-center justify-center w-[52px] h-[52px] rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                    >
                      {isStreaming ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Send className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>

      {/* 删除确认对话框 */}
      {sessionToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">确认删除</h3>
            <p className="text-gray-600 mb-6">
              确定要删除这个会话吗？此操作将同时删除会话中的所有消息，且无法恢复。
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setSessionToDelete(null)}
              >
                取消
              </Button>
              <Button
                variant="danger"
                onClick={() => handleDeleteSession(sessionToDelete)}
                loading={deleteSession.isPending}
              >
                <Trash2 className="w-4 h-4" />
                删除
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
