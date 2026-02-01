'use client';

import Link from 'next/link';
import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Empty } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useAgentDetailV2, useAgentSessionsV2, useDeleteAgentV2, useCreateAgentUpdate } from '@/hooks/use-agents-v2';
import { formatDate, formatRelativeTime, formatNumber } from '@/lib/utils';
import {
  ArrowLeft,
  Bot,
  MessageSquare,
  Zap,
  Clock,
  CheckCircle2,
  Settings,
  Code,
  FileText,
  TrendingUp,
  Cloud,
  ExternalLink,
  Copy,
  Server,
  Activity,
  FileSearch,
  Trash2,
  RefreshCw,
  X,
} from 'lucide-react';

interface PageProps {
  params: { id: string };
}

// Tab 类型定义
type TabType = 'basic' | 'agentcore';

// 更新 Agent 对话框组件
function UpdateAgentDialog({
  agent,
  isOpen,
  onClose,
  onConfirm,
  isUpdating,
}: {
  agent: { agent_id: string; agent_name: string } | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (requirement: string) => void;
  isUpdating: boolean;
}) {
  const [requirement, setRequirement] = useState('');

  if (!isOpen || !agent) return null;

  const handleSubmit = () => {
    if (requirement.trim().length >= 10) {
      onConfirm(requirement.trim());
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">更新 Agent</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <p className="text-gray-600 mb-4">
          为 <span className="font-medium text-gray-900">{agent.agent_name}</span> 创建更新任务
        </p>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            更新需求描述 <span className="text-red-500">*</span>
          </label>
          <textarea
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            placeholder="请描述您希望对该 Agent 进行的更新，例如：添加新的工具函数、修改提示词、优化响应格式等..."
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            rows={5}
            disabled={isUpdating}
          />
          <p className="text-xs text-gray-500 mt-1">
            至少输入 10 个字符，详细描述更新需求
          </p>
        </div>
        
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose} disabled={isUpdating}>
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isUpdating || requirement.trim().length < 10}
          >
            {isUpdating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                创建更新任务
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// 删除确认对话框组件
function DeleteAgentDialog({
  agent,
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
}: {
  agent: { agent_name: string; deployment_type?: string } | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (options: { deleteLocalFiles: boolean; deleteCloudResources: boolean }) => void;
  isDeleting: boolean;
}) {
  const [deleteLocalFiles, setDeleteLocalFiles] = useState(false);
  const [deleteCloudResources, setDeleteCloudResources] = useState(false);

  if (!isOpen || !agent) return null;

  const isAgentCore = agent.deployment_type === 'agentcore';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">确认删除 Agent</h3>
        <p className="text-gray-600 mb-4">
          确定要删除 Agent <span className="font-medium text-gray-900">{agent.agent_name}</span> 吗？
        </p>
        
        <div className="space-y-3 mb-6">
          <p className="text-sm text-gray-500">将删除以下资源：</p>
          <ul className="text-sm text-gray-600 space-y-1 ml-4">
            <li>• DynamoDB 中的 Agent 记录</li>
            <li>• 关联的会话和消息记录</li>
            <li>• SQS 中相关的任务消息</li>
          </ul>
          
          <div className="border-t border-gray-100 pt-3 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={deleteLocalFiles}
                onChange={(e) => setDeleteLocalFiles(e.target.checked)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">同时删除本地文件（agents、prompts、tools 目录）</span>
            </label>
            
            {isAgentCore && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={deleteCloudResources}
                  onChange={(e) => setDeleteCloudResources(e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">同时删除云资源（AgentCore Runtime、ECR 仓库）</span>
              </label>
            )}
          </div>
        </div>
        
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose} disabled={isDeleting}>
            取消
          </Button>
          <Button
            variant="danger"
            onClick={() => onConfirm({ deleteLocalFiles, deleteCloudResources })}
            disabled={isDeleting}
          >
            {isDeleting ? '删除中...' : '确认删除'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function AgentDetailPage({ params }: PageProps) {
  const { id } = params;
  const router = useRouter();
  const { data: agent, isLoading, error } = useAgentDetailV2(id);
  const { data: sessions } = useAgentSessionsV2(id, 10);
  const [activeTab, setActiveTab] = useState<TabType>('basic');
  const [copiedField, setCopiedField] = useState<string | null>(null);
  
  // 删除相关状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const deleteAgent = useDeleteAgentV2({
    onSuccess: () => {
      setDeleteDialogOpen(false);
      router.push('/agents');
    },
  });

  // 更新 Agent 相关状态
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const updateAgent = useCreateAgentUpdate({
    onSuccess: (data) => {
      setUpdateDialogOpen(false);
      // 跳转到项目详情页查看更新进度
      router.push(`/projects/${data.project_id}`);
    },
  });

  // 确认更新 Agent
  const handleConfirmUpdate = (requirement: string) => {
    if (agent) {
      updateAgent.mutate({
        agent_id: agent.agent_id,
        update_requirement: requirement,
      });
    }
  };

  // 确认删除
  const handleConfirmDelete = (options: { deleteLocalFiles: boolean; deleteCloudResources: boolean }) => {
    if (agent) {
      deleteAgent.mutate({
        agentId: agent.agent_id,
        deleteLocalFiles: options.deleteLocalFiles,
        deleteCloudResources: options.deleteCloudResources,
      });
    }
  };

  // 判断是否为 AgentCore 部署
  const isAgentCore = useMemo(() => {
    if (!agent) return false;
    return agent.deployment_type === 'agentcore' || 
           Boolean(agent.agentcore_runtime_arn) || 
           Boolean(agent.agentcore_config?.agent_arn);
  }, [agent]);

  // 获取 AgentCore 运行时信息
  const agentcoreInfo = useMemo(() => {
    if (!agent) return null;
    
    const runtimeArn = agent.agentcore_runtime_arn || agent.agentcore_config?.agent_arn;
    const region = agent.agentcore_region || 'us-west-2';
    const alias = agent.agentcore_runtime_alias || agent.agentcore_config?.agent_alias_id || 'DEFAULT';
    
    if (!runtimeArn) return null;

    // 从 ARN 中提取 runtime ID
    // ARN 格式: arn:aws:bedrock-agentcore:region:account:runtime/runtime-id
    const arnParts = runtimeArn.split('/');
    const runtimeId = arnParts.length > 1 ? arnParts[arnParts.length - 1] : runtimeArn;
    
    // 获取 agent name（用于 observability URL）
    const agentName = agent.agent_name || runtimeId.split('-')[0];

    // 构建 AWS Console 链接
    // AgentCore Console: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents/runtime-id
    const consoleUrl = `https://${region}.console.aws.amazon.com/bedrock-agentcore/agents/${runtimeId}`;
    
    // CloudWatch Logs: /aws/bedrock-agentcore/runtimes/runtime-id-ALIAS
    const logsUrl = `https://${region}.console.aws.amazon.com/cloudwatch/home?region=${region}#logsV2:log-groups/log-group/$252Faws$252Fbedrock-agentcore$252Fruntimes$252F${runtimeId}-${alias}`;
    
    // AgentCore Observability
    const observabilityUrl = `https://${region}.console.aws.amazon.com/cloudwatch/home?region=${region}#gen-ai-observability/agent-core/agent-alias/${runtimeId}/endpoint/${alias}/agent/${agentName}?start=-1209600000&resourceId=${encodeURIComponent(runtimeArn)}/runtime-endpoint/${alias}:${alias}&serviceName=${agentName}.${alias}`;

    return {
      runtimeId,
      runtimeArn,
      alias,
      region,
      agentName,
      consoleUrl,
      logsUrl,
      observabilityUrl,
      aliasArn: agent.agentcore_config?.agent_alias_arn,
    };
  }, [agent]);

  // 复制到剪贴板
  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="page-container">
        <Header title="加载中..." />
        <div className="page-content">
          <div className="animate-pulse space-y-6">
            <div className="h-32 bg-gray-100 rounded-xl" />
            <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
              <div className="lg:col-span-2 h-64 bg-gray-100 rounded-xl" />
              <div className="h-64 bg-gray-100 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="page-container">
        <Header title="Agent 详情" />
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

  const stats = {
    total_invocations: agent.total_invocations || 0,
    successful_invocations: agent.successful_invocations || 0,
    failed_invocations: agent.failed_invocations || 0,
    avg_duration_ms: agent.avg_duration_ms || 0,
    last_invoked_at: agent.last_invoked_at,
  };

  const successRate = stats.total_invocations > 0
    ? (stats.successful_invocations / stats.total_invocations) * 100
    : 0;

  return (
    <div className="page-container">
      <Header
        title={agent.agent_name}
        description={agent.description || 'AI Agent'}
        actions={
          <div className="flex items-center gap-3">
            <Link href="/agents">
              <Button variant="ghost">
                <ArrowLeft className="w-4 h-4" />
                返回
              </Button>
            </Link>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(true)}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
              删除
            </Button>
            <Link href={`/agents/${id}/chat`}>
              <Button>
                <MessageSquare className="w-4 h-4" />
                对话
              </Button>
            </Link>
          </div>
        }
      />

      <div className="page-content">
        {/* Agent Header Card */}
        <Card className="mb-6">
          <div className="flex items-start gap-6">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold text-gray-900">{agent.agent_name}</h1>
                <StatusBadge status={agent.status} />
                {agent.version && (
                  <Badge variant="outline">{agent.version}</Badge>
                )}
                {agent.deployment_type && (
                  <Badge variant={agent.deployment_type === 'agentcore' ? 'info' : 'outline'} size="sm">
                    {agent.deployment_type === 'agentcore' ? (
                      <span className="flex items-center gap-1">
                        <Cloud className="w-3 h-3" />
                        AgentCore
                      </span>
                    ) : 'Local'}
                  </Badge>
                )}
              </div>
              {agent.description && (
                <p className="text-gray-600 mb-4">{agent.description}</p>
              )}
              <div className="flex flex-wrap gap-2">
                {agent.capabilities?.map((cap, i) => (
                  <Badge key={i} variant="info" size="sm">{cap}</Badge>
                ))}
                {agent.category && (
                  <Badge variant="outline" size="sm">{agent.category}</Badge>
                )}
              </div>
            </div>
          </div>
        </Card>

        <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
          {/* Stats */}
          <div className="lg:col-span-2 space-y-6">
            {/* Performance Stats */}
            <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
              <StatCard
                icon={Zap}
                label="总调用次数"
                value={formatNumber(stats.total_invocations)}
                color="blue"
              />
              <StatCard
                icon={CheckCircle2}
                label="成功次数"
                value={formatNumber(stats.successful_invocations)}
                color="green"
              />
              <StatCard
                icon={TrendingUp}
                label="成功率"
                value={`${Math.round(successRate)}%`}
                color="purple"
              />
              <StatCard
                icon={Clock}
                label="平均响应"
                value={stats.avg_duration_ms > 0 ? `${Math.round(stats.avg_duration_ms)}ms` : '-'}
                color="amber"
              />
            </div>

            {/* Tab Navigation - 仅在 AgentCore 部署时显示 */}
            {isAgentCore && (
              <div className="flex gap-2 border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('basic')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'basic'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    基本信息
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('agentcore')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'agentcore'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Cloud className="w-4 h-4" />
                    AgentCore Runtime
                  </span>
                </button>
              </div>
            )}

            {/* Tab Content */}
            {activeTab === 'basic' ? (
              <>
                {/* Configuration */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="w-5 h-5 text-gray-500" />
                      配置信息
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
                      <InfoItem label="Agent ID" value={agent.agent_id} mono />
                      <InfoItem label="项目 ID" value={agent.project_id || '-'} mono />
                      <InfoItem label="分类" value={agent.category || '-'} />
                      <InfoItem label="部署类型" value={agent.deployment_type || 'local'} />
                      <InfoItem label="创建时间" value={formatDate(agent.created_at)} />
                      <InfoItem label="最后调用" value={formatRelativeTime(stats.last_invoked_at)} />
                    </div>

                    {agent.code_path && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">代码路径</h4>
                        <InfoItem label="Agent 代码" value={agent.code_path} mono small />
                        {agent.prompt_path && (
                          <InfoItem label="Prompt 路径" value={agent.prompt_path} mono small />
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            ) : (
              /* AgentCore Runtime Tab */
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Cloud className="w-5 h-5 text-blue-500" />
                    AgentCore 运行时信息
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {agentcoreInfo ? (
                    <div className="space-y-6">
                      {/* 运行时基本信息 */}
                      <div className="grid gap-4">
                        <CopyableInfoItem
                          icon={Server}
                          label="运行时 ID"
                          value={agentcoreInfo.runtimeId}
                          onCopy={() => copyToClipboard(agentcoreInfo.runtimeId, 'runtimeId')}
                          copied={copiedField === 'runtimeId'}
                        />
                        <CopyableInfoItem
                          icon={Code}
                          label="运行时 ARN"
                          value={agentcoreInfo.runtimeArn}
                          onCopy={() => copyToClipboard(agentcoreInfo.runtimeArn, 'runtimeArn')}
                          copied={copiedField === 'runtimeArn'}
                        />
                        <CopyableInfoItem
                          icon={Activity}
                          label="Alias"
                          value={agentcoreInfo.alias}
                          onCopy={() => copyToClipboard(agentcoreInfo.alias, 'alias')}
                          copied={copiedField === 'alias'}
                        />
                        {agentcoreInfo.aliasArn && (
                          <CopyableInfoItem
                            icon={Code}
                            label="Alias ARN"
                            value={agentcoreInfo.aliasArn}
                            onCopy={() => copyToClipboard(agentcoreInfo.aliasArn!, 'aliasArn')}
                            copied={copiedField === 'aliasArn'}
                          />
                        )}
                        <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                          <Cloud className="w-5 h-5 text-gray-400 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <div className="text-xs text-gray-500 mb-1">区域</div>
                            <div className="text-sm font-medium text-gray-900">
                              {agentcoreInfo.region}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 快速跳转链接 */}
                      <div className="border-t border-gray-100 pt-4">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">快速跳转</h4>
                        <div className="grid gap-3">
                          <ExternalLinkButton
                            icon={Cloud}
                            label="AgentCore Console"
                            description="在 AWS Console 中查看运行时详情"
                            href={agentcoreInfo.consoleUrl}
                          />
                          <ExternalLinkButton
                            icon={FileSearch}
                            label="CloudWatch Logs"
                            description="查看运行时日志"
                            href={agentcoreInfo.logsUrl}
                          />
                          <ExternalLinkButton
                            icon={Activity}
                            label="AgentCore Observability"
                            description="查看调用追踪和性能指标"
                            href={agentcoreInfo.observabilityUrl}
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <Cloud className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p>暂无 AgentCore 运行时信息</p>
                      <p className="text-sm mt-1">请先部署 Agent 到 AgentCore</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Tools */}
            {agent.tools && agent.tools.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Code className="w-5 h-5 text-gray-500" />
                    工具列表
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {agent.tools.map((tool, i) => (
                      <Badge key={i} variant="outline">{tool}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Capabilities */}
            {agent.capabilities && agent.capabilities.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Code className="w-5 h-5 text-gray-500" />
                    能力列表
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {agent.capabilities.map((cap, i) => (
                      <Badge key={i} variant="info">{cap}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>快速操作</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link href={`/agents/${id}/chat`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <MessageSquare className="w-4 h-4" />
                    开始对话
                  </Button>
                </Link>
                <Link href={`/agents/${id}/files`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Code className="w-4 h-4" />
                    查看/编辑文件
                  </Button>
                </Link>
                <Link href={`/projects/${agent.project_id}`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <FileText className="w-4 h-4" />
                    查看项目
                  </Button>
                </Link>
                <Button 
                  variant="outline" 
                  className="w-full justify-start"
                  onClick={() => setUpdateDialogOpen(true)}
                >
                  <RefreshCw className="w-4 h-4" />
                  更新 Agent
                </Button>
              </CardContent>
            </Card>

            {/* Recent Sessions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-gray-500" />
                  最近会话
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!sessions || sessions.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">暂无会话记录</p>
                ) : (
                  <div className="space-y-2">
                    {sessions.slice(0, 5).map((session) => (
                      <Link
                        key={session.session_id}
                        href={`/agents/${id}/chat?session=${session.session_id}`}
                        className="block p-3 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {session.display_name || session.session_id.slice(0, 8)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatRelativeTime(session.last_active_at || session.created_at)}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      
      {/* 删除确认对话框 */}
      <DeleteAgentDialog
        agent={agent}
        isOpen={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleConfirmDelete}
        isDeleting={deleteAgent.isPending}
      />
      
      {/* 更新 Agent 对话框 */}
      <UpdateAgentDialog
        agent={agent}
        isOpen={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        onConfirm={handleConfirmUpdate}
        isUpdating={updateAgent.isPending}
      />
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: 'blue' | 'green' | 'purple' | 'amber';
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };

  return (
    <Card padding="sm">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <div className="text-lg font-bold text-gray-900">{value}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      </div>
    </Card>
  );
}

function InfoItem({
  label,
  value,
  mono = false,
  small = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-gray-500 mb-1">{label}</dt>
      <dd className={`text-gray-900 ${mono ? 'font-mono' : ''} ${small ? 'text-xs' : 'text-sm'} break-all`}>
        {value}
      </dd>
    </div>
  );
}

// 可复制的信息项组件
function CopyableInfoItem({
  icon: Icon,
  label,
  value,
  onCopy,
  copied,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg group">
      <Icon className="w-5 h-5 text-gray-400 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-gray-500 mb-1">{label}</div>
        <div className="text-sm font-mono text-gray-900 break-all">{value}</div>
      </div>
      <button
        onClick={onCopy}
        className="p-1.5 rounded-md hover:bg-gray-200 transition-colors opacity-0 group-hover:opacity-100"
        title="复制"
      >
        {copied ? (
          <CheckCircle2 className="w-4 h-4 text-green-500" />
        ) : (
          <Copy className="w-4 h-4 text-gray-400" />
        )}
      </button>
    </div>
  );
}

// 外部链接按钮组件
function ExternalLinkButton({
  icon: Icon,
  label,
  description,
  href,
}: {
  icon: React.ElementType;
  label: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors group"
    >
      <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
        <Icon className="w-5 h-5 text-blue-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-900 group-hover:text-primary-600">
          {label}
        </div>
        <div className="text-xs text-gray-500">{description}</div>
      </div>
      <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-primary-500" />
    </a>
  );
}
