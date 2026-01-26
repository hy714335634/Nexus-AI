'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import styles from './modules.module.css';
import { toast } from 'sonner';
import { useBuildDashboard, useProjectSummaries } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { formatDateTime, formatDuration } from '@/lib/formatters';
import type { BuildDashboardStage, ProjectSummary } from '@/types/projects';

type StageStatus = BuildDashboardStage['status'];

interface StageDefinition {
  readonly id: string;
  readonly title: string;
  readonly owner?: string;
  readonly description?: string;
}

interface TabDefinition {
  readonly id: string;
  readonly label: string;
}

interface PreviewDefinition {
  readonly id: string;
  readonly label: string;
  readonly stageId?: string;
  readonly fallback: string[];
}

interface StageModuleView {
  readonly id: string;
  readonly title: string;
  readonly owner?: string;
  readonly description?: string;
  readonly status: StageStatus;
  readonly statusLabel: string;
  readonly statusClass: string;
  readonly startedAt?: string;
  readonly completedAt?: string;
  readonly metrics: string[];
  readonly metadataLines: string[];
}

const STAGE_DEFINITIONS: StageDefinition[] = [
  {
    id: 'orchestrator',
    title: 'Orchestrator · 需求理解',
    owner: 'Orchestrator Agent',
    description: '解析业务场景、分配子任务并输出初始构建蓝图。',
  },
  {
    id: 'requirements_analyzer',
    title: 'Requirements Analyzer · 需求分析',
    owner: 'Requirements Analyzer',
    description: '补全缺失上下文，梳理验收标准与关键指标。',
  },
  {
    id: 'system_architect',
    title: 'Architect · 系统设计',
    owner: 'System Architect',
    description: '定义 Agent 组件、记忆策略、外部系统集成方案。',
  },
  {
    id: 'prompt_engineer',
    title: 'Prompt Engineer · 提示词方案',
    owner: 'Prompt Engineer',
    description: '构建系统提示词、样例对话与记忆胶囊。',
  },
  {
    id: 'tools_developer',
    title: 'Tools Engineer · 工具集成',
    owner: 'Tools Engineer',
    description: '实现 API 封装、鉴权策略和监控指标。',
  },
  {
    id: 'agent_code_developer',
    title: 'Agent Developer · 代码实现',
    owner: 'Agent Developer',
    description: '生成业务逻辑、单元测试与部署脚本。',
  },
  {
    id: 'agent_developer_manager',
    title: 'Developer Manager · 开发管理',
    owner: 'Developer Manager',
    description: '协调多角色交付、整合工件并校验质量。',
  },
  {
    id: 'agent_deployer',
    title: 'Agent Deployer · 部署上线',
    owner: 'Agent Deployer',
    description: '部署至运行环境，执行验证与灰度策略。',
  },
];

const TAB_DEFINITIONS: TabDefinition[] = [
  { id: 'overview', label: '全景视图' },
  { id: 'requirements_analyzer', label: '需求分析' },
  { id: 'system_architect', label: '架构设计' },
  { id: 'tools_developer', label: '工具配置' },
  { id: 'prompt_engineer', label: '提示词方案' },
  { id: 'agent_code_developer', label: '代码实现' },
  { id: 'agent_deployer', label: '测试部署' },
];

const PREVIEW_DEFINITIONS: PreviewDefinition[] = [
  {
    id: 'blueprint',
    label: '架构蓝图',
    stageId: 'system_architect',
    fallback: [
      '• 主流程 Agent → 工具编排器 → 事件总线',
      '• Memory Service: 短期记忆 + 长期知识库',
      '• Integration: CRM API, 工单系统, Data Lake',
      '• Observability: Token usage, SLA, Alerting Webhook',
    ],
  },
  {
    id: 'prompts',
    label: '系统提示词',
    stageId: 'prompt_engineer',
    fallback: [
      '角色：企业客服质检专家',
      '目标：分析对话并输出改进建议',
      '约束：保持工单编号、遵守敏感词规则',
      '记忆：上一轮处理结论 + 历史高频问题',
    ],
  },
  {
    id: 'tests',
    label: '测试场景',
    stageId: 'agent_developer_manager',
    fallback: [
      '• 场景 01：投诉升级至人工 · 验证 SLA 告警',
      '• 场景 02：知识库缺失时的 fallback 策略',
      '• 场景 03：外部 API 限流的重试与缓冲',
    ],
  },
];

const STATUS_LABEL: Record<StageStatus, string> = {
  completed: '已完成',
  running: '进行中',
  pending: '待开始',
  failed: '构建失败',
};

const STATUS_CLASS: Record<StageStatus, string> = {
  completed: 'Completed',
  running: 'Running',
  pending: 'Pending',
  failed: 'Failed',
};

type FilterKey = 'all' | ProjectSummary['status'];

const PROJECT_STATUS_CLASS: Record<ProjectSummary['status'], string> = {
  building: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  pending: 'Pending',
  paused: 'Pending',
};

const PROJECT_STATUS_LABEL: Record<ProjectSummary['status'], string> = {
  building: '构建中',
  completed: '已完成',
  failed: '失败',
  pending: '等待中',
  paused: '已暂停',
};

const STAGE_ICONS: Record<string, string> = {
  orchestrator: '🧭',
  requirements_analyzer: '📝',
  requirements_analysis: '📝',
  system_architect: '🧠',
  system_architecture: '🧠',
  agent_designer: '🎨',
  agent_design: '🎨',
  prompt_engineer: '💡',
  tools_developer: '🛠️',
  agent_code_developer: '💻',
  agent_developer_manager: '🧩',
  agent_deployer: '🚀',
};

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

function toStringArray(value: unknown): string[] | undefined {
  if (Array.isArray(value)) {
    return value.map((item) => String(item));
  }
  return undefined;
}

function normaliseLines(lines: Array<string | undefined>): string[] {
  return lines.filter((line): line is string => Boolean(line && line.trim()));
}

function buildPreviewLines(stage: BuildDashboardStage | undefined, fallback: string[], requirement?: string) {
  if (!stage) {
    return fallback;
  }

  const metadata = stage.metadata ?? {};
  const lines: string[] = [];

  const description = toStringValue(metadata.description);
  if (description) {
    lines.push(description);
  }

  const docPath = toStringValue(metadata.doc_path);
  if (docPath) {
    lines.push(`方案文档：${docPath}`);
  }

  const artifacts = toStringArray(metadata.artifacts);
  if (artifacts?.length) {
    lines.push(`关联工件：${artifacts.join(', ')}`);
  }

  if (stage.durationSeconds) {
    lines.push(`阶段耗时：${formatDuration(Math.round(stage.durationSeconds))}`);
  }

  if (stage.inputTokens != null || stage.outputTokens != null) {
    const input = stage.inputTokens != null ? stage.inputTokens.toLocaleString() : '—';
    const output = stage.outputTokens != null ? stage.outputTokens.toLocaleString() : '—';
    lines.push(`Token 消耗：输入 ${input} · 输出 ${output}`);
  }

  if (!lines.length && requirement) {
    lines.push(requirement);
  }

  return lines.length ? lines : fallback;
}

export default function BuildModulesPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
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

  const [activeTab, setActiveTab] = useState<string>(TAB_DEFINITIONS[0]?.id ?? 'overview');
  const [activePreview, setActivePreview] = useState<string>(PREVIEW_DEFINITIONS[0]?.id ?? 'blueprint');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');

  const filteredProjects = useMemo(() => {
    if (!projectSummaries) {
      return [];
    }

    const keyword = searchTerm.trim().toLowerCase();

    return projectSummaries.filter((project) => {
      if (activeFilter !== 'all' && project.status !== activeFilter) {
        return false;
      }

      if (!keyword) {
        return true;
      }

      return (
        project.projectName?.toLowerCase().includes(keyword) ||
        project.projectId.toLowerCase().includes(keyword) ||
        project.tags?.some((tag) => tag.toLowerCase().includes(keyword))
      );
    });
  }, [projectSummaries, activeFilter, searchTerm]);

  const onSelectProject = useCallback(
    (id: string) => {
      router.push(`/build/modules?projectId=${encodeURIComponent(id)}`);
    },
    [router],
  );

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { total: filteredProjects.length };
    for (const project of filteredProjects) {
      counts[project.status] = (counts[project.status] ?? 0) + 1;
    }
    return counts;
  }, [filteredProjects]);

  const selectedProject = useMemo(
    () => projectSummaries?.find((project) => project.projectId === projectId),
    [projectSummaries, projectId],
  );

  const projectDisplayName = selectedProject?.projectName ?? dashboard?.projectName ?? projectId;

  useEffect(() => {
    if (!filteredProjects.length) {
      return;
    }
    const exists = filteredProjects.some((project) => project.projectId === projectId);
    if (!exists) {
      onSelectProject(filteredProjects[0].projectId);
    }
  }, [filteredProjects, projectId, onSelectProject]);

  const stages = dashboard?.stages ?? [];
  const stageMap = new Map<string, BuildDashboardStage>();
  stages.forEach((stage) => {
    stageMap.set(stage.name, stage);
  });

  const stageModules: StageModuleView[] = STAGE_DEFINITIONS.map((definition) => {
    const stage = stageMap.get(definition.id);
    const status: StageStatus = stage?.status ?? 'pending';
    const statusLabel = STATUS_LABEL[status] ?? '待开始';
    const statusClass = STATUS_CLASS[status] ?? 'Pending';

    const metrics: string[] = [];
    if (stage?.durationSeconds) {
      metrics.push(`耗时：${formatDuration(Math.round(stage.durationSeconds))}`);
    }
    if (stage?.inputTokens != null || stage?.outputTokens != null) {
      const input = stage?.inputTokens != null ? stage.inputTokens.toLocaleString() : '—';
      const output = stage?.outputTokens != null ? stage.outputTokens.toLocaleString() : '—';
      metrics.push(`Token：${input} ↔ ${output}`);
    }
    if (stage?.toolCalls != null) {
      metrics.push(`工具调用：${stage.toolCalls}`);
    }

    const metadataLines = normaliseLines([
      toStringValue(stage?.metadata?.description),
      toStringValue(stage?.metadata?.doc_path) ? `方案文档：${stage?.metadata?.doc_path}` : undefined,
      Array.isArray(stage?.metadata?.artifacts) && stage?.metadata?.artifacts.length
        ? `工件：${stage?.metadata?.artifacts.length} 个`
        : undefined,
      toStringValue(stage?.metadata?.owner) ? `协作负责人：${stage?.metadata?.owner}` : undefined,
    ]);

    return {
      id: definition.id,
      title: definition.title,
      owner: stage?.metadata?.owner ?? definition.owner,
      description: stage?.metadata?.description ?? definition.description,
      status,
      statusLabel,
      statusClass,
      startedAt: stage?.startedAt,
      completedAt: stage?.completedAt,
      metrics,
      metadataLines,
    };
  });

  const overviewStats = [
    {
      label: '整体进度',
      value: `${Math.round(dashboard?.progressPercentage ?? 0)}%`,
      description: '当前项目整体完成情况',
    },
    {
      label: '阶段完成',
      value: `${dashboard?.completedStages ?? 0}/${dashboard?.totalStages ?? 0}`,
      description: '已完成 / 总阶段数',
    },
    {
      label: '累计耗时',
      value:
        dashboard?.metrics?.totalDurationSeconds != null
          ? formatDuration(Math.round(dashboard.metrics.totalDurationSeconds))
          : '—',
      description: '构建累计用时',
    },
    {
      label: '工具数量',
      value: dashboard?.metrics?.totalTools != null ? `${dashboard.metrics.totalTools}` : '—',
      description: '参与构建的工具总数',
    },
  ];

  const previewSection = PREVIEW_DEFINITIONS.find((section) => section.id === activePreview) ?? PREVIEW_DEFINITIONS[0];
  const previewStage = stageMap.get(previewSection.stageId ?? '');
  const previewLines = buildPreviewLines(previewStage, previewSection.fallback, dashboard?.requirement);

  const resources = dashboard?.resources ?? [];
  const alerts = (dashboard?.alerts ?? [])
    .slice()
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));

  const dashboardStatus = dashboard?.status ?? 'pending';
  const navStageItems = stageModules;
  const projectStatusClass = `statusDot${
    dashboardStatus === 'completed'
      ? 'Completed'
      : dashboardStatus === 'failed'
      ? 'Failed'
      : dashboardStatus === 'pending'
      ? 'Pending'
      : 'Building'
  }`;

  const navResources = resources.slice(0, 3);
  const criticalAlerts = alerts.filter((alert) => alert.level !== 'info').slice(0, 3);
  const workflowNodes = dashboard?.workflowGraphNodes ?? [];
  const workflowEdges = dashboard?.workflowGraphEdges ?? [];

  const activeStageId = activeTab === 'overview' ? undefined : activeTab;
  const stageCards = activeStageId
    ? stageModules.filter((stage) => stage.id === activeStageId)
    : stageModules;

  if (summariesLoading) {
    return <LoadingState message="加载项目列表…" />;
  }

  if (summariesError) {
    return <ErrorState description="无法加载项目列表，请稍后重试。" />;
  }

  if (!projectId) {
    return (
      <div className={styles.appContainer}>
        <div className={styles.emptyStateWrapper}>
          <div className={styles.emptyState}>
            <div className={styles.emptyTitle}>暂未找到构建项目</div>
            <div className={styles.emptyDescription}>
              当前没有可用的构建记录。请先提交新的构建需求或等待现有任务创建完成。
            </div>
            <div className={styles.emptyActions}>
              <Link href="/agents/new" className={styles.emptyActionsPrimary}>
                新建代理构建任务
              </Link>
              <button
                type="button"
                className={styles.emptyActionsSecondary}
                onClick={() => toast('请先创建一个构建会话')}
              >
                了解构建流程
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (dashboardLoading && !dashboard) {
    return <LoadingState message="加载模块数据…" />;
  }

  if (dashboardError || !dashboard) {
    return (
      <div className={styles.appContainer}>
        <div className={styles.emptyStateWrapper}>
          <div className={styles.emptyState}>
            <div className={styles.emptyTitle}>无法加载模块数据</div>
            <div className={styles.emptyDescription}>
              请稍后重试，或检查后端服务状态。确保构建流程已启动并能够查询到阶段信息。
            </div>
            <div className={styles.emptyActions}>
              <button
                type="button"
                className={styles.emptyActionsPrimary}
                onClick={() => refetchDashboard()}
              >
                重试
              </button>
              <Link href="/build" className={styles.emptyActionsSecondary}>
                返回构建进度
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.appContainer}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>Nexus-AI</div>
        </div>
        <div className={styles.sidebarProject}>
          <div className={styles.sidebarProjectName}>{projectDisplayName}</div>
          <div className={styles.sidebarProjectMeta}>
            <span className={`${styles.statusDot} ${styles[projectStatusClass] ?? ''}`} />
            {dashboardStatus === 'completed'
              ? '已完成'
              : dashboardStatus === 'failed'
              ? '执行失败'
              : dashboardStatus === 'pending'
              ? '待启动'
              : '构建中'}
          </div>
          <div className={styles.sidebarProjectMeta}>最近更新：{formatDateTime(dashboard.updatedAt)}</div>
        </div>

        <div className={styles.navModules}>
          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>构建阶段</div>
            {navStageItems.map((stage) => {
              const isActive = activeStageId ? stage.id === activeStageId : stage.status === 'running';
              return (
                <button
                  key={stage.id}
                  type="button"
                  className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                  onClick={() => setActiveTab(stage.id)}
                >
                  <span className={styles.navIcon}>⚙️</span>
                  <span className={styles.navText}>{stage.title}</span>
                  <span className={styles.navBadge}>{stage.statusLabel}</span>
                </button>
              );
            })}
          </div>

          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>依赖资源</div>
            {navResources.length ? (
              navResources.map((resource) => (
                <div key={resource.id} className={styles.navItem} style={{ cursor: 'default' }}>
                  <span className={styles.navIcon}>📎</span>
                  <span className={styles.navText}>{resource.label}</span>
                  {resource.status ? <span className={styles.navBadge}>{resource.status}</span> : null}
                </div>
              ))
            ) : (
              <div className={styles.navItem} style={{ cursor: 'default', opacity: 0.6 }}>
                <span className={styles.navText}>暂无依赖记录</span>
              </div>
            )}
          </div>

          <div className={styles.navSection}>
            <div className={styles.navSectionTitle}>风险提醒</div>
            {criticalAlerts.length ? (
              criticalAlerts.map((alert) => (
                <div key={alert.id} className={styles.navItem} style={{ cursor: 'default' }}>
                  <span className={styles.navIcon}>⚠️</span>
                  <span className={styles.navText}>{alert.message}</span>
                </div>
              ))
            ) : (
              <div className={styles.navItem} style={{ cursor: 'default', opacity: 0.6 }}>
                <span className={styles.navText}>暂无风险提醒</span>
              </div>
            )}
          </div>
        </div>

        <div className={styles.sidebarFooter}>
          <button
            type="button"
            className={styles.sidebarButtonPrimary}
            onClick={() => toast.success('已创建新的构建会话')}
          >
            新建构建会话
          </button>
          <Link href="/build" className={styles.sidebarButtonSecondary}>
            查看构建进度
          </Link>
        </div>
      </aside>

      <div className={styles.mainContent}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <Link href="/" className={styles.headerLink}>
              控制台
            </Link>
            <span className={styles.headerSeparator}>/</span>
            <Link href="/build" className={styles.headerLink}>
              构建进度
            </Link>
            <span className={styles.headerSeparator}>/</span>
            <span>模块总览</span>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={styles.headerButton}
              onClick={() => refetchDashboard()}
            >
              手动刷新
            </button>
          </div>
        </header>

        <div className={styles.contentArea}>
          <section className={styles.moduleHeader}>
            <div className={styles.headerTop}>
              <div className={styles.headerInfo}>
                <div className={styles.headerTitle}>⚙️ 构建模块总览</div>
                <div className={styles.headerSubtitle}>实时掌握协作阶段、关键指标与交付物进展。</div>
                <div className={styles.headerMetaGrid}>
                  <div className={styles.headerMetaItem}>
                    <span className={styles.headerMetaLabel}>构建编号</span>
                    <span className={styles.headerMetaValue}>{projectId}</span>
                  </div>
                  <div className={styles.headerMetaItem}>
                    <span className={styles.headerMetaLabel}>构建状态</span>
                    <span className={styles.headerMetaValue}>{PROJECT_STATUS_LABEL[dashboardStatus]}</span>
                  </div>
                  <div className={styles.headerMetaItem}>
                    <span className={styles.headerMetaLabel}>最近更新</span>
                    <span className={styles.headerMetaValue}>{formatDateTime(dashboard?.updatedAt)}</span>
                  </div>
                </div>
              </div>
              <div className={styles.promoActions}>
                <button
                  type="button"
                  className={styles.primaryAction}
                  onClick={() => toast.success('已安排阶段评审')}
                >
                  安排阶段评审
                </button>
                <Link href="/build" className={styles.secondaryAction}>
                  返回构建进度
                </Link>
              </div>
            </div>

            <div className={styles.metricRow}>
              {overviewStats.map((stat) => (
                <div key={stat.label} className={styles.metricCard}>
                  <div className={styles.metricLabel}>{stat.label}</div>
                  <div className={styles.metricValue}>{stat.value}</div>
                  {stat.description ? <div className={styles.metricDescription}>{stat.description}</div> : null}
                </div>
              ))}
            </div>
          </section>

          <section className={styles.workflowCard}>
          <div className={styles.workflowHeader}>
            <div className={styles.workflowTitle}>🚀 Agent Build Workflow</div>
            <div className={styles.workflowVersion}>
              最近更新：{dashboard.updatedAt ? formatDateTime(dashboard.updatedAt) : '未知'}
            </div>
          </div>
            <div className={styles.workflowInfo}>
              <div className={styles.infoItem}>
                <div className={styles.infoLabel}>当前项目</div>
                <div className={styles.infoValue}>{projectDisplayName}</div>
              </div>
              <div className={styles.infoItem}>
                <div className={styles.infoLabel}>构建状态</div>
                <div className={styles.infoValue}>{PROJECT_STATUS_LABEL[dashboardStatus]}</div>
              </div>
              <div className={styles.infoItem}>
                <div className={styles.infoLabel}>总体进度</div>
                <div className={styles.infoValue}>{`${Math.round(dashboard?.progressPercentage ?? 0)}%`}</div>
              </div>
              <div className={styles.infoItem}>
                <div className={styles.infoLabel}>累积耗时</div>
                <div className={styles.infoValue}>
                  {dashboard.metrics?.totalDurationSeconds
                    ? formatDuration(Math.round(dashboard.metrics.totalDurationSeconds))
                    : '—'}
                </div>
              </div>
            </div>
          </section>

          <div className={styles.searchFilterSection}>
            <input
              type="search"
              className={styles.searchBar}
              placeholder="🔍 搜索构建任务名称 / 项目 ID"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <div className={styles.filterTabs}>
              {([
                { id: 'all', label: `全部任务 (${statusCounts.total ?? 0})` },
                { id: 'building', label: `构建中 (${statusCounts.building ?? 0})` },
                { id: 'completed', label: `已完成 (${statusCounts.completed ?? 0})` },
                { id: 'failed', label: `失败 (${statusCounts.failed ?? 0})` },
              ] as Array<{ id: FilterKey; label: string }>).map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  className={
                    activeFilter === filter.id ? `${styles.filterTab} ${styles.filterTabActive}` : styles.filterTab
                  }
                  onClick={() => setActiveFilter(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          <section className={styles.buildProgressCard}>
            <div className={styles.progressHeader}>
              <div className={styles.progressTitle}>📊 构建进度监控</div>
              <div className={styles.progressActions}>
                <button
                  type="button"
                  className={styles.progressButton}
                  onClick={() => refetchDashboard()}
                >
                  刷新状态
                </button>
                <Link href="/build" className={styles.progressButton}>
                  打开构建进度页
                </Link>
              </div>
            </div>

            <div className={styles.buildList}>
              {filteredProjects.length ? (
                filteredProjects.map((project) => {
                  const statusClass = PROJECT_STATUS_CLASS[project.status] ?? 'Pending';
                  const progressValue = Math.max(0, Math.min(100, Math.round(project.progressPercentage)));
                  const isActive = project.projectId === projectId;

                  return (
                    <div
                      key={project.projectId}
                      className={`${styles.buildItem} ${styles[`buildItem${statusClass}`] ?? ''} ${
                        isActive ? styles.buildItemActive : ''
                      }`}
                      onClick={() => onSelectProject(project.projectId)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className={styles.buildItemHeaderRow}>
                        <div>
                          <div className={styles.buildItemTitle}>{project.projectName ?? project.projectId}</div>
                          <div className={styles.buildItemMeta}>
                            <span>任务 ID：{project.projectId}</span>
                            <span>进度：{progressValue}%</span>
                            {project.updatedAt ? <span>最近更新：{formatDateTime(project.updatedAt)}</span> : null}
                          </div>
                        </div>
                        <div className={styles.buildItemStatus}>
                          <span
                            className={`${styles.statusDot} ${styles[`statusDot${statusClass}`] ?? ''}`}
                            aria-hidden="true"
                          />
                          {PROJECT_STATUS_LABEL[project.status]}
                        </div>
                      </div>

                      <div>
                        <div className={styles.buildProgressBar}>
                          <div className={styles.buildProgressFill} style={{ width: `${progressValue}%` }} />
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>完成度 {progressValue}%</div>
                      </div>

                      <div className={styles.buildDetailGrid}>
                        <div>
                          <span className={styles.buildDetailLabel}>当前阶段：</span>
                          <span>{project.currentStage ?? '未知'}</span>
                        </div>
                        <div>
                          <span className={styles.buildDetailLabel}>Agent 数量：</span>
                          <span>{project.agentCount ?? 0}</span>
                        </div>
                        {project.tags?.length ? (
                          <div>
                            <span className={styles.buildDetailLabel}>标签：</span>
                            <span>{project.tags.join(', ')}</span>
                          </div>
                        ) : null}
                      </div>

                      <div className={styles.buildCardFooter}>
                        <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                          最近更新：{project.updatedAt ? formatDateTime(project.updatedAt) : '未知'}
                        </div>
                        <div className={styles.buildCardActions}>
                          <button
                            type="button"
                            className={styles.buildCardButton}
                            onClick={(event) => {
                              event.stopPropagation();
                              onSelectProject(project.projectId);
                            }}
                          >
                            查看概览
                          </button>
                          <Link
                            href={`/build?projectId=${project.projectId}`}
                            className={`${styles.buildCardButton} ${styles.buildCardButtonPrimary}`}
                            onClick={(event) => event.stopPropagation()}
                          >
                            查看详情
                          </Link>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>暂无符合条件的构建任务。</div>
              )}
            </div>
          </section>

          <div className={styles.moduleGrid}>
            <section className={styles.sectionCard}>
              <div className={styles.sectionHeader}>
                <h3 className={styles.sectionTitle}>阶段与角色协作</h3>
                <Link href="/build/graph" className={styles.headerLink} style={{ fontWeight: 600 }}>
                  查看工作流拓扑 →
                </Link>
              </div>
              <div className={styles.stageList}>
                {stageCards.length ? (
                  stageCards.map((stage) => {
                    const icon = STAGE_ICONS[stage.id] ?? '⚙️';
                    const actionLabel =
                      stage.status === 'running'
                        ? '查看日志'
                        : stage.status === 'completed'
                        ? '查看交付物'
                        : stage.status === 'failed'
                        ? '查看错误'
                        : '待启动';

                    return (
                      <div
                        key={stage.id}
                        className={`${styles.stageCard} ${styles[`stageCard${stage.statusClass}`] ?? ''}`}
                      >
                        <div className={styles.stageCardHeader}>
                          <div className={styles.stageCardInfo}>
                            <span className={styles.stageIconCircle} aria-hidden="true">
                              {icon}
                            </span>
                            <div>
                              <div className={styles.stageCardTitle}>{stage.title}</div>
                              {stage.owner ? (
                                <div className={styles.stageMetaSecondary}>负责人：{stage.owner}</div>
                              ) : null}
                            </div>
                          </div>
                          <div className={styles.stageCardStatus}>
                            <span
                              className={`${styles.stageStatusBadge} ${
                                styles[`stageStatus${stage.statusClass}`] ?? ''
                              }`}
                            >
                              {stage.statusLabel}
                            </span>
                            <button type="button" className={styles.stageAction}>
                              {actionLabel}
                            </button>
                          </div>
                        </div>

                        {stage.description ? <div className={styles.stageMeta}>{stage.description}</div> : null}

                        {(stage.startedAt || stage.completedAt) && (
                          <div className={styles.stageMeta}>
                            {stage.startedAt ? `开始：${formatDateTime(stage.startedAt)}` : ''}
                            {stage.completedAt ? ` · 完成：${formatDateTime(stage.completedAt)}` : ''}
                          </div>
                        )}

                        {stage.metrics.map((metric) => (
                          <div key={`${stage.id}-metric-${metric}`} className={styles.stageMeta}>
                            {metric}
                          </div>
                        ))}
                        {stage.metadataLines.map((line, index) => (
                          <div key={`${stage.id}-meta-${index}`} className={styles.stageMeta}>
                            {line}
                          </div>
                        ))}
                      </div>
                    );
                  })
                ) : (
                  <div className={styles.stageMeta}>暂无阶段数据。</div>
                )}
              </div>
            </section>

            <aside className={`${styles.sectionCard} ${styles.previewPanel}`}>
              <div className={styles.sectionHeader}>
                <h3 className={styles.sectionTitle}>交付物预览</h3>
              <div className={styles.previewTabs}>
                {PREVIEW_DEFINITIONS.map((panel) => (
                  <button
                    key={panel.id}
                    type="button"
                    className={
                      panel.id === activePreview
                        ? `${styles.previewTab} ${styles.previewTabActive}`
                        : styles.previewTab
                    }
                    onClick={() => setActivePreview(panel.id)}
                  >
                    {panel.label}
                  </button>
                ))}
                </div>
              </div>

              <div className={styles.previewBody}>
                {previewLines.length ? (
                  previewLines.map((line, index) => (
                    <div key={`${previewSection.id}-line-${index}`} style={{ marginBottom: 8 }}>
                      {line}
                    </div>
                  ))
                ) : (
                  <div className={styles.previewEmpty}>暂无该阶段的交付物说明。</div>
                )}
              </div>

              <div className={styles.workflowCanvas}>
                <div style={{ fontWeight: 600 }}>工作流拓扑概览</div>
                <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
                  当前图节点 {workflowNodes.length} 个 · 连接 {workflowEdges.length} 条。
                  访问拓扑图可查看节点详情与关键路径分析。
                </div>
              </div>
            </aside>
          </div>

          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>上/下游依赖检查</h3>
              <button
                type="button"
                className={styles.secondaryAction}
                onClick={() => toast('已生成依赖健康检查报告')}
              >
                生成健康检查报告
              </button>
            </div>
            <div className={styles.checklist}>
              {resources.length ? (
                resources.map((resource) => (
                  <div key={resource.id} className={styles.checkItem}>
                    <span>✅</span>
                    <span>
                      {resource.label}
                      {resource.status ? ` · ${resource.status}` : ''}
                    </span>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>暂无依赖检查记录。</div>
              )}
            </div>
          </section>

          <section className={styles.sectionCard}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.sectionTitle}>实时提醒</h3>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                当前共有 {alerts.length} 条提醒（含 {criticalAlerts.length} 条风险项）
              </span>
            </div>
            <div className={styles.notificationList}>
              {alerts.length ? (
                alerts.map((alert) => (
                  <div key={alert.id} className={styles.notificationItem}>
                    <div className={styles.notificationTitle}>{alert.message}</div>
                    <div className={styles.notificationMeta}>
                      时间：{formatDateTime(alert.createdAt)} · 类型：{alert.level.toUpperCase()}
                    </div>
                    {alert.metadata?.details ? <div>{String(alert.metadata.details)}</div> : null}
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>暂无提醒，构建流程运行正常。</div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
