'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Progress } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useStatisticsOverviewV2 } from '@/hooks/use-statistics-v2';
import { useProjectsV2, useCreateProjectV2 } from '@/hooks/use-projects-v2';
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
  Brain,
  Rocket,
  Loader2,
} from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [requirement, setRequirement] = useState('');
  const { data: stats, isLoading: statsLoading } = useStatisticsOverviewV2();
  const { data: projects, isLoading: projectsLoading } = useProjectsV2({ limit: 6 });
  const { data: agents, isLoading: agentsLoading } = useAgentsV2({ limit: 6 });
  
  // 创建项目 mutation
  const createProjectMutation = useCreateProjectV2({
    onSuccess: (data) => {
      // 创建成功后跳转到项目详情页
      router.push(`/projects/${data.project_id}`);
    },
  });

  const recentProjects = projects || [];
  const recentAgents = agents || [];
  
  // 处理提交构建需求
  const handleSubmitRequirement = () => {
    if (!requirement.trim()) return;
    
    createProjectMutation.mutate({
      requirement: requirement.trim(),
    });
  };

  // 处理快捷示例点击
  const handleExampleClick = (example: string) => {
    setRequirement(example);
  };

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
        {/* Hero Banner with Quick Build */}
        <div className="mb-6 p-6 rounded-2xl bg-gradient-to-br from-primary-500 via-accent-500 to-agent-500 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-10" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-5 h-5" />
              <span className="text-sm font-medium opacity-90">Agentic AI Native</span>
            </div>
            <h2 className="text-xl font-bold mb-3">从想法到 Agent 自动化构建</h2>
            
            {/* 快速构建输入框 - 集成在 Banner 中 */}
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={requirement}
                  onChange={(e) => setRequirement(e.target.value)}
                  placeholder="描述你想要构建的 Agent，例如：帮我创建一个能够分析股票数据的智能助手..."
                  className="w-full px-4 py-3 text-gray-900 placeholder-gray-400 bg-white/95 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-white/50 transition-all"
                  disabled={createProjectMutation.isPending}
                />
              </div>
              <Button
                onClick={handleSubmitRequirement}
                disabled={!requirement.trim() || createProjectMutation.isPending}
                className="px-6 bg-white/20 hover:bg-white/30 text-white border border-white/30 disabled:opacity-50"
              >
                {createProjectMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Rocket className="w-4 h-4" />
                    构建
                  </>
                )}
              </Button>
            </div>
            
            {/* 快捷示例标签 */}
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="text-xs text-white/70">快捷：</span>
              {[
                { label: '医学文献', text: '创建一个能够搜索和分析 PubMed 医学文献的智能助手' },
                { label: 'AWS 报价', text: '帮我构建一个 AWS 云服务报价计算器，支持 EC2、S3、RDS 等产品' },
                { label: '新闻简报', text: '创建一个能够抓取和分析行业新闻的智能助手，每日生成简报' },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => handleExampleClick(item.text)}
                  className="px-2 py-0.5 text-xs bg-white/20 text-white/90 rounded-full hover:bg-white/30 transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
            
            {/* 错误提示 */}
            {createProjectMutation.isError && (
              <div className="mt-3 p-2 bg-red-500/20 text-white text-sm rounded-lg">
                构建失败：{createProjectMutation.error?.message || '未知错误'}
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4 mb-6">
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

        <div className="grid gap-4 lg:grid-cols-3">
          {/* Recent Projects */}
          <div className="lg:col-span-2 flex">
            <Card className="flex-1 flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <FolderKanban className="w-4 h-4 text-primary-600" />
                  构建进度
                </CardTitle>
                <Link href="/projects" className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1">
                  查看全部 <ArrowRight className="w-3 h-3" />
                </Link>
              </CardHeader>
              <CardContent className="pt-2 flex-1">
                {projectsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : recentProjects.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full py-8 text-gray-500">
                    <FolderKanban className="w-10 h-10 mb-2 text-gray-300" />
                    <p className="text-sm">暂无构建项目</p>
                    <Link href="/agents/new" className="text-primary-600 hover:underline text-xs">
                      创建第一个 Agent
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {recentProjects.map((project) => (
                      <Link
                        key={project.project_id}
                        href={`/projects/${project.project_id}`}
                        className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:border-primary-200 hover:bg-primary-50/30 transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
                            <FolderKanban className="w-4 h-4 text-primary-600" />
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-gray-900">
                              {project.project_name || `项目 ${project.project_id.slice(0, 8)}`}
                            </h4>
                            <p className="text-xs text-gray-500">
                              {project.current_stage || '等待开始'} · {formatRelativeTime(project.updated_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="w-20">
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
          <div className="flex flex-col gap-4">
            {/* Quick Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">快速操作</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 pt-2">
                <Link href="/agents/new" className="block">
                  <div className="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:border-primary-200 hover:bg-gradient-to-r hover:from-primary-50 hover:to-accent-50 transition-all">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-primary-600" />
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">创建 Agent</h4>
                      <p className="text-xs text-gray-500">用自然语言描述业务需求</p>
                    </div>
                  </div>
                </Link>
                <Link href="/tools" className="block">
                  <div className="flex items-center gap-3 p-2 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-all">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                      <Activity className="w-4 h-4 text-gray-600" />
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">能力工具库</h4>
                      <p className="text-xs text-gray-500">浏览和管理可用能力</p>
                    </div>
                  </div>
                </Link>
              </CardContent>
            </Card>

            {/* Recent Agents */}
            <Card className="flex-1 flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Bot className="w-4 h-4 text-primary-600" />
                  运行中 Agent
                </CardTitle>
                <Link href="/agents" className="text-xs text-primary-600 hover:text-primary-700">
                  全部
                </Link>
              </CardHeader>
              <CardContent className="pt-2 flex-1">
                {agentsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : recentAgents.length === 0 ? (
                  <div className="flex items-center justify-center h-full py-4 text-gray-500 text-xs">
                    暂无 Agent
                  </div>
                ) : (
                  <div className="space-y-1">
                    {recentAgents.slice(0, 4).map((agent) => (
                      <Link
                        key={agent.agent_id}
                        href={`/agents/${agent.agent_id}`}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            agent.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-gray-300'
                          }`} />
                          <span className="text-sm font-medium text-gray-900 truncate max-w-[120px]">
                            {agent.agent_name}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {formatNumber(agent.total_invocations || 0)} 次
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
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-100 animate-pulse" />
          <div className="flex-1">
            <div className="h-6 w-12 bg-gray-100 rounded animate-pulse mb-1" />
            <div className="h-3 w-20 bg-gray-100 rounded animate-pulse" />
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card hover className="p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xl font-bold text-gray-900">{value}</div>
          <div className="text-xs text-gray-500">
            {label}
            {total !== undefined && <span className="text-gray-400"> / {total}</span>}
          </div>
        </div>
      </div>
    </Card>
  );
}
