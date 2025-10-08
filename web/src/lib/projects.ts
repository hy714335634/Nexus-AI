import { apiFetch } from '@/lib/api-client';
import type {
  AgentListResponse,
  AgentSummary,
  AgentDetailsResponse,
  StageTimelineResponse,
  StageTimelineResponseData,
  StageData,
} from '@/types/api';
import type { ProjectDetail, ProjectSummary } from '@/types/projects';

const SAMPLE_PROJECTS: ProjectSummary[] = [
  {
    projectId: 'demo-orchestrator',
    projectName: 'Autonomous Research Analyst',
    status: 'building',
    progressPercentage: 42,
    currentStage: 'agent_design',
    updatedAt: new Date().toISOString(),
    agentCount: 1,
    ownerName: 'Demo User',
    tags: ['demo', 'sample'],
  },
  {
    projectId: 'demo-deployed',
    projectName: 'Cloud Deployment Assistant',
    status: 'completed',
    progressPercentage: 100,
    currentStage: 'agent_deployer',
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    agentCount: 2,
    ownerName: 'Demo User',
    tags: ['production'],
  },
];

function buildSampleTimeline(projectId: string): StageTimelineResponseData {
  const stageBlueprint = [
    { id: 'orchestrator', label: '编排器', durationMinutes: 2, status: 'completed' as const },
    { id: 'requirements_analysis', label: '需求分析', durationMinutes: 8, status: 'completed' as const },
    { id: 'system_architecture', label: '系统架构', durationMinutes: 12, status: 'completed' as const },
    { id: 'agent_design', label: 'Agent 设计', durationMinutes: 15, status: 'running' as const },
    { id: 'agent_developer_manager', label: '开发管理', durationMinutes: 0, status: 'pending' as const },
    { id: 'agent_deployer', label: '部署中', durationMinutes: 0, status: 'pending' as const },
  ];

  const stages: StageData[] = [];
  let cursor = Date.now() - 60 * 60 * 1000; // 1 小时前开始

  for (let index = 0; index < stageBlueprint.length; index += 1) {
    const blueprint = stageBlueprint[index];
    const start = new Date(cursor);
    const end = new Date(cursor + blueprint.durationMinutes * 60 * 1000);

    const isCompleted = blueprint.status === 'completed';
    const isRunning = blueprint.status === 'running';

    stages.push({
      stage: blueprint.id as StageData['stage'],
      stage_number: index + 1,
      stage_name: blueprint.id,
      stage_name_cn: blueprint.label,
      status: blueprint.status,
      started_at: isCompleted || isRunning ? start.toISOString() : null,
      completed_at: isCompleted ? end.toISOString() : null,
      duration_seconds: isCompleted ? blueprint.durationMinutes * 60 : undefined,
      logs: isRunning ? ['initial-run'] : [],
      output_data: undefined,
      error_message: undefined,
      agent_name: undefined,
    });

    if (isCompleted) {
      cursor = end.getTime();
    } else if (isRunning) {
      cursor = Date.now();
    }
  }

  const completedStages = stages.filter((stage) => stage.status === 'completed').length;
  const overallProgress = Math.min(100, Math.round((completedStages / stages.length) * 100));

  return {
    project_id: projectId,
    total_stages: stages.length,
    completed_stages: completedStages,
    stages,
    overall_progress: overallProgress,
  };
}

function synthesizeFromAgents(agent: AgentSummary): ProjectSummary {
  const inferredProgress = agent.status === 'running' ? 100 : 35;
  const inferredStage = agent.status === 'running' ? 'agent_deployer' : 'agent_developer_manager';

  return {
    projectId: agent.project_id,
    projectName: agent.agent_name,
    status: agent.status === 'running' ? 'completed' : 'building',
    progressPercentage: inferredProgress,
    currentStage: inferredStage,
    updatedAt: agent.created_at,
    agentCount: 1,
    tags: [],
  };
}

export async function fetchProjectSummaries(): Promise<ProjectSummary[]> {
  const response = await apiFetch<AgentListResponse>('/api/v1/agents?limit=200').catch(() => undefined);

  if (!response?.success || !response.data?.agents?.length) {
    return SAMPLE_PROJECTS;
  }

  const projects = new Map<string, ProjectSummary>();

  for (const agent of response.data.agents) {
    const existing = projects.get(agent.project_id);
    if (existing) {
      existing.agentCount = (existing.agentCount ?? 0) + 1;
      existing.updatedAt = agent.created_at;
      continue;
    }

    projects.set(agent.project_id, synthesizeFromAgents(agent));
  }

  return Array.from(projects.values()).sort((a, b) => {
    const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
    const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
    return timeB - timeA;
  });
}

async function fetchProjectStages(projectId: string): Promise<StageTimelineResponseData | undefined> {
  const response = await apiFetch<StageTimelineResponse>(`/api/v1/agents/${projectId}/stages`).catch(() => undefined);
  if (!response?.success) {
    return undefined;
  }
  return response.data;
}

async function fetchAgentsForProject(projectId: string): Promise<AgentSummary[]> {
  const response = await apiFetch<AgentListResponse>('/api/v1/agents?limit=200').catch(() => undefined);
  if (!response?.success) {
    return [];
  }
  return response.data.agents.filter((agent) => agent.project_id === projectId);
}

async function fetchPrimaryAgent(projectId: string, agentId?: string) {
  if (!agentId) {
    return undefined;
  }
  const response = await apiFetch<AgentDetailsResponse>(`/api/v1/agents/${agentId}`).catch(() => undefined);
  if (!response?.success || response.data.project_id !== projectId) {
    return undefined;
  }
  return response.data;
}

export async function fetchProjectDetail(projectId: string): Promise<ProjectDetail | undefined> {
  const [summaries, stagePayload, agents] = await Promise.all([
    fetchProjectSummaries(),
    fetchProjectStages(projectId),
    fetchAgentsForProject(projectId),
  ]);

  const summary = summaries.find((project) => project.projectId === projectId);

  if (!summary) {
    return undefined;
  }

  const timeline = stagePayload ?? buildSampleTimeline(projectId);
  const stageList = timeline.stages?.length ? timeline.stages : buildSampleTimeline(projectId).stages;

  const primaryAgent = agents[0];
  const metadataAgent = await fetchPrimaryAgent(projectId, primaryAgent?.agent_id).catch(() => undefined);

  const failedStage = stageList.find((stage) => stage.status === 'failed');
  const runningStage = stageList.find((stage) => stage.status === 'running');
  const pendingStage = stageList.find((stage) => stage.status === 'pending');

  const progress = timeline.overall_progress ?? summary.progressPercentage;

  let latestTimestamp: string | undefined = summary.updatedAt;
  for (const stage of stageList) {
    const dateCandidate = stage.completed_at ?? stage.started_at;
    if (!dateCandidate) {
      continue;
    }
    if (!latestTimestamp || Date.parse(dateCandidate) > Date.parse(latestTimestamp)) {
      latestTimestamp = dateCandidate;
    }
  }

  const startedStage = stageList.find((stage) => stage.started_at);

  const detail: ProjectDetail = {
    ...summary,
    progressPercentage: progress,
    currentStage: runningStage?.stage ?? pendingStage?.stage ?? summary.currentStage,
    updatedAt: latestTimestamp ?? summary.updatedAt,
    stages: stageList,
    agents,
    agentCount: agents.length,
    startedAt: metadataAgent?.created_at ?? startedStage?.started_at ?? summary.updatedAt,
    estimatedCompletion: runningStage?.completed_at ?? pendingStage?.started_at ?? undefined,
    lastError: failedStage?.error_message ?? undefined,
    artifacts: summary.projectId.startsWith('demo')
      ? {
          requirementMarkdown:
            metadataAgent?.description
            || '## 目标\n- 构建一个具备上下文记忆的研究分析 Agent\n- 聚合多模态资料并输出结构化洞察',
          architectureJson: {
            orchestrator: 'bedrock.claude-v2',
            planner: 'internal.workflow_planner',
            tools: ['serp', 'vector-search', 'custom-python-executor'],
            persistence: {
              redis: true,
              vectorStore: 'opensearch',
            },
          },
          toolsJson: {
            retrieval: {
              description: '基于关键字的新闻检索',
              provider: 'newsapi',
            },
            summarizer: {
              description: '长文档分段总结',
              provider: 'bedrock.claude-instant',
            },
          },
          promptText:
            metadataAgent?.prompt_path
            || 'You are an autonomous research agent. Aggregate findings and respond in markdown tables.',
          agentCode:
            metadataAgent?.script_path
            || 'class ResearchAgent:\n    def run(self, query: str) -> str:\n        context = self.retriever.fetch(query)\n        summary = self.summarizer.summarize(context)\n        return self.formatter.to_markdown(summary)',
          deploymentNotes:
            '最新部署：us-west-2，运行在 AgentCore v1.2.0，启用灰度流量 15%。',
        }
      : undefined,
    errorContext:
      failedStage?.error_message
        ? [failedStage.error_message]
        : ['暂无错误记录', '监控正常'],
  };

  return detail;
}
