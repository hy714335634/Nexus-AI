'use client';

import { Badge } from '@/components/ui/badge';
import type { ProjectStatus, StageStatus, AgentStatus } from '@/types/api';
import type { AgentStatus as AgentStatusV2 } from '@/types/api-v2';

interface StatusBadgeProps {
  status: ProjectStatus | StageStatus | AgentStatus | AgentStatusV2;
  size?: 'sm' | 'md';
}

const statusConfig: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  // Project status
  pending: { label: '等待中', variant: 'default' },
  building: { label: '构建中', variant: 'info' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失败', variant: 'error' },
  paused: { label: '已暂停', variant: 'warning' },
  // Stage status
  running: { label: '运行中', variant: 'info' },
  // Agent status
  offline: { label: '离线', variant: 'default' },
  error: { label: '错误', variant: 'error' },
  deploying: { label: '部署中', variant: 'info' },
};

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, variant: 'default' as const };
  
  return (
    <Badge variant={config.variant} size={size}>
      {status === 'building' || status === 'running' || status === 'deploying' ? (
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
          {config.label}
        </span>
      ) : (
        config.label
      )}
    </Badge>
  );
}
