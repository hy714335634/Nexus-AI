'use client';

import Link from 'next/link';
import { useProjectDetail } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { StatusBadge } from '@components/status-badge';
import { ProjectMetadataCard } from '@components/project-metadata-card';
import { ProjectStageTimeline } from '@components/project-stage-timeline';
import { StageLogViewer } from '@components/logs/stage-log-viewer';
import { ProjectArtifactTabs } from '@components/project-artifact-tabs';
import { formatDateTime } from '@/lib/formatters';

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

  const runningStage = data.stages.find((stage) => stage.status === 'running');
  const pendingStage = data.stages.find((stage) => stage.status === 'pending');
  const activeStage = runningStage ?? pendingStage ?? data.stages[0];

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
            <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 600 }}>{data.projectName ?? data.projectId}</h1>
            <StatusBadge status={data.status} />
            {data.currentStage ? <StatusBadge status={data.currentStage} /> : null}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--muted)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <span>项目 ID：{data.projectId}</span>
            <span>最近更新：{formatDateTime(data.updatedAt)}</span>
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

      <ProjectMetadataCard project={data} />
      <ProjectArtifactTabs artifacts={data.artifacts} />

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <h2 style={{ margin: 0, fontSize: '20px' }}>阶段时间线</h2>
            {activeStage ? (
              <span style={{ fontSize: '13px', color: 'var(--muted)' }}>
                当前阶段：{activeStage.stage_name_cn}
              </span>
            ) : null}
          </div>
          <ProjectStageTimeline stages={data.stages} activeStage={activeStage} />
        </section>

        <aside style={{ display: 'grid', gap: '24px' }}>
          <StageLogViewer projectId={projectId} stages={data.stages} activeStageId={activeStage?.stage} />

          <section
            style={{
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '24px',
              background: 'rgba(14, 12, 24, 0.9)',
              display: 'grid',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ margin: 0, fontSize: '20px' }}>Agent 列表</h2>
              <Link
                href={`/projects/${projectId}/deploy`}
                style={{ fontSize: '13px', color: 'var(--muted)', textDecoration: 'underline' }}
              >
                查看部署记录
              </Link>
            </div>
            <div style={{ display: 'grid', gap: '12px' }}>
              {data.agents.map((agent) => (
                <div
                  key={agent.agent_id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '16px 20px',
                    borderRadius: '12px',
                    background: 'rgba(17, 18, 28, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <div style={{ display: 'grid', gap: '4px' }}>
                    <span style={{ fontWeight: 600 }}>{agent.agent_name}</span>
                    <span style={{ fontSize: '12px', color: 'var(--muted)' }}>Agent ID：{agent.agent_id}</span>
                  </div>
                  <StatusBadge status={agent.status} />
                </div>
              ))}
              {!data.agents.length ? (
                <div style={{ fontSize: '13px', color: 'var(--muted)' }}>暂无生成的 Agent。</div>
              ) : null}
            </div>
          </section>

          {data.errorContext?.length ? (
            <section
              style={{
                borderRadius: '16px',
                border: '1px solid rgba(248, 113, 113, 0.35)',
                background: 'rgba(127, 29, 29, 0.16)',
                padding: '20px',
                display: 'grid',
                gap: '8px',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '18px', color: '#fca5a5' }}>错误上下文</h3>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', lineHeight: 1.6 }}>
                {data.errorContext.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {data.lastError ? (
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
              <h3 style={{ margin: 0, fontSize: '18px', color: '#fca5a5' }}>最近错误</h3>
              <p style={{ margin: 0, fontSize: '14px', lineHeight: 1.6 }}>{data.lastError}</p>
            </section>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
