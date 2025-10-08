'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { createAgent } from '@/lib/agents';
import type { CreateAgentRequest } from '@/types/api';
import type { ProjectSummary } from '@/types/projects';
import { LoadingState } from '@components/feedback/loading-state';
import { ErrorState } from '@components/feedback/error-state';

interface FormState {
  requirement: string;
  user_id: string;
  user_name: string;
  priority: number;
  tags: string;
}

const INITIAL_STATE: FormState = {
  requirement: '',
  user_id: 'console-user',
  user_name: 'Console User',
  priority: 3,
  tags: '',
};

type Step = 'requirement' | 'metadata';

const STEPS: { id: Step; title: string; description: string }[] = [
  {
    id: 'requirement',
    title: '需求描述',
    description: '说明你希望构建的 Agent 目标、输入输出和关键限制。',
  },
  {
    id: 'metadata',
    title: '任务参数',
    description: '配置调用信息并快速确认提交内容。',
  },
];

function parseTags(input: string) {
  return input
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function requirementError(requirement: string) {
  const trimmed = requirement.trim();
  if (!trimmed) {
    return '需求描述不能为空';
  }

  if (trimmed.length < 10) {
    return '至少需要 10 个字符';
  }

  return undefined;
}

export function NewAgentView() {
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [stepIndex, setStepIndex] = useState(0);
  const [submittedTaskId, setSubmittedTaskId] = useState<string | null>(null);

  const router = useRouter();
  const queryClient = useQueryClient();
  const currentStep = STEPS[stepIndex];
  const isLastStep = stepIndex === STEPS.length - 1;
  const requirementValidation = useMemo(() => requirementError(form.requirement), [form.requirement]);

  const mutation = useMutation({
    mutationFn: (payload: CreateAgentRequest) => createAgent(payload),
    onSuccess: (data, variables) => {
      setSubmittedTaskId(data.task_id);
      toast.success('已提交构建任务', {
        description: `项目 ${data.project_id} 正在排队构建。`,
      });

      const optimisticProject: ProjectSummary = {
        projectId: data.project_id,
        projectName: variables.requirement.slice(0, 60) || data.project_id,
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
        const without = existing.filter((project) => project.projectId !== optimisticProject.projectId);
        return [optimisticProject, ...without];
      });

      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });

      setTimeout(() => router.push(`/projects/${data.project_id}`), 600);
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : '提交失败，请稍后重试';
      toast.error('提交失败', { description: message });
    },
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.reset();
    setSubmittedTaskId(null);

    const payload: CreateAgentRequest = {
      requirement: form.requirement.trim(),
      user_id: form.user_id.trim(),
      user_name: form.user_name.trim(),
      priority: form.priority,
      tags: parseTags(form.tags),
    };

    mutation.mutate(payload);
  };

  const canProceed =
    currentStep.id === 'requirement'
      ? !requirementValidation
      : form.user_id.trim().length > 0 && form.user_name.trim().length > 0;

  const nextStep = () => {
    if (!canProceed || isLastStep) {
      return;
    }
    setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
  };

  const prevStep = () => {
    setStepIndex((index) => Math.max(index - 1, 0));
  };

  return (
    <section style={{ display: 'grid', gap: '24px' }}>
      <header>
        <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 600 }}>新建代理构建任务</h1>
        <p style={{ margin: '6px 0 0', fontSize: '14px', color: 'var(--muted)' }}>
          按步骤提供上下文，系统将自动启动端到端流水线。
        </p>
      </header>

      <nav
        aria-label="构建向导"
        style={{
          display: 'flex',
          gap: '16px',
          flexWrap: 'wrap',
          padding: '12px 20px',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(17, 20, 31, 0.75)',
        }}
      >
        {STEPS.map((step, index) => {
          const isActive = index === stepIndex;
          const isCompleted = index < stepIndex;

          return (
            <div
              key={step.id}
              style={{
                display: 'flex',
                gap: '10px',
                alignItems: 'center',
                opacity: isActive || isCompleted ? 1 : 0.65,
              }}
            >
              <span
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '999px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: isCompleted ? 'rgba(34,211,238,0.25)' : 'rgba(79,70,229,0.25)',
                  border: isActive
                    ? '1px solid rgba(34,211,238,0.6)'
                    : '1px solid rgba(255,255,255,0.12)',
                  color: '#fff',
                  fontWeight: 600,
                }}
              >
                {index + 1}
              </span>
              <div style={{ display: 'grid', gap: '4px' }}>
                <span style={{ fontWeight: 600 }}>{step.title}</span>
                <span style={{ fontSize: '12px', color: 'var(--muted)' }}>{step.description}</span>
              </div>
            </div>
          );
        })}
      </nav>

      <form
        onSubmit={onSubmit}
        style={{
          display: 'grid',
          gap: '20px',
          padding: '24px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(15, 16, 24, 0.92)',
        }}
      >
        {currentStep.id === 'requirement' ? (
          <label style={{ display: 'grid', gap: '12px' }}>
            <span style={{ fontSize: '14px', color: 'var(--muted)' }}>需求描述 *</span>
            <textarea
              required
              rows={8}
              value={form.requirement}
              onChange={(event) => setForm((prev) => ({ ...prev, requirement: event.target.value }))}
              placeholder="描述目标、输入、产出和关键约束。"
              style={{
                padding: '14px',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                background: 'rgba(255, 255, 255, 0.04)',
                color: '#fff',
                resize: 'vertical',
              }}
            />
            {requirementValidation ? (
              <span style={{ fontSize: '12px', color: '#f87171' }}>{requirementValidation}</span>
            ) : null}
          </label>
        ) : null}

        {currentStep.id === 'metadata' ? (
          <div style={{ display: 'grid', gap: '18px' }}>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '16px',
              }}
            >
              <label style={{ display: 'grid', gap: '8px' }}>
                <span style={{ fontSize: '14px', color: 'var(--muted)' }}>用户 ID *</span>
                <input
                  required
                  value={form.user_id}
                  onChange={(event) => setForm((prev) => ({ ...prev, user_id: event.target.value }))}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#fff',
                  }}
                />
              </label>

              <label style={{ display: 'grid', gap: '8px' }}>
                <span style={{ fontSize: '14px', color: 'var(--muted)' }}>用户名称 *</span>
                <input
                  required
                  value={form.user_name}
                  onChange={(event) => setForm((prev) => ({ ...prev, user_name: event.target.value }))}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#fff',
                  }}
                />
              </label>

              <label style={{ display: 'grid', gap: '8px' }}>
                <span style={{ fontSize: '14px', color: 'var(--muted)' }}>优先级 (1-5)</span>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={form.priority}
                  onChange={(event) => setForm((prev) => ({ ...prev, priority: Number(event.target.value) }))}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: '#fff',
                  }}
                />
              </label>
            </div>

            <label style={{ display: 'grid', gap: '8px' }}>
              <span style={{ fontSize: '14px', color: 'var(--muted)' }}>标签 (逗号分隔)</span>
              <input
                value={form.tags}
                onChange={(event) => setForm((prev) => ({ ...prev, tags: event.target.value }))}
                placeholder="research, qa, internal"
                style={{
                  padding: '10px 12px',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: '#fff',
                }}
              />
            </label>

            <div
              style={{
                display: 'grid',
                gap: '12px',
                padding: '18px',
                borderRadius: '12px',
                border: '1px solid rgba(34, 211, 238, 0.3)',
                background: 'rgba(13, 148, 136, 0.08)',
              }}
            >
              <div style={{ fontWeight: 600 }}>提交前确认</div>
              <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--muted)', fontSize: '13px', lineHeight: 1.6 }}>
                <li>需求描述将同步到 orchestrator 环节。</li>
                <li>提交后可以在项目列表中查看阶段进度。</li>
                <li>若要修改配置，可在构建完成后重新发起任务。</li>
              </ul>
            </div>
          </div>
        ) : null}

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ fontSize: '13px', color: 'var(--muted)' }}>
            步骤 {stepIndex + 1} / {STEPS.length}
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {stepIndex > 0 ? (
              <button
                type="button"
                onClick={prevStep}
                style={{
                  padding: '10px 18px',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  background: 'transparent',
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                上一步
              </button>
            ) : null}

            {!isLastStep ? (
              <button
                type="button"
                disabled={!canProceed}
                onClick={nextStep}
                style={{
                  padding: '10px 18px',
                  borderRadius: '12px',
                  border: 'none',
                  background: canProceed
                    ? 'linear-gradient(135deg, #22d3ee, #6366f1)'
                    : 'rgba(255, 255, 255, 0.08)',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: canProceed ? 'pointer' : 'not-allowed',
                }}
              >
                下一步
              </button>
            ) : (
              <button
                type="submit"
                disabled={mutation.isPending || !canProceed}
                style={{
                  padding: '12px 20px',
                  borderRadius: '12px',
                  border: 'none',
                  background: mutation.isPending
                    ? 'rgba(255, 255, 255, 0.12)'
                    : 'linear-gradient(135deg, #16a34a, #22c55e)',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: mutation.isPending ? 'wait' : 'pointer',
                }}
              >
                {mutation.isPending ? '提交中…' : '提交构建任务'}
              </button>
            )}
          </div>
        </div>
      </form>

      {mutation.isPending ? <LoadingState message="正在提交构建任务…" /> : null}
      {mutation.isError ? <ErrorState description="提交失败，请稍后重试" /> : null}

      {submittedTaskId ? (
        <section
          style={{
            padding: '20px',
            borderRadius: '16px',
            border: '1px solid rgba(34, 211, 238, 0.3)',
            background: 'rgba(20, 184, 166, 0.1)',
            display: 'grid',
            gap: '6px',
          }}
        >
          <div style={{ fontWeight: 600 }}>构建任务已创建</div>
          <div style={{ fontSize: '14px', color: 'var(--muted)' }}>任务 ID：{submittedTaskId}</div>
          <div style={{ fontSize: '13px', color: 'var(--muted)' }}>
            即将跳转到项目详情，可随时在项目列表中查看实时状态。
          </div>
        </section>
      ) : null}
    </section>
  );
}
