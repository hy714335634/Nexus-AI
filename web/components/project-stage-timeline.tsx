import { StatusBadge } from './status-badge';
import type { StageData } from '@/types/api';
import { formatDateTime, formatDuration, formatRelativeTime } from '@/lib/formatters';

interface ProjectStageTimelineProps {
  readonly stages: StageData[];
  readonly activeStage?: StageData;
}

function computeDuration(stage: StageData): string {
  if (stage.duration_seconds != null) {
    return formatDuration(stage.duration_seconds);
  }

  if (stage.started_at && stage.completed_at) {
    const start = new Date(stage.started_at).getTime();
    const end = new Date(stage.completed_at).getTime();
    if (!Number.isNaN(start) && !Number.isNaN(end) && end >= start) {
      const diffSeconds = Math.round((end - start) / 1000);
      return formatDuration(diffSeconds);
    }
  }

  if (stage.status === 'running' && stage.started_at) {
    const start = new Date(stage.started_at).getTime();
    const now = Date.now();
    if (!Number.isNaN(start) && now >= start) {
      const diffSeconds = Math.round((now - start) / 1000);
      return formatDuration(diffSeconds);
    }
  }

  return '未知';
}

export function ProjectStageTimeline({ stages, activeStage }: ProjectStageTimelineProps) {
  if (!stages.length) {
    return (
      <div
        style={{
          padding: '24px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(14, 16, 24, 0.92)',
        }}
      >
        暂无阶段信息。
      </div>
    );
  }

  return (
    <ol
      style={{
        margin: 0,
        padding: 0,
        listStyle: 'none',
        display: 'grid',
        gap: '16px',
      }}
    >
      {stages.map((stage, index) => {
        const isActive = activeStage && activeStage.stage === stage.stage;
        const durationLabel = computeDuration(stage);
        const startedAt = formatDateTime(stage.started_at);
        const completedAt = formatDateTime(stage.completed_at);
        const relativeStarted = formatRelativeTime(stage.started_at);
        const relativeCompleted = formatRelativeTime(stage.completed_at);

        return (
          <li
            key={`${stage.stage}-${index}`}
            style={{
              display: 'grid',
              gap: '12px',
              borderRadius: '16px',
              border: isActive
                ? '1px solid rgba(34, 211, 238, 0.5)'
                : '1px solid rgba(255, 255, 255, 0.08)',
              background: isActive
                ? 'rgba(13, 148, 136, 0.12)'
                : 'rgba(17, 20, 30, 0.85)',
              padding: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ display: 'grid', gap: '4px' }}>
                <div style={{ fontSize: '15px', fontWeight: 600 }}>{stage.stage_name_cn}</div>
                <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{stage.stage_name}</div>
              </div>
              <StatusBadge status={stage.status} />
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '12px',
                fontSize: '13px',
                color: 'var(--muted)',
              }}
            >
              <div>
                <div>开始：{startedAt}</div>
                {stage.started_at ? <div>（{relativeStarted}）</div> : null}
              </div>
              <div>
                <div>完成：{completedAt}</div>
                {stage.completed_at ? <div>（{relativeCompleted}）</div> : null}
              </div>
              <div>
                <div>耗时：{durationLabel}</div>
                {stage.logs && stage.logs.length ? (
                  <div>日志条目：{stage.logs.length}</div>
                ) : null}
              </div>
            </div>

            {stage.error_message ? (
              <div
                style={{
                  padding: '12px',
                  borderRadius: '12px',
                  border: '1px solid rgba(248, 113, 113, 0.45)',
                  background: 'rgba(127, 29, 29, 0.18)',
                  fontSize: '13px',
                  lineHeight: 1.6,
                }}
              >
                <div style={{ fontWeight: 600, color: '#fca5a5' }}>错误信息</div>
                <div>{stage.error_message}</div>
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
