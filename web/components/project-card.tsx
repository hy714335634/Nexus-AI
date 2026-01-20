import Link from 'next/link';
import { StatusBadge } from './status-badge';
import type { ProjectSummary } from '@/lib/projects';
import type { ProjectStatus, BuildStage } from '@/types/api';

interface ProjectCardProps {
  readonly project: ProjectSummary;
}

function formatDate(input?: string) {
  if (!input) {
    return '未知';
  }

  const date = new Date(input);
  if (Number.isNaN(date.valueOf())) {
    return input;
  }
  return date.toLocaleString();
}

export function ProjectCard({ project }: ProjectCardProps) {
  const progressLabel = `${Math.round(project.progress)}%`;
  const updatedAt = formatDate(project.updatedAt);
  const projectStatus = project.status as ProjectStatus;
  const currentStage = project.currentStage as BuildStage | undefined;

  return (
    <article
      style={{
        padding: '24px',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'linear-gradient(160deg, rgba(9, 10, 17, 0.92), rgba(9, 13, 27, 0.78))',
        display: 'grid',
        gap: '16px',
      }}
    >
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'grid', gap: '8px' }}>
          <div style={{ fontSize: '18px', fontWeight: 600 }}>{project.name ?? project.id}</div>
          <div style={{ fontSize: '13px', color: 'var(--muted)' }}>最新更新：{updatedAt}</div>
        </div>
        <StatusBadge status={projectStatus} />
      </header>

      <div style={{ display: 'grid', gap: '8px' }}>
        <div style={{ fontSize: '13px', color: 'var(--muted)' }}>当前阶段</div>
        {currentStage ? <StatusBadge status={currentStage} /> : <span>未知阶段</span>}
      </div>

      <div style={{ display: 'grid', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--muted)' }}>
          <span>进度</span>
          <span>{progressLabel}</span>
        </div>
        <div
          style={{
            height: '6px',
            borderRadius: '999px',
            background: 'rgba(148, 163, 184, 0.2)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: progressLabel,
              background: 'linear-gradient(90deg, #4f46e5, #818cf8)',
            }}
          />
        </div>
      </div>

      <footer
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <span style={{ fontSize: '13px', color: 'var(--muted)' }}>
          Agents：{project.agentCount ?? 0}
        </span>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <Link
            href={`/projects/${project.id}`}
            style={{
              padding: '8px 16px',
              borderRadius: '999px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              fontSize: '13px',
            }}
          >
            查看详情
          </Link>
          <Link
            href={`/projects/${project.id}/deploy`}
            style={{
              padding: '8px 16px',
              borderRadius: '999px',
              background: 'rgba(79, 70, 229, 0.16)',
              border: '1px solid rgba(79, 70, 229, 0.4)',
              fontSize: '13px',
            }}
          >
            部署
          </Link>
        </div>
      </footer>
    </article>
  );
}
