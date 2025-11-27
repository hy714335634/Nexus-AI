'use client';

// Force dynamic rendering for pages using useSearchParams
export const dynamic = 'force-dynamic';

import { Suspense, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import styles from './build.module.css';
import { toast } from 'sonner';
import { useBuildDashboard, useProjectSummaries } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { formatDateTime, formatDuration } from '@/lib/formatters';

type StepVisualStatus = 'completed' | 'current' | 'pending' | 'failed';

interface StepItem {
  readonly id: string;
  readonly title: string;
  readonly icon: string;
  readonly owner?: string;
  readonly description?: string;
  readonly status: StepVisualStatus;
  readonly statusLabel: string;
  readonly startedAt?: string;
  readonly completedAt?: string;
  readonly metadata: string[];
}

const FALLBACK_REQUIREMENT = '暂无需求摘要，等待需求分析阶段输出。';

const STAGE_CATALOG: Array<{
  readonly id: string;
  readonly title: string;
  readonly owner?: string;
  readonly description?: string;
  readonly icon: string;
}> = [
  {
    id: 'orchestrator',
    title: 'Orchestrator · 需求理解',
    owner: 'Orchestrator Agent',
    description: '解析业务场景并拆解交付目标，生成构建蓝图。',
    icon: '🧭',
  },
  {
    id: 'requirements_analyzer',
    title: 'Requirements Analyzer · 需求分析',
    owner: 'Requirements Analyzer',
    description: '深入分析需求约束，补充缺失上下文与验收标准。',
    icon: '📝',
  },
  {
    id: 'system_architect',
    title: 'Architect · 系统设计',
    owner: 'System Architect',
    description: '设计 Agent 组件、记忆策略与工具编排方案。',
    icon: '🧠',
  },
  {
    id: 'agent_designer',
    title: 'Agent Designer · 交互方案',
    owner: 'Agent Designer',
    description: '生成 Agent 角色设定、会话策略与响应格式。',
    icon: '🎨',
  },
  {
    id: 'prompt_engineer',
    title: 'Prompt Engineer · 提示词方案',
    owner: 'Prompt Engineer',
    description: '构建系统提示词、样例对话与记忆胶囊。',
    icon: '🗂️',
  },
  {
    id: 'tools_developer',
    title: 'Tools Engineer · 工具集成',
    owner: 'Tools Engineer',
    description: '实现外部 API 封装、鉴权策略与监控指标。',
    icon: '🛠️',
  },
  {
    id: 'agent_code_developer',
    title: 'Agent Developer · 代码实现',
    owner: 'Agent Developer',
    description: '生成自定义代码、单元测试与部署脚本。',
    icon: '💻',
  },
  {
    id: 'agent_developer_manager',
    title: 'Developer Manager · 开发管理',
    owner: 'Developer Manager',
    description: '协调多角色交付，整合工件并校验质量。',
    icon: '🧩',
  },
  {
    id: 'agent_deployer',
    title: 'Agent Deployer · 部署上线',
    owner: 'Agent Deployer',
    description: '发布至运行环境，执行验证与灰度策略。',
    icon: '🚀',
  },
];

const STATUS_LABEL: Record<StepVisualStatus, string> = {
  completed: '已完成',
  current: '进行中',
  pending: '待开始',
  failed: '构建失败',
};

function Step({ step }: { readonly step: StepItem }) {
  const statusClass =
    step.status === 'completed'
      ? styles.stepCompleted
      : step.status === 'current'
      ? styles.stepCurrent
      : step.status === 'failed'
      ? styles.stepFailed
      : styles.stepPending;

  const iconClass =
    step.status === 'completed'
      ? `${styles.stepIcon} ${styles.iconCompleted}`
      : step.status === 'current'
      ? `${styles.stepIcon} ${styles.iconCurrent}`
      : step.status === 'failed'
      ? `${styles.stepIcon} ${styles.iconFailed}`
      : `${styles.stepIcon} ${styles.iconPending}`;

  return (
    <div className={`${styles.stepItem} ${statusClass}`}>
      <div className={iconClass}>{step.icon}</div>
      <div className={styles.stepContent}>
        <div className={styles.stepTitle}>{step.title}</div>
        {step.description ? <div className={styles.stepMeta}>{step.description}</div> : null}
        <div className={styles.stepMeta}>
          {step.owner ? <span>👥 {step.owner} · </span> : null}
          <span>状态：{step.statusLabel}</span>
          {step.startedAt ? <span> · 开始：{formatDateTime(step.startedAt)}</span> : null}
          {step.completedAt ? <span> · 完成：{formatDateTime(step.completedAt)}</span> : null}
        </div>
        {step.metadata.map((line, index) => (
          <div key={`${step.id}-meta-${index}`} className={styles.stepMeta}>
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function toStringValue(value: unknown): string | undefined {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  }
  return undefined;
}

function formatTokens(value?: number): string {
  if (value == null) {
    return '—';
  }
  return value.toLocaleString();
}

function BuildPageContent() {
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
        <header className={styles.hero}>
          <h1 className={styles.heroTitle}>🛠️ Agent 构建进度</h1>
          <p className={styles.heroSubtitle}>请选择或创建一个项目以查看构建状态</p>
        </header>
        <ErrorState
          title="暂无可用项目"
          description="还没有可用的构建记录，点击下方链接创建一个新的 Agent。"
        />
        <Link
          href="/agents/new"
          style={{
            justifySelf: 'center',
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
    return <LoadingState message="加载构建进度…" />;
  }

  // 区分"加载错误"和"没有数据"两种情况
  if (dashboardError) {
    return (
      <section className={styles.page}>
        <ErrorState
          title="无法加载构建进度"
          description="请稍后重试，或检查后端服务状态。"
          onRetry={() => refetchDashboard()}
        />
      </section>
    );
  }

  // 项目不存在或暂无构建数据 - 显示友好的空状态
  if (!dashboard) {
    return (
      <section className={styles.page}>
        <header className={styles.hero}>
          <h1 className={styles.heroTitle}>🛠️ Agent 构建进度</h1>
          <p className={styles.heroSubtitle}>项目 ID: {projectId}</p>
        </header>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 20px',
          textAlign: 'center',
          color: '#666',
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '8px', color: '#333' }}>
            暂无构建数据
          </h2>
          <p style={{ marginBottom: '24px', maxWidth: '400px' }}>
            该项目尚未开始构建，或构建数据正在生成中。请稍后刷新页面查看。
          </p>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              type="button"
              onClick={() => refetchDashboard()}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                border: '1px solid #ddd',
                background: '#fff',
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              刷新页面
            </button>
            <Link
              href="/"
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #2563eb, #4f46e5)',
                color: '#fff',
                fontWeight: 500,
                textDecoration: 'none',
              }}
            >
              返回首页
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const orderedStages = STAGE_CATALOG.map((entry) => {
    const stage = dashboard.stages.find((item) => item.name === entry.id);
    return {
      catalog: entry,
      stage,
    };
  });

  const firstIncompleteIndex = orderedStages.findIndex(({ stage }) => stage?.status !== 'completed');
  const activeIndex = orderedStages.findIndex(({ stage }) => stage?.status === 'running');

  const steps: StepItem[] = orderedStages.map(({ catalog, stage }, index) => {
    let visualStatus: StepVisualStatus = 'pending';
    if (stage?.status === 'completed') {
      visualStatus = 'completed';
    } else if (stage?.status === 'failed') {
      visualStatus = 'failed';
    } else if (stage?.status === 'running') {
      visualStatus = 'current';
    } else if (firstIncompleteIndex === index || (firstIncompleteIndex === -1 && index === orderedStages.length - 1)) {
      visualStatus = 'current';
    }

    if (visualStatus === 'current' && activeIndex >= 0 && activeIndex !== index) {
      visualStatus = 'pending';
    }

    const metadata = stage?.metadata ?? {};
    const metaLines: string[] = [];

    const efficiency = toStringValue(metadata.efficiency);
    if (efficiency) {
      metaLines.push(`效率：${efficiency}`);
    }

    const docPath = toStringValue(metadata.doc_path);
    if (docPath) {
      metaLines.push(`文档：${docPath}`);
    }

    if (Array.isArray(metadata.artifacts) && metadata.artifacts.length) {
      metaLines.push(`工件：${metadata.artifacts.length} 个`);
    }

    if (stage?.durationSeconds) {
      metaLines.push(`耗时：${formatDuration(Math.round(stage.durationSeconds))}`);
    }

    if (stage?.inputTokens != null || stage?.outputTokens != null) {
      metaLines.push(
        `Token：${formatTokens(stage?.inputTokens ?? 0)} ↔ ${formatTokens(stage?.outputTokens ?? 0)}`,
      );
    }

    if (stage?.toolCalls != null) {
      metaLines.push(`工具调用：${stage.toolCalls}`);
    }

    return {
      id: catalog.id,
      title: catalog.title,
      icon: stage?.status === 'failed' ? '⚠️' : catalog.icon,
      owner: toStringValue(metadata.owner) ?? catalog.owner,
      description: toStringValue(metadata.description) ?? catalog.description,
      status: visualStatus,
      statusLabel: STATUS_LABEL[visualStatus],
      startedAt: stage?.startedAt,
      completedAt: stage?.completedAt,
      metadata: metaLines,
    };
  });

  const completedCount = steps.filter((step) => step.status === 'completed').length;
  const progressValue = Math.round(dashboard.progressPercentage ?? 0);

  const activeStep =
    steps.find((step) => step.status === 'current') ??
    steps.find((step) => step.status === 'pending') ??
    steps[steps.length - 1];

  const requirementText = dashboard.requirement ?? FALLBACK_REQUIREMENT;

  const resources = dashboard.resources ?? [];
  const alertsRaw = dashboard.alerts ?? [];
  const alerts = alertsRaw
    .slice()
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));
  const riskAlertCount = alerts.filter((alert) => alert.level !== 'info').length;

  const metricsCards = [
    { label: '整体构建进度', value: `${progressValue}%` },
    { label: '已完成阶段', value: `${completedCount}` },
    {
      label: '当前阶段',
      value: activeStep ? activeStep.title.replace(/^[0-9.]+\s*/, '') : '待开始',
    },
    {
      label: '风险提醒',
      value: `${riskAlertCount}`,
    },
  ];

  const metricsGrid = [
    {
      label: '总耗时',
      value: dashboard.metrics?.totalDurationSeconds
        ? formatDuration(Math.round(dashboard.metrics.totalDurationSeconds))
        : '—',
    },
    {
      label: '输入 Token',
      value: formatTokens(dashboard.metrics?.inputTokens),
    },
    {
      label: '输出 Token',
      value: formatTokens(dashboard.metrics?.outputTokens),
    },
    {
      label: '工具调用',
      value:
        dashboard.metrics?.toolCalls != null
          ? dashboard.metrics.toolCalls.toString()
          : '—',
    },
  ];

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>
          🛠️ {dashboard.projectName ?? dashboard.projectId} · 构建进度
        </h1>
        <p className={styles.heroSubtitle}>
          实时追踪从需求理解到部署上线的每一个阶段 · 最近更新：{formatDateTime(dashboard.updatedAt)}
        </p>
      </section>

      <section className={styles.requirementCard}>
        <div className={styles.requirementHeader}>
          📝 {dashboard.projectName ?? dashboard.projectId} · 需求摘要
        </div>
        <div className={styles.requirementBody} style={{ whiteSpace: 'pre-line' }}>
          {requirementText}
        </div>
      </section>

      <section className={styles.progressOverview}>
        {metricsCards.map((metric) => (
          <div key={metric.label} className={styles.progressCard}>
            <div className={styles.progressValue}>{metric.value}</div>
            <div className={styles.progressLabel}>{metric.label}</div>
          </div>
        ))}
      </section>

      <section className={styles.stepSection}>
        <div className={styles.stepHeader}>
          <h3>构建阶段总览</h3>
          <span>
            共 {steps.length} 个阶段 · 当前进行到第 {completedCount + 1} 阶段
          </span>
        </div>
        <div className={styles.stepList}>
          {steps.map((step) => (
            <Step key={step.id} step={step} />
          ))}
        </div>
      </section>

      <div className={styles.layoutColumns}>
        <section className={styles.currentWork}>
          <h3 className={styles.sectionTitle}>
            当前工作 · {activeStep ? activeStep.title : '等待下一阶段'}
          </h3>
          <div className={styles.workSummary}>
            {activeStep?.description ?? '暂无该阶段的详细描述。'}
          </div>

          <div className={styles.metricsGrid}>
            {metricsGrid.map((metric) => (
              <div key={metric.label} className={styles.metricCard}>
                <div className={styles.metricValue}>{metric.value}</div>
                <div>{metric.label}</div>
              </div>
            ))}
          </div>

          <div>
            <h4 style={{ marginBottom: '12px', color: '#555' }}>依赖资源</h4>
            <div className={styles.resourceList}>
              {resources.length ? (
                resources.map((resource, index) => (
                  <div key={resource.id ?? `resource-${index}`} className={styles.resourceItem}>
                    <span role="img" aria-hidden="true">
                      📎
                    </span>
                    <div style={{ flex: 1 }}>
                      <div>{resource.label}</div>
                      {resource.owner ? (
                        <div style={{ fontSize: '0.8rem', color: '#666' }}>负责人：{resource.owner}</div>
                      ) : null}
                    </div>
                    <span className={styles.resourceBadge}>{resource.status ?? '待更新'}</span>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.85rem', color: '#777' }}>暂无资源记录。</div>
              )}
            </div>
          </div>

          <div className={styles.nextActions}>
            <button
              type="button"
              className={styles.primaryAction}
              onClick={() => toast.success('已安排阶段评审')}
            >
              安排阶段评审
            </button>
            <button
              type="button"
              className={styles.secondaryAction}
              onClick={() => toast('将生成最新报告草稿')}
            >
              导出阶段报告
            </button>
          </div>
        </section>

        <aside className={styles.notifications}>
          <h3 className={styles.sectionTitle}>实时提醒</h3>
          <div className={styles.notificationList}>
            {alerts.length ? (
              alerts.map((notification) => (
                <div key={notification.id} className={styles.notificationItem}>
                  <div className={styles.notificationTitle}>{notification.message}</div>
                  <div className={styles.notificationMeta}>
                    时间：{formatDateTime(notification.createdAt)} · 类型：{notification.level.toUpperCase()}
                  </div>
                  {notification.metadata?.details ? (
                    <div>{String(notification.metadata.details)}</div>
                  ) : null}
                </div>
              ))
            ) : (
              <div style={{ fontSize: '0.85rem', color: '#777' }}>暂无提醒，构建流程正常进行中。</div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function BuildPage() {
  return (
    <Suspense fallback={<LoadingState message="加载页面…" />}>
      <BuildPageContent />
    </Suspense>
  );
}
