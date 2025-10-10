'use client';

import { useMemo, useState } from 'react';
import { useProjectSummaries } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { ProjectGrid } from '@components/project-grid';
import type { ProjectSummary } from '@/types/projects';

function applyFilter(projects: ProjectSummary[], statusFilter: string, keyword: string) {
  const normalized = keyword.trim().toLowerCase();
  return projects.filter((project) => {
    const statusMatch = statusFilter === 'all' || project.status === statusFilter;
    const keywordMatch =
      !normalized ||
      project.projectId.toLowerCase().includes(normalized) ||
      (project.projectName ?? '').toLowerCase().includes(normalized);
    return statusMatch && keywordMatch;
  });
}

export function ProjectsView() {
  const [statusFilter, setStatusFilter] = useState<'all' | 'building' | 'completed' | 'failed'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const { data, isLoading, isError, refetch, isFetching } = useProjectSummaries();

  const filteredProjects = useMemo(() => applyFilter(data ?? [], statusFilter, searchTerm), [data, statusFilter, searchTerm]);

  if (isLoading) {
    return <LoadingState message="加载项目列表…" />;
  }

  if (isError) {
    return <ErrorState description="无法加载项目列表" onRetry={() => refetch()} />;
  }

  return (
    <section style={{ display: 'grid', gap: '24px' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'grid', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>构建项目</h1>
            <span style={{ fontSize: '13px', color: 'var(--muted)' }}>共 {filteredProjects.length} 个</span>
          </div>
          <p style={{ margin: 0, fontSize: '14px', color: 'var(--muted)' }}>
            追踪端到端构建状态、阶段进度和部署准备情况。
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            gap: '12px',
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          <input
            type="search"
            placeholder="按名称或 ID 搜索"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            style={{
              padding: '8px 12px',
              background: 'rgba(255, 255, 255, 0.04)',
              color: '#fff',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              minWidth: '220px',
            }}
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}
            style={{
              padding: '8px 12px',
              background: 'rgba(255, 255, 255, 0.04)',
              color: '#fff',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
            }}
          >
            <option value="all">全部状态</option>
            <option value="building">构建中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
          <button
            type="button"
            onClick={() => refetch()}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid rgba(79, 70, 229, 0.5)',
              background: 'rgba(79, 70, 229, 0.16)',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            {isFetching ? '刷新中…' : '刷新列表'}
          </button>
        </div>
      </header>

      <ProjectGrid projects={filteredProjects} />
    </section>
  );
}
