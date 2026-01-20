'use client';

import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Progress } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useStatisticsOverviewV2 } from '@/hooks/use-statistics-v2';
import { useProjectsV2 } from '@/hooks/use-projects-v2';
import { useAgentsV2 } from '@/hooks/use-agents-v2';
import { formatRelativeTime, formatNumber } from '@/lib/utils';
import {
  Bot,
  FolderKanban,
  Zap,
  TrendingUp,
  ArrowRight,
  Plus,
  Activity,
  Sparkles,
  Target,
  Brain,
} from 'lucide-react';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useStatisticsOverviewV2();
  const { data: projects, isLoading: projectsLoading } = useProjectsV2({ limit: 5 });
  const { data: agents, isLoading: agentsLoading } = useAgentsV2({ limit: 6 });

  const recentProjects = projects || [];
  const recentAgents = agents || [];

  return (
    <div className="page-container">
      <Header
        title="工作台"
        description="More Agent, More Intelligence, More Business Impact"
        actions={
          <Link href="/agents/new">
            <Button className="bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700">
              <Plus className="w-4 h-4" />
              创建 Agent
            </Button>
          </Link>
        }
      />

      <div className="page-content">
        {/* Hero Banner */}
        <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500 via-accent-500 to-agent-500 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-10" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-6 h-6" />
              <span className="text-sm font-medium opacity-90">Agentic AI Native</span>
            </div>
            <h2 className="text-2xl font-bold mb-2">从想法到 Agent 自动化构建</h2>
            <p className="text-white/80 max-w-2xl">
              通过自然语言描述业务需求，快速构建专属 Agent。无需编程，业务人员即可创建、部署和管理智能助手。
            </p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 mb-8">
          <StatCard
            icon={Bot}
            label="运行中 Agent"
            value={stats?.running_agents ?? 0}
            total={stats?.total_agents ?? 0}
            loading={statsLoading}
            color="primary"
          />
          <StatCard
            icon={FolderKanban}
            label="构建中项目"
            value={stats?.building_projects ?? 0}
            total={stats?.total_projects ?? 0}
            loading={statsLoading}
            color="accent"
          />
          <StatCard
            icon={Zap}
            label="今日业务处理"
            value={stats?.today_invocations ?? 0}
            loading={statsLoading}
            color="agent"
          />
          <StatCard
            icon={TrendingUp}
            label="构建成功率"
            value={`${Math.round(stats?.success_rate ?? 0)}%`}
            loading={statsLoading}
            color="success"
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Projects */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FolderKanban className="w-5 h-5 text-primary-600" />
                  构建进度
                </CardTitle>
                <Link href="/projects" className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1">
                  查看全部 <ArrowRight className="w-4 h-4" />
                </Link>
              </CardHeader>
              <CardContent>
                {projectsLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : recentProjects.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <FolderKanban className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>暂无构建项目</p>
                    <Link href="/agents/new" className="text-primary-600 hover:underline text-sm">
                      创建第一个 Agent
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentProjects.map((project) => (
                      <Link
                        key={project.project_id}
                        href={`/projects/${project.project_id}`}
                        className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:border-primary-200 hover:bg-primary-50/30 transition-all"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
                            <FolderKanban className="w-5 h-5 text-primary-600" />
                          </div>
                          <div>
                            <h4 className="font-medium text-gray-900">
                              {project.project_name || `项目 ${project.project_id.slice(0, 8)}`}
                            </h4>
                            <p className="text-sm text-gray-500">
                              {project.current_stage || '等待开始'} · {formatRelativeTime(project.updated_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="w-24">
                            <Progress value={project.progress} size="sm" />
                          </div>
                          <StatusBadge status={project.status as any} size="sm" />
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions & Recent Agents */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>快速操作</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link href="/agents/new" className="block">
                  <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-primary-200 hover:bg-gradient-to-r hover:from-primary-50 hover:to-accent-50 transition-all">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
                      <Sparkles className="w-5 h-5 text-primary-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">创建 Agent</h4>
                      <p className="text-xs text-gray-500">用自然语言描述业务需求</p>
                    </div>
                  </div>
                </Link>
                <Link href="/tools" className="block">
                  <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all">
                    <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900">能力工具库</h4>
                      <p className="text-xs text-gray-500">浏览和管理可用能力</p>
                    </div>
                  </div>
                </Link>
              </CardContent>
            </Card>

            {/* Recent Agents */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-primary-600" />
                  运行中 Agent
                </CardTitle>
                <Link href="/agents" className="text-sm text-primary-600 hover:text-primary-700">
                  全部
                </Link>
              </CardHeader>
              <CardContent>
                {agentsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : recentAgents.length === 0 ? (
                  <div className="text-center py-6 text-gray-500 text-sm">
                    暂无 Agent
                  </div>
                ) : (
                  <div className="space-y-2">
                    {recentAgents.map((agent) => (
                      <Link
                        key={agent.agent_id}
                        href={`/agents/${agent.agent_id}`}
                        className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${
                            agent.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-gray-300'
                          }`} />
                          <span className="text-sm font-medium text-gray-900 truncate max-w-[140px]">
                            {agent.agent_name}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {formatNumber(agent.total_invocations || 0)} 次处理
                        </span>
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

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: number | string;
  total?: number;
  loading?: boolean;
  color: 'primary' | 'accent' | 'agent' | 'success';
}

function StatCard({ icon: Icon, label, value, total, loading, color }: StatCardProps) {
  const colors = {
    primary: 'bg-primary-50 text-primary-600',
    accent: 'bg-accent-50 text-accent-600',
    agent: 'bg-agent-50 text-agent-600',
    success: 'bg-success-50 text-success-600',
  };

  if (loading) {
    return (
      <Card>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gray-100 animate-pulse" />
          <div className="flex-1">
            <div className="h-8 w-16 bg-gray-100 rounded animate-pulse mb-2" />
            <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card hover>
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">
            {label}
            {total !== undefined && <span className="text-gray-400"> / {total}</span>}
          </div>
        </div>
      </div>
    </Card>
  );
}
