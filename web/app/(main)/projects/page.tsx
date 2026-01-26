'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, Button, Input, Empty, Progress, Badge } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useProjectsV2 } from '@/hooks/use-projects-v2';
import { formatRelativeTime, truncate } from '@/lib/utils';
import {
  FolderKanban,
  Plus,
  Search,
  Clock,
  CheckCircle2,
  XCircle,
  Pause,
  Loader2,
} from 'lucide-react';
import type { ProjectStatus } from '@/types/api-v2';

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjectsV2({ limit: 100 });
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | 'all'>('all');

  const filteredProjects = projects?.filter((project) => {
    const name = project.project_name || project.project_id;
    const matchesSearch = name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];

  const statusCounts = {
    all: projects?.length || 0,
    building: projects?.filter((p) => p.status === 'building').length || 0,
    completed: projects?.filter((p) => p.status === 'completed').length || 0,
    failed: projects?.filter((p) => p.status === 'failed').length || 0,
    pending: projects?.filter((p) => p.status === 'pending').length || 0,
    queued: projects?.filter((p) => p.status === 'queued').length || 0,
    paused: projects?.filter((p) => p.status === 'paused').length || 0,
  };

  const statusFilters: { key: ProjectStatus | 'all'; label: string; icon?: React.ElementType }[] = [
    { key: 'all', label: '全部' },
    { key: 'building', label: '构建中', icon: Loader2 },
    { key: 'completed', label: '已完成', icon: CheckCircle2 },
    { key: 'failed', label: '失败', icon: XCircle },
    { key: 'paused', label: '已暂停', icon: Pause },
  ];

  return (
    <div className="page-container">
      <Header
        title="项目"
        description="管理 Agent 构建项目"
        actions={
          <Link href="/agents/new">
            <Button>
              <Plus className="w-4 h-4" />
              新建项目
            </Button>
          </Link>
        }
      />

      <div className="page-content">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="搜索项目..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {statusFilters.map((filter) => (
              <button
                key={filter.key}
                onClick={() => setStatusFilter(filter.key)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5 ${
                  statusFilter === filter.key
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                {filter.icon && <filter.icon className={`w-4 h-4 ${filter.key === 'building' ? 'animate-spin' : ''}`} />}
                {filter.label}
                <span className="text-xs">({statusCounts[filter.key as keyof typeof statusCounts] || 0})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Project List */}
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} padding="none">
                <div className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gray-100 animate-pulse" />
                    <div className="flex-1">
                      <div className="h-5 w-48 bg-gray-100 rounded animate-pulse mb-2" />
                      <div className="h-4 w-32 bg-gray-100 rounded animate-pulse" />
                    </div>
                    <div className="w-32 h-2 bg-gray-100 rounded animate-pulse" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : filteredProjects.length === 0 ? (
          <Empty
            icon={FolderKanban}
            title={searchQuery || statusFilter !== 'all' ? '没有找到匹配的项目' : '暂无项目'}
            description={
              searchQuery || statusFilter !== 'all'
                ? '尝试调整搜索条件或筛选器'
                : '创建您的第一个 Agent 构建项目'
            }
            action={
              !searchQuery && statusFilter === 'all' && (
                <Link href="/agents/new">
                  <Button>
                    <Plus className="w-4 h-4" />
                    新建项目
                  </Button>
                </Link>
              )
            }
          />
        ) : (
          <div className="space-y-4">
            {filteredProjects.map((project) => (
              <Link key={project.project_id} href={`/projects/${project.project_id}`}>
                <Card hover padding="none">
                  <div className="p-6">
                    <div className="flex items-center gap-6">
                      <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
                        <FolderKanban className="w-6 h-6 text-primary-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-semibold text-gray-900 truncate">
                            {project.project_name || `项目 ${project.project_id.slice(0, 8)}`}
                          </h3>
                          <StatusBadge status={project.status as any} size="sm" />
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {formatRelativeTime(project.updated_at || project.created_at)}
                          </span>
                          {project.current_stage && (
                            <span>当前阶段: {project.current_stage}</span>
                          )}
                        </div>
                      </div>
                      <div className="w-40 flex-shrink-0">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-gray-500">进度</span>
                          <span className="font-medium text-gray-900">{Math.round(project.progress)}%</span>
                        </div>
                        <Progress
                          value={project.progress}
                          variant={
                            project.status === 'completed' ? 'success' :
                            project.status === 'failed' ? 'error' :
                            project.status === 'building' ? 'default' : 'default'
                          }
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
