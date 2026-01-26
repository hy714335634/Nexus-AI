'use client';

import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { 
  useStatisticsOverview, 
  useBuildStatistics, 
  useInvocationStatistics,
  useAgentCategoryDistribution,
  useTopAgents,
  useRecentActivities,
  useSystemHealth,
} from '@/hooks/use-statistics';
import { formatNumber, formatRelativeTime } from '@/lib/utils';
import {
  BarChart3,
  TrendingUp,
  Bot,
  Zap,
  Clock,
  CheckCircle2,
  Activity,
  FolderKanban,
  Award,
  Heart,
  AlertCircle,
  Server,
} from 'lucide-react';

export default function AnalyticsPage() {
  const { data: overview, isLoading: overviewLoading } = useStatisticsOverview();
  const { data: buildStats } = useBuildStatistics(30);
  const { data: invocationStats } = useInvocationStatistics(30);
  const { data: categoryDistribution } = useAgentCategoryDistribution();
  const { data: topAgents } = useTopAgents(5);
  const { data: recentActivities } = useRecentActivities(8);
  const { data: systemHealth } = useSystemHealth();

  const stats = [
    {
      label: '总 Agents',
      value: overview?.total_agents ?? 0,
      icon: Bot,
      color: 'blue',
    },
    {
      label: '运行中',
      value: overview?.running_agents ?? 0,
      icon: Activity,
      color: 'green',
    },
    {
      label: '总调用次数',
      value: overview?.total_invocations ?? 0,
      icon: Zap,
      color: 'amber',
    },
    {
      label: '构建成功率',
      value: `${Math.round(overview?.success_rate ?? 0)}%`,
      icon: CheckCircle2,
      color: 'purple',
    },
  ];

  // 计算构建统计汇总
  const totalBuilds = buildStats?.reduce((sum, day) => sum + day.total_builds, 0) ?? 0;
  const successfulBuilds = buildStats?.reduce((sum, day) => sum + day.successful_builds, 0) ?? 0;
  const failedBuilds = buildStats?.reduce((sum, day) => sum + day.failed_builds, 0) ?? 0;

  // 计算调用统计汇总
  const totalInvocations = invocationStats?.reduce((sum, day) => sum + day.total_invocations, 0) ?? 0;
  const successfulInvocations = invocationStats?.reduce((sum, day) => sum + day.successful_invocations, 0) ?? 0;

  // 系统健康状态颜色
  const healthColors = {
    healthy: 'text-green-600 bg-green-50',
    degraded: 'text-yellow-600 bg-yellow-50',
    warning: 'text-orange-600 bg-orange-50',
    critical: 'text-red-600 bg-red-50',
  };

  const healthLabels = {
    healthy: '健康',
    degraded: '轻微异常',
    warning: '警告',
    critical: '严重',
  };

  return (
    <div className="page-container">
      <Header
        title="业务洞察"
        description="查看平台使用统计和业务指标"
      />

      <div className="page-content">
        {/* 系统健康状态 */}
        {systemHealth && (
          <Card className="mb-6">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${healthColors[systemHealth.status]}`}>
                    {systemHealth.status === 'healthy' ? (
                      <Heart className="w-5 h-5" />
                    ) : (
                      <AlertCircle className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">系统状态</div>
                    <div className={`font-semibold ${healthColors[systemHealth.status].split(' ')[0]}`}>
                      {healthLabels[systemHealth.status]}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">数据库:</span>
                    <span className={systemHealth.database === 'healthy' ? 'text-green-600' : 'text-red-600'}>
                      {systemHealth.database === 'healthy' ? '正常' : '异常'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">活跃 Agent:</span>
                    <span className="font-medium">{systemHealth.active_agents}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FolderKanban className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">构建中:</span>
                    <span className="font-medium">{systemHealth.building_projects}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 概览统计 */}
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4 mb-6">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <div className="flex items-start justify-between p-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {overviewLoading ? '-' : typeof stat.value === 'number' ? formatNumber(stat.value) : stat.value}
                  </p>
                </div>
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  stat.color === 'blue' ? 'bg-blue-50 text-blue-600' :
                  stat.color === 'green' ? 'bg-green-50 text-green-600' :
                  stat.color === 'amber' ? 'bg-amber-50 text-amber-600' :
                  'bg-purple-50 text-purple-600'
                }`}>
                  <stat.icon className="w-5 h-5" />
                </div>
              </div>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2 mb-6">
          {/* 构建统计 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="w-5 h-5 text-primary-600" />
                构建统计 (30天)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-xl font-bold text-gray-900">{formatNumber(totalBuilds)}</div>
                  <div className="text-xs text-gray-500">总构建</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-xl font-bold text-green-600">{formatNumber(successfulBuilds)}</div>
                  <div className="text-xs text-gray-500">成功</div>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <div className="text-xl font-bold text-red-600">{formatNumber(failedBuilds)}</div>
                  <div className="text-xs text-gray-500">失败</div>
                </div>
              </div>
              
              {/* 构建趋势图 */}
              {buildStats && buildStats.length > 0 ? (
                <div className="space-y-1.5">
                  {buildStats.slice(-7).map((day) => (
                    <div key={day.date} className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 w-16">{day.date.slice(5)}</span>
                      <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden flex">
                        <div
                          className="h-full bg-green-500"
                          style={{ width: `${day.total_builds > 0 ? (day.successful_builds / day.total_builds) * 100 : 0}%` }}
                        />
                        <div
                          className="h-full bg-red-500"
                          style={{ width: `${day.total_builds > 0 ? (day.failed_builds / day.total_builds) * 100 : 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-6 text-right">{day.total_builds}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无构建数据
                </div>
              )}
            </CardContent>
          </Card>

          {/* 调用统计 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Zap className="w-5 h-5 text-amber-600" />
                调用统计 (30天)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-xl font-bold text-gray-900">{formatNumber(totalInvocations)}</div>
                  <div className="text-xs text-gray-500">总调用</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-xl font-bold text-green-600">{formatNumber(successfulInvocations)}</div>
                  <div className="text-xs text-gray-500">成功</div>
                </div>
              </div>

              {/* 调用趋势图 */}
              {invocationStats && invocationStats.length > 0 ? (
                <>
                  <div className="h-32 flex items-end gap-1">
                    {invocationStats.slice(-14).map((day) => {
                      const maxInvocations = Math.max(...(invocationStats?.map(d => d.total_invocations) || [1]));
                      const height = maxInvocations > 0 ? (day.total_invocations / maxInvocations) * 100 : 0;
                      return (
                        <div
                          key={day.date}
                          className="flex-1 bg-primary-500 rounded-t hover:bg-primary-600 transition-colors cursor-pointer"
                          style={{ height: `${Math.max(height, 4)}%` }}
                          title={`${day.date}: ${day.total_invocations} 次调用`}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between mt-2 text-xs text-gray-400">
                    <span>14天前</span>
                    <span>今天</span>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无调用数据
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3 mb-6">
          {/* Agent 分类分布 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="w-5 h-5 text-blue-600" />
                Agent 分类分布
              </CardTitle>
            </CardHeader>
            <CardContent>
              {categoryDistribution && categoryDistribution.length > 0 ? (
                <div className="space-y-2">
                  {categoryDistribution.slice(0, 6).map((item, index) => {
                    const total = categoryDistribution.reduce((sum, i) => sum + i.count, 0);
                    const percentage = total > 0 ? (item.count / total) * 100 : 0;
                    const colors = ['bg-blue-500', 'bg-green-500', 'bg-amber-500', 'bg-purple-500', 'bg-pink-500', 'bg-cyan-500'];
                    return (
                      <div key={item.category} className="flex items-center gap-2">
                        <span className="text-xs text-gray-600 w-24 truncate" title={item.category}>
                          {item.category}
                        </span>
                        <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${colors[index % colors.length]} rounded-full`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-8 text-right">{item.count}</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无分类数据
                </div>
              )}
            </CardContent>
          </Card>

          {/* 热门 Agent */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Award className="w-5 h-5 text-amber-600" />
                热门 Agent
              </CardTitle>
            </CardHeader>
            <CardContent>
              {topAgents && topAgents.length > 0 ? (
                <div className="space-y-2">
                  {topAgents.map((agent, index) => (
                    <Link
                      key={agent.agent_id}
                      href={`/agents/${agent.agent_id}`}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                        index === 0 ? 'bg-amber-100 text-amber-700' :
                        index === 1 ? 'bg-gray-200 text-gray-600' :
                        index === 2 ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {index + 1}
                      </span>
                      <span className="flex-1 text-sm font-medium text-gray-900 truncate">
                        {agent.agent_name}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatNumber(agent.total_invocations)} 次
                      </span>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无 Agent 数据
                </div>
              )}
            </CardContent>
          </Card>

          {/* 最近活动 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="w-5 h-5 text-green-600" />
                最近活动
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentActivities && recentActivities.length > 0 ? (
                <div className="space-y-2">
                  {recentActivities.slice(0, 6).map((activity) => (
                    <Link
                      key={`${activity.type}-${activity.id}`}
                      href={activity.type === 'project' ? `/projects/${activity.id}` : `/agents/${activity.id}`}
                      className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className={`w-6 h-6 rounded flex items-center justify-center ${
                        activity.type === 'project' ? 'bg-primary-100 text-primary-600' : 'bg-agent-100 text-agent-600'
                      }`}>
                        {activity.type === 'project' ? (
                          <FolderKanban className="w-3 h-3" />
                        ) : (
                          <Bot className="w-3 h-3" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {activity.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {activity.action}
                        </div>
                      </div>
                      <span className="text-xs text-gray-400">
                        {formatRelativeTime(activity.timestamp)}
                      </span>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400 text-sm">
                  暂无活动记录
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 性能指标 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="w-5 h-5 text-gray-500" />
              性能指标
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">平均构建时间</span>
                </div>
                <div className="text-xl font-bold text-gray-900">
                  {overview?.avg_build_time_minutes ? `${Math.round(overview.avg_build_time_minutes)} 分钟` : '-'}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">平均响应时间</span>
                </div>
                <div className="text-xl font-bold text-gray-900">
                  {invocationStats && invocationStats.length > 0
                    ? `${Math.round(invocationStats.reduce((sum, d) => sum + d.avg_duration_ms, 0) / invocationStats.length)} ms`
                    : '-'}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">调用成功率</span>
                </div>
                <div className="text-xl font-bold text-gray-900">
                  {totalInvocations > 0
                    ? `${Math.round((successfulInvocations / totalInvocations) * 100)}%`
                    : '-'}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <FolderKanban className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">总项目数</span>
                </div>
                <div className="text-xl font-bold text-gray-900">
                  {overview?.total_projects ?? '-'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
