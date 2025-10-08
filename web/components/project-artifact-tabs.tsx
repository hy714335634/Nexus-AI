'use client';

import { useMemo, useState } from 'react';
import type { ProjectArtifacts } from '@/types/projects';
import { CodeViewer } from '@components/viewer/code-viewer';

interface ProjectArtifactTabsProps {
  readonly artifacts?: ProjectArtifacts;
}

interface TabConfig {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly render: () => JSX.Element;
}

export function ProjectArtifactTabs({ artifacts }: ProjectArtifactTabsProps) {
  const tabs = useMemo<TabConfig[]>(() => {
    return [
      {
        id: 'requirement',
        label: '需求说明',
        description: '原始需求、业务上下文与成功标准。',
        render: () => (
          <CodeViewer
            content={artifacts?.requirementMarkdown ?? ''}
            language="markdown"
            filename="requirements.md"
            emptyFallback="暂无需求文档"
          />
        ),
      },
      {
        id: 'architecture',
        label: '系统架构',
        description: '规划的模块组成、模型选择与外部依赖。',
        render: () => (
          <CodeViewer
            content={artifacts?.architectureJson ? JSON.stringify(artifacts.architectureJson, null, 2) : ''}
            language="json"
            filename="architecture.json"
            emptyFallback="暂无架构数据"
          />
        ),
      },
      {
        id: 'tools',
        label: '工具配置',
        description: '内置工具定义与运行参数。',
        render: () => (
          <CodeViewer
            content={artifacts?.toolsJson ? JSON.stringify(artifacts.toolsJson, null, 2) : ''}
            language="json"
            filename="tools.json"
            emptyFallback="暂无工具配置"
          />
        ),
      },
      {
        id: 'prompt',
        label: '提示词',
        description: '主提示词/系统提示词模板。',
        render: () => (
          <CodeViewer
            content={artifacts?.promptText ?? ''}
            language="markdown"
            filename="prompt.txt"
            emptyFallback="暂无提示词内容"
          />
        ),
      },
      {
        id: 'agent-code',
        label: 'Agent 代码',
        description: '核心 Agent 实现或入口脚本。',
        render: () => (
          <CodeViewer
            content={artifacts?.agentCode ?? ''}
            language="python"
            filename="agent.py"
            emptyFallback="暂无 Agent 代码"
          />
        ),
      },
      {
        id: 'deployment',
        label: '部署记录',
        description: '最近一次部署信息与发布说明。',
        render: () => (
          <CodeViewer
            content={artifacts?.deploymentNotes ?? ''}
            language="markdown"
            filename="deployment.md"
            emptyFallback="暂无部署记录"
          />
        ),
      },
    ];
  }, [artifacts]);

  const [activeTab, setActiveTab] = useState(tabs[0]?.id ?? 'requirement');
  const current = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];

  if (!current) {
    return null;
  }

  return (
    <section
      style={{
        display: 'grid',
        gap: '16px',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        padding: '20px',
        background: 'rgba(12, 14, 24, 0.9)',
      }}
    >
      <header style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              type="button"
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 14px',
                borderRadius: '999px',
                border: isActive ? '1px solid rgba(34, 211, 238, 0.5)' : '1px solid rgba(255, 255, 255, 0.08)',
                background: isActive ? 'rgba(34, 211, 238, 0.15)' : 'transparent',
                color: '#fff',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </header>

      <div style={{ fontSize: '13px', color: 'var(--muted)' }}>{current.description}</div>

      <div>{current.render()}</div>
    </section>
  );
}
