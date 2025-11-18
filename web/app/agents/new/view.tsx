'use client';

import { FormEvent, KeyboardEvent, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import styles from './new-agent.module.css';
import { createAgent } from '@/lib/agents';
import type { CreateAgentRequest } from '@/types/api';
import type { ProjectSummary } from '@/types/projects';
import { useProjectSummaries } from '@/hooks/use-projects';

interface FormState {
  requirement: string;
  agentName: string;
  userId: string;
  userName: string;
  priority: number;
  tags: string[];
}

const INITIAL_FORM: FormState = {
  requirement: '',
  agentName: '',
  userId: 'console-user',
  userName: 'Console User',
  priority: 3,
  tags: [],
};

const QUICK_START_TEMPLATES: Array<{
  id: string;
  title: string;
  description: string;
  requirement: string;
  agentName: string;
  tags: string[];
}> = [
  {
    id: 'file-summary',
    title: '📄 文件摘要助理',
    description: '自动读取多格式文档并生成结构化摘要、要点和后续行动建议。',
    requirement:
      '帮我构建一个可以自动读取 PDF、Word、Markdown 等多种格式文件，并输出结构化摘要的 Agent，要包含关键要点、风险提示以及可执行建议。',
    agentName: '结构化文件摘要官',
    tags: ['summary', 'document', 'analysis'],
  },
  {
    id: 'ops-incident',
    title: '🛡️ 运维巡检助手',
    description: '每日拉取监控数据，生成巡检日报与异常告警，支持多渠道通知。',
    requirement:
      '我需要一个自动化运维巡检 Agent，可以每天早上 7 点汇总监控指标、异常日志与告警信息，输出日报并通过飞书推送。',
    agentName: '云原生巡检助手',
    tags: ['ops', 'monitor', 'daily-report'],
  },
  {
    id: 'sales-insight',
    title: '📈 销售洞察分析师',
    description: '整合 CRM 与 BI 数据，自动生成周度复盘和 KPI 趋势报告。',
    requirement:
      '构建一个销售洞察 Agent，能够拉取 CRM 数据，生成周度复盘报告，重点包含成交趋势、客户画像和重点跟进建议。',
    agentName: '销售洞察分析师',
    tags: ['sales', 'crm', 'insight'],
  },
];

const STAGE_PIPELINE: Array<{ id: string; title: string; description: string }> = [
  {
    id: 'requirements_analyzer',
    title: '需求分析',
    description: '识别目标与约束，补充业务上下文与验收标准。',
  },
  {
    id: 'system_architect',
    title: '系统设计',
    description: '定义智能体架构、记忆策略及外部系统对接方案。',
  },
  {
    id: 'agent_designer',
    title: 'Agent 设计',
    description: '构建角色设定、对话分层与响应样式。',
  },
  {
    id: 'agent_developer_manager',
    title: '交付管理',
    description: '整合工件、联调测试，并评估交付质量。',
  },
];

const SUGGESTED_TAGS = ['internal', 'automation', 'analysis', 'mcp', 'customer-service', 'qa'];

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function parseTagInput(source: string): string[] {
  return source
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function NewAgentView() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [tagInput, setTagInput] = useState('');
  const [submittedTask, setSubmittedTask] = useState<{ id: string; name?: string } | null>(null);

  const { data: projectSummaries, isLoading: statsLoading, isError: statsError } = useProjectSummaries();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload: CreateAgentRequest) => createAgent(payload),
    onSuccess: (data, variables) => {
      setSubmittedTask({ id: data.task_id, name: data.agent_name ?? variables.agent_name });
      toast.success('已提交构建任务', {
        description: `${data.agent_name ?? variables.agent_name ?? data.project_id} 正在创建中`,
      });

      const optimistic: ProjectSummary = {
        projectId: data.project_id,
        projectName: variables.agent_name || variables.requirement.slice(0, 60) || data.project_id,
        status: 'building',
        progressPercentage: 0,
        currentStage: 'orchestrator',
        updatedAt: new Date().toISOString(),
        agentCount: 0,
        ownerName: variables.user_name || undefined,
        tags: variables.tags && variables.tags.length ? variables.tags : undefined,
      };

      queryClient.setQueryData<ProjectSummary[] | undefined>(['projects', 'summaries'], (current) => {
        const existing = current ?? [];
        const filtered = existing.filter((item) => item.projectId !== optimistic.projectId);
        return [optimistic, ...filtered];
      });
      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });
      setForm((prev) => ({ ...INITIAL_FORM, userId: prev.userId, userName: prev.userName }));
      setTagInput('');
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : '提交失败，请稍后重试';
      toast.error('提交失败', { description: message });
    },
  });

  const stats = useMemo(() => {
    const list = projectSummaries ?? [];
    if (!list.length) {
      return {
        total: 0,
        building: 0,
        completed: 0,
        successRate: 0,
        averageProgress: 0,
      };
    }

    const total = list.length;
    const building = list.filter((item) => item.status === 'building').length;
    const completed = list.filter((item) => item.status === 'completed').length;
    const averageProgress =
      list.reduce((sum, item) => sum + (item.progressPercentage ?? 0), 0) / Math.max(total, 1) / 100;
    const successRate = completed / total;

    return {
      total,
      building,
      completed,
      successRate,
      averageProgress,
    };
  }, [projectSummaries]);

  const canSubmit = form.requirement.trim().length >= 10 && form.userId.trim() && form.userName.trim();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || mutation.isPending) {
      return;
    }

    mutation.reset();
    const mergedTags = Array.from(new Set([...form.tags, ...parseTagInput(tagInput)])).map((tag) => tag.trim());

    const payload: CreateAgentRequest = {
      requirement: form.requirement.trim(),
      user_id: form.userId.trim(),
      user_name: form.userName.trim(),
      agent_name: form.agentName.trim() || undefined,
      priority: form.priority,
      tags: mergedTags,
    };

    mutation.mutate(payload);
  };

  const addSuggestedTag = (tag: string) => {
    if (form.tags.includes(tag)) {
      return;
    }
    setForm((prev) => ({ ...prev, tags: [...prev.tags, tag] }));
  };

  const removeTag = (tag: string) => {
    setForm((prev) => ({ ...prev, tags: prev.tags.filter((item) => item !== tag) }));
  };

  const handleTagInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    const value = (event.currentTarget.value || '').trim();
    if (!value) {
      return;
    }
    addSuggestedTag(value);
    setTagInput('');
  };

  const applyTemplate = (templateId: string) => {
    const template = QUICK_START_TEMPLATES.find((item) => item.id === templateId);
    if (!template) {
      return;
    }
    setForm((prev) => ({
      ...prev,
      requirement: template.requirement,
      agentName: template.agentName,
      tags: Array.from(new Set([...prev.tags, ...template.tags])),
    }));
    toast('已应用预设模板', { description: template.title });
  };

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroLabel}>
          <span>🚀 智能体构建中心</span>
          <span>端到端工作流 · 60 秒即可提交</span>
        </div>
        <h1 className={styles.heroTitle}>完成需求表述，剩下交给 Nexus-AI</h1>
        <p className={styles.heroSubtitle}>
          只需描述业务诉求，系统将自动完成需求解析、架构设计、Agent 生成与交付验证，实现智能体的全链路构建。
        </p>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>累计构建</div>
            <div className={styles.statValue}>{stats.total}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>进行中</div>
            <div className={styles.statValue}>{stats.building}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>成功率</div>
            <div className={styles.statValue}>{formatPercent(stats.successRate)}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>平均进度</div>
            <div className={styles.statValue}>{formatPercent(stats.averageProgress)}</div>
          </div>
        </div>
        {statsLoading ? <span className={styles.loadingBanner}>加载构建概览…</span> : null}
        {statsError ? <span className={styles.errorCard}>统计数据暂时不可用，请稍后刷新。</span> : null}
      </section>

      <section className={styles.quickStart}>
        <div className={styles.sectionHeading}>
          <div>
            <div className={styles.sectionTitle}>快速开始</div>
            <div className={styles.sectionDescription}>选择预设模板即可自动填充需求描述与推荐标签。</div>
          </div>
        </div>
        <div className={styles.quickStartGrid}>
          {QUICK_START_TEMPLATES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={styles.quickStartCard}
              onClick={() => applyTemplate(item.id)}
            >
              <div className={styles.quickStartTitle}>{item.title}</div>
              <div className={styles.quickStartBody}>{item.description}</div>
              <div className={styles.tagList}>
                {item.tags.map((tag) => (
                  <span key={tag} className={styles.tagChip}>
                    #{tag}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </section>

      <form className={styles.formSection} onSubmit={handleSubmit}>
        <div className={styles.formHeader}>
          <div className={styles.formHeaderText}>
            <div className={styles.formTitle}>填写需求，生成智能体方案</div>
            <p className={styles.formSubtitle}>
              描述你要解决的问题，越具体越好。系统会自动完成需求拆解、角色设计、提示词编排与代码生成。
            </p>
          </div>
          <div className={styles.statusBadge}>
            <span>⚡ 全流程自动构建</span>
            <span>8 个阶段实时可视</span>
          </div>
        </div>

        <div className={styles.formCard}>
          <div className={styles.formBody}>
            <div className={styles.requirementColumn}>
              <label className={styles.label}>
                <span>需求描述 *</span>
                <textarea
                  className={styles.textArea}
                  placeholder="描述业务目标、输入输出、关键约束、上下文示例等。"
                  value={form.requirement}
                  onChange={(event) => setForm((prev) => ({ ...prev, requirement: event.target.value }))}
                  required
                />
                <span className={styles.helperText}>不少于 10 个字符，包含角色定位、目标指标或差异化要求更佳。</span>
              </label>
            </div>

            <aside className={styles.metadataColumn}>
              <label className={styles.label}>
                <span>Agent 名称</span>
                <input
                  className={styles.input}
                  placeholder="例如：客户服务质检官"
                  value={form.agentName}
                  onChange={(event) => setForm((prev) => ({ ...prev, agentName: event.target.value }))}
                />
              </label>

              <label className={styles.label}>
                <span>创建人 ID *</span>
                <input
                  className={styles.input}
                  value={form.userId}
                  onChange={(event) => setForm((prev) => ({ ...prev, userId: event.target.value }))}
                  required
                />
              </label>

              <label className={styles.label}>
                <span>创建人姓名 *</span>
                <input
                  className={styles.input}
                  value={form.userName}
                  onChange={(event) => setForm((prev) => ({ ...prev, userName: event.target.value }))}
                  required
                />
              </label>

              <label className={styles.label}>
                <span>优先级 (1-5)</span>
                <input
                  className={styles.input}
                  type="number"
                  min={1}
                  max={5}
                  value={form.priority}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, priority: Number.parseInt(event.target.value || '3', 10) }))
                  }
                />
              </label>

              <div>
                <div className={styles.label}>
                  <span>推荐标签</span>
                  <span className={styles.helperText}>点击即可添加，支持自定义标签。</span>
                </div>
                <div className={styles.tagList}>
                  {SUGGESTED_TAGS.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      className={styles.tagChip}
                      onClick={() => addSuggestedTag(tag)}
                    >
                      #{tag}
                    </button>
                  ))}
                </div>
                {form.tags.length ? (
                  <div className={styles.tagList} style={{ marginTop: 12 }}>
                    {form.tags.map((tag) => (
                      <button
                        type="button"
                        key={tag}
                        className={styles.tagChip}
                        onClick={() => removeTag(tag)}
                        title="点击移除"
                      >
                        ✕ {tag}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <label className={styles.label}>
                <span>自定义标签</span>
                <input
                  className={styles.input}
                  placeholder="输入后回车添加"
                  value={tagInput}
                  onChange={(event) => setTagInput(event.target.value)}
                  onKeyDown={handleTagInputKeyDown}
                />
              </label>
            </aside>
          </div>

          <div className={styles.submitBar}>
            <div>
              <div className={styles.helperText}>
                👣 构建流水线：需求分析 → 架构设计 → Agent 设计 → 交付管理 → 部署验证
              </div>
              {mutation.isPending ? <span className={styles.loadingBanner}>正在提交构建任务…</span> : null}
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={`${styles.actionButton} ${styles.secondary}`}
                onClick={() => {
                  setForm((prev) => ({ ...INITIAL_FORM, userId: prev.userId, userName: prev.userName }));
                  setTagInput('');
                }}
              >
                清空表单
              </button>
              <button
                type="submit"
                className={`${styles.actionButton} ${styles.primary}`}
                disabled={!canSubmit || mutation.isPending}
              >
                {mutation.isPending ? '提交中…' : '提交构建任务'}
              </button>
            </div>
          </div>
        </div>
      </form>

      {submittedTask ? (
        <section className={styles.successCard}>
          <div style={{ fontWeight: 600 }}>构建任务已创建</div>
          <div>任务 ID：{submittedTask.id}</div>
          {submittedTask.name ? <div>Agent 名称：{submittedTask.name}</div> : null}
          <div>你可以在构建模块中查看实时进度与阶段日志。</div>
        </section>
      ) : null}

      {mutation.isError ? (
        <section className={styles.errorCard}>
          <div style={{ fontWeight: 600 }}>提交失败</div>
          <div>请稍后重试，或检查网络与表单内容是否符合要求。</div>
        </section>
      ) : null}

      <section className={styles.pipeline}>
        <div className={styles.sectionHeading}>
          <div>
            <div className={styles.sectionTitle}>标准构建流水线</div>
            <div className={styles.sectionDescription}>
              每个阶段都有专属 Agent 负责交付，系统会自动协调协作并沉淀可复用工件。
            </div>
          </div>
        </div>
        <div className={styles.pipelineGrid}>
          {STAGE_PIPELINE.map((stage) => (
            <div key={stage.id} className={styles.pipelineCard}>
              <div className={styles.pipelineTitle}>{stage.title}</div>
              <div className={styles.pipelineMeta}>{stage.description}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
