'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import styles from './graph.module.css';
import { useBuildDashboard, useProjectSummaries } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { formatDateTime, formatDuration } from '@/lib/formatters';
import type { BuildDashboardGraphEdge, BuildDashboardGraphNode, BuildDashboardStage } from '@/types/projects';

type StageStatus = BuildDashboardStage['status'];

interface StageDefinition {
  readonly id: string;
  readonly title: string;
}

interface NodeView {
  readonly id: string;
  readonly label: string;
  readonly icon: string;
  readonly status: StageStatus;
  readonly statusClass: string;
  readonly typeLabel: string;
}

interface EdgeView {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  readonly kind?: string;
}

const STAGE_DEFINITIONS: StageDefinition[] = [
  { id: 'orchestrator', title: 'Orchestrator · 需求理解' },
  { id: 'requirements_analyzer', title: 'Requirements Analyzer · 需求分析' },
  { id: 'system_architect', title: 'Architect · 系统设计' },
  { id: 'prompt_engineer', title: 'Prompt Engineer · 提示词方案' },
  { id: 'tools_developer', title: 'Tools Engineer · 工具集成' },
  { id: 'agent_code_developer', title: 'Agent Developer · 代码实现' },
  { id: 'agent_developer_manager', title: 'Developer Manager · 开发管理' },
  { id: 'agent_deployer', title: 'Agent Deployer · 部署上线' },
];

const NODE_ICONS: Record<string, string> = {
  orchestrator: '🟦',
  execution: '🟩',
  interaction: '🟧',
  alert: '🟥',
};

const STATUS_CLASS: Record<StageStatus, string> = {
  completed: 'Completed',
  running: 'Running',
  pending: 'Pending',
  failed: 'Failed',
};

const STATUS_LABEL: Record<StageStatus, string> = {
  completed: '已完成',
  running: '进行中',
  pending: '待开始',
  failed: '构建失败',
};

function toStringValue(value: unknown): string | undefined {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  }
  return undefined;
}

function mapNode(
  node: BuildDashboardGraphNode,
  stage: BuildDashboardStage | undefined,
  fallbackTitle: string,
): NodeView {
  const status: StageStatus = node.status ?? stage?.status ?? 'pending';
  const icon = NODE_ICONS[node.type ?? ''] ?? NODE_ICONS[stage ? 'execution' : 'orchestrator'] ?? '🟦';
  const label = toStringValue(node.label) ?? fallbackTitle;
  const typeLabel = (() => {
    switch (node.type) {
      case 'orchestrator':
        return '控制节点';
      case 'execution':
        return '执行节点';
      case 'interaction':
        return '交互节点';
      case 'alert':
        return '风险节点';
      default:
        return '阶段节点';
    }
  })();

  return {
    id: node.id,
    label,
    icon,
    status,
    statusClass: STATUS_CLASS[status] ?? 'Pending',
    typeLabel,
  };
}

function buildFallbackGraph(): { nodes: BuildDashboardGraphNode[]; edges: BuildDashboardGraphEdge[] } {
  const nodes = STAGE_DEFINITIONS.map<BuildDashboardGraphNode>((stage) => ({
    id: stage.id,
    label: stage.title,
    type: stage.id === 'orchestrator' ? 'orchestrator' : 'execution',
    status: stage.id === 'orchestrator' ? 'completed' : 'pending',
  }));

  const edges: BuildDashboardGraphEdge[] = [];
  for (let index = 0; index < STAGE_DEFINITIONS.length - 1; index += 1) {
    edges.push({
      source: STAGE_DEFINITIONS[index].id,
      target: STAGE_DEFINITIONS[index + 1].id,
      kind: index >= 1 && index <= 3 ? 'parallel-ready' : 'serial',
    });
  }

  return { nodes, edges };
}

export default function BuildGraphPage() {
  const searchParams = useSearchParams();
  const requestedProjectId = searchParams?.get('projectId') ?? undefined;

  const {
    data: projectSummaries,
    isLoading: summariesLoading,
    isError: summariesError,
  } = useProjectSummaries();

  const projectId = useMemo(() => {
    if (requestedProjectId) {
      return requestedProjectId;
    }
    if (!projectSummaries?.length) {
      return undefined;
    }
    const building = projectSummaries.find((project) => project.status === 'building');
    return building?.projectId ?? projectSummaries[0]?.projectId;
  }, [requestedProjectId, projectSummaries]);

  const {
    data: dashboard,
    isLoading: dashboardLoading,
    isError: dashboardError,
    refetch: refetchDashboard,
  } = useBuildDashboard(projectId ?? '', {
    enabled: Boolean(projectId),
  });

  if (summariesLoading) {
    return <LoadingState message="加载项目列表…" />;
  }

  if (summariesError) {
    return <ErrorState description="无法加载项目列表，请稍后重试。" />;
  }

  if (!projectId) {
    return (
      <section className={styles.page}>
        <ErrorState
          title="暂未找到构建项目"
          description="请先创建一个构建会话，再查看拓扑图。"
        />
        <Link
          href="/agents/new"
          style={{
            justifySelf: 'flex-start',
            padding: '12px 24px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #2563eb, #4f46e5)',
            color: '#fff',
            fontWeight: 600,
          }}
        >
          新建代理构建任务
        </Link>
      </section>
    );
  }

  if (dashboardLoading && !dashboard) {
    return <LoadingState message="加载拓扑图…" />;
  }

  if (dashboardError || !dashboard) {
    return (
      <section className={styles.page}>
        <ErrorState
          title="无法加载工作流拓扑"
          description="请稍后重试，或检查后端服务状态。"
          onRetry={() => refetchDashboard()}
        />
      </section>
    );
  }

  const stageMap = new Map<string, BuildDashboardStage>();
  dashboard.stages.forEach((stage) => stageMap.set(stage.name, stage));

  const graphSource =
    dashboard.workflowGraphNodes.length || dashboard.workflowGraphEdges.length
      ? {
          nodes: dashboard.workflowGraphNodes,
          edges: dashboard.workflowGraphEdges,
        }
      : buildFallbackGraph();

  const nodeViews: NodeView[] = graphSource.nodes.map((node) => {
    const stage = stageMap.get(node.id);
    const fallbackTitle =
      STAGE_DEFINITIONS.find((definition) => definition.id === node.id)?.title ?? node.id;
    return mapNode(node, stage, fallbackTitle);
  });

  const edgeViews: EdgeView[] = graphSource.edges.map((edge, index) => ({
    id: `${edge.source}->${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    kind: edge.kind,
  }));

  const keyPath = STAGE_DEFINITIONS.filter((definition) => stageMap.has(definition.id)).map(
    (definition) => definition.title.split('·')[0]?.trim() ?? definition.title,
  );

  const riskAlerts = dashboard.alerts.filter((alert) => alert.level !== 'info');
  const metricsList = [
    `累计耗时：${
      dashboard.metrics?.totalDurationSeconds
        ? formatDuration(Math.round(dashboard.metrics.totalDurationSeconds))
        : '—'
    }`,
    `输入 Token：${
      dashboard.metrics?.inputTokens != null ? dashboard.metrics.inputTokens.toLocaleString() : '—'
    }`,
    `输出 Token：${
      dashboard.metrics?.outputTokens != null ? dashboard.metrics.outputTokens.toLocaleString() : '—'
    }`,
    `工具调用：${
      dashboard.metrics?.toolCalls != null ? dashboard.metrics.toolCalls.toLocaleString() : '—'
    }`,
  ];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.title}>
          🕸️ {dashboard.projectName ?? dashboard.projectId} · 工作流拓扑图
        </div>
        <div className={styles.actions}>
          <Link href="/build" className={styles.button}>
            返回构建进度
          </Link>
          <Link href="/build/modules" className={styles.button}>
            模块总览
          </Link>
        </div>
      </div>

      <section className={styles.canvasWrapper}>
        <div className={styles.legend}>
          <span className={styles.legendItem}>🟦 Orchestrator / 控制节点</span>
          <span className={styles.legendItem}>🟩 执行节点 / 工具调用</span>
          <span className={styles.legendItem}>🟧 用户交互 / 手动审批</span>
          <span className={styles.legendItem}>🟥 风险告警 / 回滚通道</span>
        </div>

        <div className={styles.canvas}>
          <div className={styles.nodeGrid}>
            {nodeViews.map((node) => (
              <div
                key={node.id}
                className={`${styles.nodeCard} ${styles[`nodeCard${node.statusClass}`] ?? ''}`}
              >
                <div className={styles.nodeIcon}>{node.icon}</div>
                <div className={styles.nodeLabel}>{node.label}</div>
                <div className={styles.nodeType}>{node.typeLabel}</div>
                <div className={styles.nodeStatus}>{node.status === 'completed' ? '已完成' : STATUS_LABEL[node.status] ?? '待开始'}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>关键路径洞察</div>
          <div className={styles.list}>
            {keyPath.length ? (
              <div>• {keyPath.join(' → ')}</div>
            ) : (
              <div>• 暂无关键路径，请稍后查看。</div>
            )}
            <div>• 当前阶段：{stageMap.get('agent_deployer')?.status === 'completed' ? '已部署' : '正在推进'}</div>
            <div>• 最近更新：{formatDateTime(dashboard.updatedAt)}</div>
          </div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>风险与回滚策略</div>
          <div className={styles.list}>
            {riskAlerts.length ? (
              riskAlerts.map((alert) => (
                <div key={alert.id}>• {alert.message}</div>
              ))
            ) : (
              <div>• 暂无风险提醒。</div>
            )}
          </div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>并行依赖与边</div>
          <div className={styles.edgeList}>
            {edgeViews.length ? (
              edgeViews.map((edge) => (
                <div key={edge.id} className={styles.edgeItem}>
                  {edge.source} → {edge.target}
                  {edge.kind ? ` · ${edge.kind}` : ''}
                </div>
              ))
            ) : (
              <div className={styles.edgeItem}>暂无连接信息</div>
            )}
          </div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardTitle}>执行指标</div>
          <div className={styles.list}>
            {metricsList.map((item) => (
              <div key={item}>• {item}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
