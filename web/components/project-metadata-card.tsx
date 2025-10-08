import { StatusBadge } from './status-badge';
import type { ProjectDetail } from '@/types/projects';
import { formatDateTime, formatRelativeTime } from '@/lib/formatters';

interface ProjectMetadataCardProps {
  readonly project: ProjectDetail;
}

export function ProjectMetadataCard({ project }: ProjectMetadataCardProps) {
  const startedAt = formatDateTime(project.startedAt);
  const estimatedCompletion = formatDateTime(project.estimatedCompletion);
  const updatedAt = formatDateTime(project.updatedAt);
  const relativeUpdated = formatRelativeTime(project.updatedAt);

  return (
    <section
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
      }}
    >
      <article
        style={{
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '20px',
          background: 'rgba(12, 14, 24, 0.9)',
          display: 'grid',
          gap: '12px',
        }}
      >
        <div style={{ fontSize: '13px', color: 'var(--muted)' }}>项目进度</div>
        <div style={{ fontSize: '32px', fontWeight: 700 }}>{Math.round(project.progressPercentage)}%</div>
        <div
          style={{
            height: '8px',
            borderRadius: '999px',
            background: 'rgba(148, 163, 184, 0.2)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.round(project.progressPercentage)}%`,
              background: 'linear-gradient(90deg, #22d3ee, #6366f1)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <StatusBadge status={project.status} />
          {project.currentStage ? <StatusBadge status={project.currentStage} /> : null}
        </div>
      </article>

      <article
        style={{
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '20px',
          background: 'rgba(12, 14, 24, 0.9)',
          display: 'grid',
          gap: '8px',
        }}
      >
        <div style={{ fontSize: '13px', color: 'var(--muted)' }}>时间信息</div>
        <div style={{ fontSize: '14px' }}>
          <span style={{ color: 'var(--muted)' }}>开始时间：</span>
          {startedAt}
        </div>
        <div style={{ fontSize: '14px' }}>
          <span style={{ color: 'var(--muted)' }}>预计完成：</span>
          {estimatedCompletion}
        </div>
        <div style={{ fontSize: '14px' }}>
          <span style={{ color: 'var(--muted)' }}>最近更新：</span>
          {updatedAt}（{relativeUpdated}）
        </div>
      </article>

      <article
        style={{
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '20px',
          background: 'rgba(10, 12, 20, 0.95)',
          display: 'grid',
          gap: '10px',
        }}
      >
        <div style={{ fontSize: '13px', color: 'var(--muted)' }}>构建详情</div>
        <div style={{ fontSize: '14px', color: '#f8fafc' }}>项目 ID：{project.projectId}</div>
        <div style={{ fontSize: '14px', color: '#f8fafc' }}>构建阶段：{project.currentStage ?? '未知'}</div>
        <div style={{ fontSize: '14px', color: '#f8fafc' }}>Agent 数量：{project.agentCount ?? project.agents.length}</div>
      </article>
    </section>
  );
}
