'use client';

import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Badge, Empty } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useAgentDetailV2, useAgentSessionsV2 } from '@/hooks/use-agents-v2';
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
} from 'lucide-react';

interface PageProps {
  params: { id: string };
}

export default function AgentDetailPage({ params }: PageProps) {
  const { id } = params;
  const { data: agent, isLoading, error } = useAgentDetailV2(id);
  const { data: sessions } = useAgentSessionsV2(id, 10);

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
                    {agent.deployment_type === 'agentcore' ? 'AgentCore' : 'Local'}
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

                {agent.agentcore_config && (
                  <div className="mt-4 pt-4 border-t border-gray-100">
                    <h4 className="text-sm font-medium text-gray-700 mb-3">AgentCore 配置</h4>
                    <div className="grid gap-4 grid-cols-1">
                      <InfoItem label="Agent ARN" value={agent.agentcore_config.agent_arn || '-'} mono small />
                      <InfoItem label="Alias ID" value={agent.agentcore_config.agent_alias_id || '-'} mono />
                    </div>
                  </div>
                )}

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
                <Link href={`/projects/${agent.project_id}`} className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <FileText className="w-4 h-4" />
                    查看项目
                  </Button>
                </Link>
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
