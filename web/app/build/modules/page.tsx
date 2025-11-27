'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import styles from './modules.module.css';
import { toast } from 'sonner';
import { useBuildDashboard, useProjectSummaries } from '@/hooks/use-projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';
import { formatDateTime, formatDuration } from '@/lib/formatters';
import type { BuildDashboard, BuildDashboardStage, ProjectSummary } from '@/types/projects';

type StageStatus = BuildDashboardStage['status'];
type FilterKey = 'all' | ProjectSummary['status'];

interface StageDefinition {
  readonly id: string;
  readonly title: string;
  readonly description?: string;
  readonly owner?: string;
  readonly icon: string;
}

interface StageCardView {
  readonly id: string;
  readonly title: string;
  readonly description?: string;
  readonly owner?: string;
  readonly icon: string;
  readonly status: StageStatus;
  readonly statusLabel: string;
  readonly statusClass: string;
  readonly metrics: string[];
  readonly metadata: string[];
}

const STAGE_DEFINITIONS: StageDefinition[] = [
  {
    id: 'orchestrator',
    title: 'Orchestrator · 需求理解',
    description: '解析业务场景并拆解交付目标，生成初始构建蓝图。',
    owner: 'Orchestrator Agent',
    icon: '🧭',
  },
  {
    id: 'requirements_analyzer',
    title: 'Requirements Analyzer · 需求分析',
    description: '补全缺失上下文，梳理验收标准与关键指标。',
    owner: 'Requirements Analyzer',
    icon: '📝',
  },
  {
    id: 'system_architect',
    title: 'Architect · 系统设计',
    description: '定义 Agent 组件、记忆策略与系统集成方案。',
    owner: 'System Architect',
    icon: '🧠',
  },
  {
    id: 'agent_designer',
    title: 'Agent Designer · 交互方案',
    description: '生成 Agent 角色设定、会话策略与响应格式。',
    owner: 'Agent Designer',
    icon: '🎨',
  },
  {
    id: 'prompt_engineer',
    title: 'Prompt Engineer · 提示词方案',
    description: '构建系统提示词、样例对话与记忆胶囊。',
    owner: 'Prompt Engineer',
    icon: '💡',
  },
  {
    id: 'tools_developer',
    title: 'Tools Engineer · 工具集成',
    description: '实现外部 API 封装、鉴权策略与监控指标。',
    owner: 'Tools Engineer',
    icon: '🛠️',
  },
  {
    id: 'agent_code_developer',
    title: 'Agent Developer · 代码实现',
    description: '生成业务逻辑、单元测试与部署脚本。',
    owner: 'Agent Developer',
    icon: '💻',
  },
  {
    id: 'agent_developer_manager',
    title: 'Developer Manager · 开发管理',
    description: '协调多角色交付，整合工件并校验质量。',
    owner: 'Developer Manager',
    icon: '🧩',
  },
  {
    id: 'agent_deployer',
    title: 'Agent Deployer · 部署上线',
    description: '部署至运行环境，执行验证与灰度策略。',
    owner: 'Agent Deployer',
    icon: '🚀',
  },
];

const STATUS_LABEL: Record<StageStatus, string> = {
  completed: '已完成',
  running: '进行中',
  pending: '待开始',
  failed: '失败',
};

const STATUS_CLASS: Record<StageStatus, string> = {
  completed: 'Completed',
  running: 'Running',
  pending: 'Pending',
  failed: 'Failed',
};

const PROJECT_STATUS_LABEL: Record<ProjectSummary['status'], string> = {
  building: '构建中',
  completed: '已完成',
  failed: '失败',
  pending: '等待中',
  paused: '已暂停',
};

const PROJECT_STATUS_CLASS: Record<ProjectSummary['status'], string> = {
  building: 'Building',
  completed: 'Completed',
  failed: 'Failed',
  pending: 'Pending',
  paused: 'Pending',
};

const JOB_ID_PATTERN = /^job_[0-9a-f]{8,}$/i;

function toStringValue(value: unknown): string | undefined {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed.length) {
      return trimmed;
    }
  }
  return undefined;
}

function normaliseLines(lines: Array<string | undefined>): string[] {
  return lines.filter((line): line is string => Boolean(line && line.trim()));
}

function buildStageCards(stages: BuildDashboardStage[] | undefined): StageCardView[] {
  const stageMap = new Map<string, BuildDashboardStage>();
  stages?.forEach((stage) => {
    stageMap.set(stage.name, stage);
  });

  return STAGE_DEFINITIONS.map((definition) => {
    const stage = stageMap.get(definition.id);
    const status: StageStatus = stage?.status ?? 'pending';
    const statusLabel = STATUS_LABEL[status] ?? STATUS_LABEL.pending;
    const statusClass = STATUS_CLASS[status] ?? STATUS_CLASS.pending;

    const metrics: string[] = [];
    if (stage?.durationSeconds) {
      metrics.push(`耗时 ${formatDuration(Math.round(stage.durationSeconds))}`);
    }
    if (stage?.inputTokens != null || stage?.outputTokens != null) {
      const input = stage?.inputTokens != null ? stage.inputTokens.toLocaleString() : '—';
      const output = stage?.outputTokens != null ? stage.outputTokens.toLocaleString() : '—';
      metrics.push(`Token ${input} ↔ ${output}`);
    }
    if (stage?.toolCalls != null) {
      metrics.push(`工具调用 ${stage.toolCalls}`);
    }

    const owner = toStringValue(stage?.metadata?.owner) ?? definition.owner;
    const description = toStringValue(stage?.metadata?.description) ?? definition.description;

    const metadata = normaliseLines([
      owner ? `协作负责人：${owner}` : undefined,
      toStringValue(stage?.metadata?.doc_path) ? `方案文档：${stage?.metadata?.doc_path}` : undefined,
      Array.isArray(stage?.metadata?.artifacts) && stage?.metadata?.artifacts.length
        ? `工件：${stage.metadata.artifacts.length} 个`
        : undefined,
      stage?.startedAt ? `开始：${formatDateTime(stage.startedAt)}` : undefined,
      stage?.completedAt ? `完成：${formatDateTime(stage.completedAt)}` : undefined,
    ]);

    return {
      id: definition.id,
      title: definition.title,
      description,
      owner,
      icon: definition.icon,
      status,
      statusLabel,
      statusClass,
      metrics,
      metadata,
    };
  });
}

function deriveNameFromTags(tags?: string[] | undefined | null): string | undefined {
  if (!tags || !tags.length) {
    return undefined;
  }

  for (const raw of tags) {
    const tag = raw?.trim();
    if (!tag) {
      continue;
    }
    if (JOB_ID_PATTERN.test(tag)) {
      continue;
    }
    const cleaned = tag.replace(/^name[:：]/i, '').trim();
    if (cleaned.length) {
      return cleaned;
    }
    if (tag.length) {
      return tag;
    }
  }
  return undefined;
}

function extractProjectName(
  summary: ProjectSummary | undefined,
  dashboard: BuildDashboard | undefined,
): string | undefined {
  const metadata = (dashboard?.latestTask?.metadata ?? undefined) as Record<string, unknown> | undefined;

  const metadataValue = (key: string) => {
    const raw = metadata ? metadata[key] : undefined;
    if (typeof raw === 'string') {
      const trimmed = raw.trim();
      return trimmed.length ? trimmed : undefined;
    }
    return undefined;
  };

  const candidates: Array<string | undefined> = [
    summary?.projectName,
    dashboard?.projectName,
    metadataValue('project_name'),
    metadataValue('projectName'),
    metadataValue('name'),
    metadataValue('title'),
    deriveNameFromTags(summary?.tags),
  ];

  for (const candidate of candidates) {
    if (candidate && !JOB_ID_PATTERN.test(candidate)) {
      return candidate;
    }
  }

  const requirementLead = dashboard?.requirement?.split(/\r?\n|。/)[0]?.trim();
  if (requirementLead && requirementLead.length <= 40) {
    return requirementLead;
  }

  if (summary?.projectId) {
    return `构建任务 ${summary.projectId.slice(-6)}`;
  }

  if (dashboard?.projectId) {
    return `构建任务 ${dashboard.projectId.slice(-6)}`;
  }

  return undefined;
}

function getProjectListName(project: ProjectSummary): string {
  const candidate = extractProjectName(project, undefined);
  if (candidate) {
    return candidate;
  }
  return project.projectName && !JOB_ID_PATTERN.test(project.projectName)
    ? project.projectName
    : `构建任务 ${project.projectId.slice(-6)}`;
}

function formatStatValue(value: number | undefined, options?: { readonly suffix?: string; readonly digits?: number }) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  const digits = options?.digits ?? 0;
  const formatted = digits > 0 ? value.toFixed(digits) : Math.round(value).toLocaleString();
  return options?.suffix ? `${formatted}${options.suffix}` : formatted;
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

  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const allTasksRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!projectSummaries?.length || !projectId) {
      return;
    }
    const exists = projectSummaries.some((project) => project.projectId === projectId);
    if (!exists) {
      router.push(`/build/modules?projectId=${encodeURIComponent(projectSummaries[0].projectId)}`);
    }
  }, [projectSummaries, projectId, router]);

  const onSelectProject = useCallback(
    (id: string) => {
      router.push(`/build/modules?projectId=${encodeURIComponent(id)}`);
    },
    [router],
  );

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refetchDashboard();
      toast.success('刷新成功');
    } catch (error) {
      toast.error('刷新失败，请重试');
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  }, [refetchDashboard]);

  const scrollToAllTasks = useCallback(() => {
    allTasksRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const filteredProjects = useMemo(() => {
    if (!projectSummaries) {
      return [];
    }
    const keyword = searchTerm.trim().toLowerCase();
    return projectSummaries.filter((project) => {
      const matchesFilter = activeFilter === 'all' || project.status === activeFilter;
      if (!matchesFilter) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      const name = project.projectName?.toLowerCase() ?? '';
      const tags = project.tags ?? [];
      return (
        name.includes(keyword) ||
        project.projectId.toLowerCase().includes(keyword) ||
        tags.some((tag) => tag.toLowerCase().includes(keyword))
      );
    });
  }, [projectSummaries, activeFilter, searchTerm]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { total: projectSummaries?.length ?? 0 };
    if (!projectSummaries) {
      return counts;
    }
    for (const project of projectSummaries) {
      counts[project.status] = (counts[project.status] ?? 0) + 1;
    }
    return counts;
  }, [projectSummaries]);

  const selectedProject = useMemo(
    () => projectSummaries?.find((project) => project.projectId === projectId),
    [projectSummaries, projectId],
  );

  const projectDisplayName =
    extractProjectName(selectedProject, dashboard) ?? projectId ?? '未命名构建任务';

  const stageCards = useMemo(
    () => buildStageCards(dashboard?.stages),
    [dashboard?.stages],
  );

  const totalProjects = projectSummaries?.length ?? 0;
  const buildingCount = statusCounts.building ?? 0;
  const completedCount = statusCounts.completed ?? 0;
  const failedCount = statusCounts.failed ?? 0;

  const totalProgress = projectSummaries?.reduce((sum, project) => sum + (project.progressPercentage ?? 0), 0) ?? 0;
  const averageProgress = totalProjects ? totalProgress / totalProjects : 0;
  const successRate = totalProjects ? (completedCount / totalProjects) * 100 : 0;

  const moduleStats = [
    { label: '总构建任务', value: formatStatValue(totalProjects) },
    { label: '进行中', value: formatStatValue(buildingCount) },
    { label: '已完成', value: formatStatValue(completedCount) },
    { label: '失败', value: formatStatValue(failedCount) },
    { label: '平均进度', value: totalProjects ? `${averageProgress.toFixed(1)}%` : '—' },
    { label: '成功率', value: totalProjects ? `${successRate.toFixed(1)}%` : '—' },
  ];

  const workflowFeatures = useMemo(
    () =>
      STAGE_DEFINITIONS.map((stage) => {
        const [, right] = stage.title.split('·');
        return right ? right.trim() : stage.title;
      }),
    [],
  );

  const workflowInfo = [
    {
      label: '当前项目',
      value: projectDisplayName,
    },
    {
      label: '构建状态',
      value: dashboard ? PROJECT_STATUS_LABEL[dashboard.status] : '—',
    },
    {
      label: '总体进度',
      value: dashboard ? `${Math.round(dashboard.progressPercentage ?? 0)}%` : '—',
    },
    {
      label: '累计耗时',
      value:
        dashboard?.metrics?.totalDurationSeconds != null
          ? formatDuration(Math.round(dashboard.metrics.totalDurationSeconds))
          : '—',
    },
  ];

  const activeStage =
    dashboard?.stages.find((stage) => stage.status === 'running') ??
    dashboard?.stages.find((stage) => stage.status === 'pending');

  const getCurrentStageName = () => {
    if (!dashboard?.stages?.length) return '等待启动';

    const runningStage = dashboard.stages.find((stage) => stage.status === 'running');
    if (runningStage) {
      const definition = STAGE_DEFINITIONS.find((def) => def.id === runningStage.name);
      return definition ? definition.title.split('·')[1]?.trim() || definition.title : runningStage.name;
    }

    const completedCount = dashboard.stages.filter((stage) => stage.status === 'completed').length;
    const totalCount = dashboard.stages.length;

    if (completedCount === totalCount) {
      return '全部完成';
    } else if (completedCount > 0) {
      const nextStage = dashboard.stages.find((stage) => stage.status === 'pending');
      if (nextStage) {
        const definition = STAGE_DEFINITIONS.find((def) => def.id === nextStage.name);
        return `准备中: ${definition ? definition.title.split('·')[1]?.trim() || definition.title : nextStage.name}`;
      }
    }

    return '等待启动';
  };

  const moduleMeta = [
    { label: '构建编号', value: dashboard?.projectId ?? selectedProject?.projectId ?? '—' },
    { label: '当前阶段', value: getCurrentStageName() },
    { label: '最近更新', value: dashboard?.updatedAt ? formatDateTime(dashboard.updatedAt) : '—' },
  ];

  const filterOptions = useMemo(() => {
    const base: Array<{ id: FilterKey; label: string; count: number }> = [
      { id: 'all', label: '全部任务', count: statusCounts.total ?? 0 },
      { id: 'building', label: '构建中', count: statusCounts.building ?? 0 },
      { id: 'completed', label: '已完成', count: statusCounts.completed ?? 0 },
      { id: 'failed', label: '失败', count: statusCounts.failed ?? 0 },
    ];
    if ((statusCounts.pending ?? 0) > 0) {
      base.push({ id: 'pending', label: '等待中', count: statusCounts.pending });
    }
    if ((statusCounts.paused ?? 0) > 0) {
      base.push({ id: 'paused', label: '已暂停', count: statusCounts.paused });
    }
    return base;
  }, [statusCounts]);

  if (summariesLoading) {
    return <LoadingState message="加载构建项目…" />;
  }

  if (summariesError) {
    return <ErrorState description="无法加载项目列表，请稍后重试。" />;
  }

  if (!projectId) {
    return (
      <div className={styles.emptyLayout}>
        <div className={styles.emptyCard}>
          <div className={styles.emptyTitle}>暂未找到构建项目</div>
          <div className={styles.emptyDescription}>
            当前没有可用的构建记录。请先提交新的构建需求或等待现有任务创建完成。
          </div>
          <div className={styles.emptyActions}>
            <Link href="/agents/new" className={`${styles.button} ${styles.buttonPrimary}`}>
              新建代理构建任务
            </Link>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={() => toast('请先创建一个构建会话')}
            >
              了解构建流程
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (dashboardLoading && !dashboard) {
    return <LoadingState message="加载模块视图…" />;
  }

  if (dashboardError || !dashboard) {
    return (
      <ErrorState
        title="无法加载构建模块"
        description="请稍后重试，或检查后端服务状态。"
        onRetry={() => refetchDashboard()}
      />
    );
  }

  return (
    <div className={styles.contentArea}>
      <section className={styles.moduleHeader}>
        <div className={styles.headerContent}>
          <div>
            <div className={styles.headerTitle}>🔨 Agent构建模块</div>
            <div className={styles.headerMeta}>
              {moduleMeta.map((meta) => (
                <div key={meta.label} className={styles.headerMetaItem}>
                  <span className={styles.metaLabel}>{meta.label}</span>
                  <span className={styles.metaValue}>{meta.value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className={styles.headerActions}>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={scrollToAllTasks}
            >
              📋 构建历史
            </button>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={() => toast('工作流配置即将推出')}
            >
              ⚙️ 工作流配置
            </button>
            <Link href="/agents/new" className={`${styles.button} ${styles.buttonPrimary}`}>
              ➕ 新建构建
            </Link>
          </div>
        </div>
        <div className={styles.statsGrid}>
          {moduleStats.map((stat) => (
            <div key={stat.label} className={styles.statCard}>
              <div className={styles.statNumber}>{stat.value}</div>
              <div className={styles.statLabel}>{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.workflowCard}>
        <div className={styles.workflowHeader}>
          <div className={styles.workflowTitle}>🚀 当前构建概览</div>
          <div className={styles.workflowVersion}>
            最近更新：{dashboard.updatedAt ? formatDateTime(dashboard.updatedAt) : '—'}
          </div>
        </div>
        <div className={styles.workflowInfo}>
          {workflowInfo.map((item) => (
            <div key={item.label} className={styles.infoItem}>
              <div className={styles.infoLabel}>{item.label}</div>
              <div className={styles.infoValue}>{item.value}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.stageSection}>
        <div className={styles.sectionHeader}>
          <div>
            <div className={styles.sectionTitle}>🎯 构建阶段详情</div>
            <div className={styles.sectionSubtitle}>
              当前项目：{projectDisplayName} · 共 {stageCards.length} 个阶段
            </div>
          </div>
          <div className={styles.sectionActions}>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={handleRefresh}
              disabled={isRefreshing}
              style={{ opacity: isRefreshing ? 0.6 : 1 }}
            >
              {isRefreshing ? '⏳ 刷新中...' : '🔄 刷新'}
            </button>
          </div>
        </div>
        <div className={styles.stageList}>
          {stageCards.length > 0 ? (
            stageCards.map((card) => (
              <div key={card.id} className={styles.stageCard}>
                <div className={styles.stageIcon}>{card.icon}</div>
                <div className={styles.stageBody}>
                  <div className={styles.stageHeaderRow}>
                    <div>
                      <div className={styles.stageTitle}>{card.title}</div>
                      {card.description && <div className={styles.stageDescription}>{card.description}</div>}
                    </div>
                    <div
                      className={`${styles.stageStatus} ${
                        styles[`stageStatus${card.statusClass}` as const] ?? ''
                      }`}
                    >
                      {card.statusLabel}
                    </div>
                  </div>
                  {card.metrics.length > 0 && (
                    <div className={styles.stageMetaRow}>
                      {card.metrics.map((metric, index) => (
                        <div key={index} className={styles.stageMetric}>
                          {metric}
                        </div>
                      ))}
                    </div>
                  )}
                  {card.metadata.length > 0 && (
                    <div className={styles.stageMetaList}>
                      {card.metadata.map((meta, index) => (
                        <div key={index} className={styles.stageMeta}>
                          {meta}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className={styles.emptyList}>暂无构建阶段数据，请等待构建启动。</div>
          )}
        </div>
      </section>

      <section className={styles.searchFilterSection}>
        <input
          type="search"
          className={styles.searchBar}
          placeholder="🔍 搜索构建任务名称 / 项目 ID / 标签…"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
        />
        <div className={styles.filterTabs}>
          {filterOptions.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={
                activeFilter === filter.id ? `${styles.filterTab} ${styles.filterTabActive}` : styles.filterTab
              }
              onClick={() => setActiveFilter(filter.id)}
            >
              {filter.label} ({filter.count})
            </button>
          ))}
        </div>
      </section>

      <section ref={allTasksRef} className={styles.buildProgressCard}>
        <div className={styles.progressHeader}>
          <div>
            <div className={styles.progressTitle}>📋 所有构建任务</div>
            <div className={styles.progressSubtitle}>当前共 {filteredProjects.length} 个任务符合筛选条件</div>
          </div>
          <div className={styles.progressActions}>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={handleRefresh}
              disabled={isRefreshing}
              style={{ opacity: isRefreshing ? 0.6 : 1 }}
            >
              {isRefreshing ? '⏳ 刷新中...' : '🔄 刷新'}
            </button>
            <button
              type="button"
              className={`${styles.button} ${styles.buttonSecondary}`}
              onClick={() => toast('将导出构建任务概览')}
            >
              📤 导出
            </button>
          </div>
        </div>
        <div className={styles.buildList}>
          {filteredProjects.length ? (
            filteredProjects.map((project) => {
              const statusClass = PROJECT_STATUS_CLASS[project.status] ?? 'Pending';
              const statusLabel = PROJECT_STATUS_LABEL[project.status] ?? project.status;
              const progressValue = Math.max(0, Math.min(100, Math.round(project.progressPercentage ?? 0)));
              const isActive = project.projectId === projectId;
              const displayName = getProjectListName(project);
              return (
                <div
                  key={project.projectId}
                  className={`${styles.buildItem} ${styles[`buildItem${statusClass}` as const] ?? ''} ${
                    isActive ? styles.buildItemActive : ''
                  }`}
                  onClick={() => onSelectProject(project.projectId)}
                >
                  <div className={styles.buildHeaderRow}>
                    <div>
                      <div className={styles.buildName}>{displayName}</div>
                      <div className={styles.buildMeta}>
                        <span>项目 ID：{project.projectId}</span>
                        <span>更新：{project.updatedAt ? formatDateTime(project.updatedAt) : '—'}</span>
                        <span>当前阶段：{project.currentStage ?? '未开始'}</span>
                      </div>
                    </div>
                    <div className={styles.buildStatus}>
                      <span className={`${styles.statusDot} ${styles[`statusDot${statusClass}` as const] ?? ''}`} />
                      {statusLabel}
                    </div>
                  </div>
                  <div className={styles.buildProgress}>
                    <div className={styles.progressBar}>
                      <div className={styles.progressFill} style={{ width: `${progressValue}%` }} />
                    </div>
                    <div className={styles.progressText}>进度：{progressValue}%</div>
                  </div>
                  <div className={styles.buildDetails}>
                    <div className={styles.detailItem}>
                      <span className={styles.detailLabel}>负责人</span>
                      <span className={styles.detailValue}>{project.ownerName ?? (project as any).user_name ?? '未分配'}</span>
                    </div>
                    <div className={styles.detailItem}>
                      <span className={styles.detailLabel}>Agent 数</span>
                      <span className={styles.detailValue}>
                        {project.agentCount != null ? project.agentCount : '—'}
                      </span>
                    </div>
                    <div className={styles.detailItem}>
                      <span className={styles.detailLabel}>标签</span>
                      <span className={styles.detailValue}>
                        {project.tags?.length ? project.tags.join(' · ') : '—'}
                      </span>
                    </div>
                    <div className={styles.detailItem}>
                      <span className={styles.detailLabel}>选中</span>
                      <span className={styles.detailValue}>{isActive ? '当前查看' : '点击切换'}</span>
                    </div>
                  </div>
                  <div className={styles.buildActions}>
                    <Link
                      href={`/build?projectId=${encodeURIComponent(project.projectId)}`}
                      className={`${styles.button} ${styles.buttonPrimary} ${styles.buttonSmall}`}
                      onClick={(event) => event.stopPropagation()}
                    >
                      查看详情
                    </Link>
                    <button
                      type="button"
                      className={`${styles.button} ${styles.buttonSecondary} ${styles.buttonSmall}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        toast('日志模块暂未接入');
                      }}
                    >
                      查看日志
                    </button>
                    {project.status === 'building' ? (
                      <button
                        type="button"
                        className={`${styles.button} ${styles.buttonSecondary} ${styles.buttonSmall}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          toast('构建暂停功能即将上线');
                        }}
                      >
                        暂停
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })
          ) : (
            <div className={styles.emptyList}>暂无符合筛选条件的构建任务。</div>
          )}
        </div>
      </section>
    </div>
  );
}
