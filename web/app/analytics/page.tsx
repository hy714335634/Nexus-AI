'use client';

import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui';
import { useStatisticsOverview, useBuildStatistics, useInvocationStatistics } from '@/hooks/use-statistics';
import { formatNumber } from '@/lib/utils';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Bot,
  Zap,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
} from 'lucide-react';

export default function AnalyticsPage() {
  const { data: overview, isLoading: overviewLoading } = useStatisticsOverview();
  const { data: buildStats } = useBuildStatistics(30);
  const { data: invocationStats } = useInvocationStatistics(30);

  const stats = [
    {
      label: '总 Agents',
      value: overview?.total_agents ?? 0,
      icon: Bot,
      color: 'blue',
      change: '+12%',
      changeType: 'up' as const,
    },
    {
      label: '运行中',
      value: overview?.running_agents ?? 0,
      icon: Activity,
      color: 'green',
      change: '+5%',
      changeType: 'up' as const,
    },
    {
      label: '今日调用',
      value: overview?.today_calls ?? 0,
      icon: Zap,
      color: 'amber',
      change: '+23%',
      changeType: 'up' as const,
    },
    {
      label: '成功率',
      value: `${Math.round(overview?.success_rate ?? 0)}%`,
      icon: CheckCircle2,
      color: 'purple',
      change: '+2%',
      changeType: 'up' as const,
    },
  ];

  // Calculate totals from build stats
  const totalBuilds = buildStats?.reduce((sum, day) => sum + day.total_builds, 0) ?? 0;
  const successfulBuilds = buildStats?.reduce((sum, day) => sum + day.successful_builds, 0) ?? 0;
  const failedBuilds = buildStats?.reduce((sum, day) => sum + day.failed_builds, 0) ?? 0;

  // Calculate totals from invocation stats
  const totalInvocations = invocationStats?.reduce((sum, day) => sum + day.total_invocations, 0) ?? 0;
  const successfulInvocations = invocationStats?.reduce((sum, day) => sum + day.successful_invocations, 0) ?? 0;

  return (
    <div className="page-container">
      <Header
        title="数据分析"
        description="查看平台使用统计和趋势"
      />

      <div className="page-content">
        {/* Overview Stats */}
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {overviewLoading ? '-' : typeof stat.value === 'number' ? formatNumber(stat.value) : stat.value}
                  </p>
                </div>
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  stat.color === 'blue' ? 'bg-blue-50 text-blue-600' :
                  stat.color === 'green' ? 'bg-green-50 text-green-600' :
                  stat.color === 'amber' ? 'bg-amber-50 text-amber-600' :
                  'bg-purple-50 text-purple-600'
                }`}>
                  <stat.icon className="w-6 h-6" />
                </div>
              </div>
              <div className={`flex items-center gap-1 mt-3 text-sm ${
                stat.changeType === 'up' ? 'text-green-600' : 'text-red-600'
              }`}>
                {stat.changeType === 'up' ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span>{stat.change} 较上月</span>
              </div>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Build Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary-600" />
                构建统计 (30天)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">{formatNumber(totalBuilds)}</div>
                  <div className="text-sm text-gray-500">总构建</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{formatNumber(successfulBuilds)}</div>
                  <div className="text-sm text-gray-500">成功</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{formatNumber(failedBuilds)}</div>
                  <div className="text-sm text-gray-500">失败</div>
                </div>
              </div>
              
              {/* Simple bar chart representation */}
              <div className="space-y-2">
                {buildStats?.slice(-7).map((day, i) => (
                  <div key={day.date} className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-20">{day.date.slice(5)}</span>
                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden flex">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${day.total_builds > 0 ? (day.successful_builds / day.total_builds) * 100 : 0}%` }}
                      />
                      <div
                        className="h-full bg-red-500"
                        style={{ width: `${day.total_builds > 0 ? (day.failed_builds / day.total_builds) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-8">{day.total_builds}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Invocation Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-600" />
                调用统计 (30天)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">{formatNumber(totalInvocations)}</div>
                  <div className="text-sm text-gray-500">总调用</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{formatNumber(successfulInvocations)}</div>
                  <div className="text-sm text-gray-500">成功</div>
                </div>
              </div>

              {/* Simple line chart representation */}
              <div className="h-40 flex items-end gap-1">
                {invocationStats?.slice(-14).map((day, i) => {
                  const maxInvocations = Math.max(...(invocationStats?.map(d => d.total_invocations) || [1]));
                  const height = maxInvocations > 0 ? (day.total_invocations / maxInvocations) * 100 : 0;
                  return (
                    <div
                      key={day.date}
                      className="flex-1 bg-primary-500 rounded-t hover:bg-primary-600 transition-colors"
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
            </CardContent>
          </Card>
        </div>

        {/* Performance Metrics */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-gray-500" />
              性能指标
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 grid-cols-1 sm:grid-cols-3">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">平均构建时间</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {overview?.avg_build_time_minutes ? `${Math.round(overview.avg_build_time_minutes)} 分钟` : '-'}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">平均响应时间</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {invocationStats && invocationStats.length > 0
                    ? `${Math.round(invocationStats.reduce((sum, d) => sum + d.avg_duration_ms, 0) / invocationStats.length)} ms`
                    : '-'}
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">整体成功率</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">
                  {totalInvocations > 0
                    ? `${Math.round((successfulInvocations / totalInvocations) * 100)}%`
                    : '-'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
