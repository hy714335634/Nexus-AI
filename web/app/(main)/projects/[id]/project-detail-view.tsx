'use client';

import Link from 'next/link';
import { useProjectDetail } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { StatusBadge } from '@components/status-badge';
import { formatDateTime } from '@/lib/formatters';
import type { ProjectStatus, BuildStage } from '@/types/api';

interface ProjectDetailViewProps {
  readonly projectId: string;
}

export function ProjectDetailView({ projectId }: ProjectDetailViewProps) {
  const { data, isLoading, isError, refetch, isFetching } = useProjectDetail(projectId);

  if (isLoading) {
    return <LoadingState message="加载项目详情…" />;
  }

  if (isError) {
    return <ErrorState description="无法加载项目详情" onRetry={() => refetch()} />;
  }

  if (!data) {
    return <ErrorState title="未找到项目" description={`项目 ${projectId} 不存在或已被移除。`} />;
  }

  const projectStatus = data.status as ProjectStatus;
  const currentStage = data.currentStage as BuildStage | undefined;

  return (
    <section style={{ display: 'grid', gap: '24px' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '24px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'grid', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 600 }}>{data.name ?? data.id}</h1>
            <StatusBadge status={projectStatus} />
            {currentStage ? <StatusBadge status={currentStage} /> : null}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--muted)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <span>项目 ID：{data.id}</span>
            <span>进度：{data.progress}%</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => refetch()}
            style={{
              padding: '10px 16px',
              borderRadius: '12px',
              border: '1px solid rgba(79, 70, 229, 0.45)',
              background: 'rgba(79, 70, 229, 0.16)',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            {isFetching ? '刷新中…' : '刷新状态'}
          </button>
          <Link
            href={`/projects/${projectId}/deploy`}
            style={{
              padding: '12px 20px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #2563eb, #4f46e5)',
              color: '#fff',
              fontWeight: 600,
            }}
          >
            部署到 AgentCore
          </Link>
        </div>
      </header>

      <div
        style={{
          display: 'grid',
          gap: '24px',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          alignItems: 'start',
        }}
      >
        <section
          style={{
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '24px',
            background: 'rgba(14, 16, 24, 0.92)',
            display: 'grid',
            gap: '16px',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '20px' }}>项目信息</h2>
          <div style={{ display: 'grid', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--muted)' }}>状态</span>
              <StatusBadge status={projectStatus} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--muted)' }}>进度</span>
              <span>{data.progress}%</span>
            </div>
            {currentStage && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--muted)' }}>当前阶段</span>
                <span>{currentStage}</span>
              </div>
            )}
            {data.currentAgent && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--muted)' }}>当前 Agent</span>
                <span>{data.currentAgent}</span>
              </div>
            )}
            {data.startedAt && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--muted)' }}>开始时间</span>
                <span>{formatDateTime(data.startedAt)}</span>
              </div>
            )}
            {data.estimatedCompletion && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--muted)' }}>预计完成</span>
                <span>{formatDateTime(data.estimatedCompletion)}</span>
              </div>
            )}
          </div>
        </section>

        <aside style={{ display: 'grid', gap: '24px' }}>
          {data.currentWork && (
            <section
              style={{
                borderRadius: '16px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                padding: '24px',
                background: 'rgba(14, 16, 24, 0.92)',
                display: 'grid',
                gap: '16px',
              }}
            >
              <h2 style={{ margin: 0, fontSize: '20px' }}>当前工作</h2>
              <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.6, color: 'var(--muted)' }}>
                {data.currentWork}
              </p>
            </section>
          )}

          {data.errorInfo && Object.keys(data.errorInfo).length > 0 && (
            <section
              style={{
                borderRadius: '16px',
                border: '1px solid rgba(248, 113, 113, 0.45)',
                background: 'rgba(127, 29, 29, 0.18)',
                padding: '20px',
                display: 'grid',
                gap: '8px',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '18px', color: '#fca5a5' }}>错误信息</h3>
              <pre style={{ margin: 0, fontSize: '12px', lineHeight: 1.6, overflow: 'auto' }}>
                {JSON.stringify(data.errorInfo, null, 2)}
              </pre>
            </section>
          )}
        </aside>
      </div>
    </section>
  );
}
