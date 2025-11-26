import type { AgentStatus, ProjectStatus, StageStatus, BuildStage } from '@/types/api';

type Status = AgentStatus | ProjectStatus | StageStatus | BuildStage;

type Variant = 'neutral' | 'success' | 'warning' | 'danger';

interface StatusBadgeProps {
  readonly status: Status;
}

const STATUS_VARIANT: Record<Status, Variant> = {
  pending: 'neutral',
  building: 'warning',
  completed: 'success',
  failed: 'danger',
  paused: 'warning',
  running: 'success',
  offline: 'neutral',
  error: 'danger',
  agent_design: 'neutral',
  agent_deployer: 'neutral',
  agent_developer_manager: 'neutral',
  orchestrator: 'neutral',
  requirements_analysis: 'neutral',
  system_architecture: 'neutral',
};

const LABELS: Record<Status, string> = {
  pending: '等待中',
  building: '构建中',
  completed: '已完成',
  failed: '失败',
  paused: '已暂停',
  running: '运行中',
  offline: '离线',
  error: '错误',
  agent_design: 'Agent 设计',
  agent_deployer: '部署中',
  agent_developer_manager: '开发管理',
  orchestrator: '编排器',
  requirements_analysis: '需求分析',
  system_architecture: '系统架构',
};

const VARIANT_STYLE: Record<Variant, { text: string; background: string }> = {
  neutral: { text: '#cbd5f5', background: 'rgba(148, 163, 184, 0.15)' },
  success: { text: '#4ade80', background: 'rgba(22, 163, 74, 0.15)' },
  warning: { text: '#facc15', background: 'rgba(234, 179, 8, 0.12)' },
  danger: { text: '#f87171', background: 'rgba(248, 113, 113, 0.12)' },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const variant = STATUS_VARIANT[status] ?? 'neutral';
  const styles = VARIANT_STYLE[variant];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        fontSize: '12px',
        fontWeight: 600,
        color: styles.text,
        background: styles.background,
      }}
    >
      <span style={{ fontSize: '16px', lineHeight: 1 }} aria-hidden="true">
        ⦿
      </span>
      {LABELS[status] ?? status}
    </span>
  );
}
