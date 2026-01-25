'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

// ============== Types ==============

export interface WorkflowStatus {
  project_id: string;
  project_name: string;
  status: string;
  control_status: string;
  current_stage: string | null;
  completed_stages: string[];
  pending_stages: string[];
  aggregated_metrics: {
    total_duration_seconds: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tool_calls: number;
  } | null;
}

export interface StageStatus {
  project_id: string;
  stage_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  metrics: Record<string, unknown> | null;
}

export interface WorkflowMetrics {
  project_id: string;
  stage_metrics: Record<string, Record<string, unknown>>;
  aggregated_metrics: Record<string, unknown>;
}

export interface StageOutput {
  project_id: string;
  stage_name: string;
  content: string;
  document_content: string | null;
  document_format: string | null;
  generated_files: Array<{
    path: string;
    type: string;
    size: number;
  }>;
}

export interface MultiAgentProgress {
  project_id: string;
  is_multi_agent: boolean;
  agent_count: number;
  orchestration_pattern: string | null;
  main_agent: string | null;
  agents: Array<{
    name: string;
    type: string;
    description: string;
    orchestration_pattern: string;
    dependencies: string[];
    tools: string[];
  }>;
  progress: Record<string, Record<string, unknown>>;
}

export interface ControlResponse {
  success: boolean;
  message: string;
  project_id: string;
  control_status: string;
  timestamp: string;
}

// ============== API Functions ==============

const API_BASE = '/api/v2/workflow';

async function fetchWorkflowStatus(projectId: string): Promise<WorkflowStatus> {
  const response = await fetch(`${API_BASE}/${projectId}/status`);
  if (!response.ok) {
    throw new Error('获取工作流状态失败');
  }
  return response.json();
}

async function fetchStageStatus(projectId: string, stageName: string): Promise<StageStatus> {
  const response = await fetch(`${API_BASE}/${projectId}/stages/${stageName}`);
  if (!response.ok) {
    throw new Error('获取阶段状态失败');
  }
  return response.json();
}

async function fetchWorkflowMetrics(projectId: string): Promise<WorkflowMetrics> {
  const response = await fetch(`${API_BASE}/${projectId}/metrics`);
  if (!response.ok) {
    throw new Error('获取工作流指标失败');
  }
  return response.json();
}

async function fetchStageOutput(projectId: string, stageName: string): Promise<StageOutput> {
  const response = await fetch(`${API_BASE}/${projectId}/stages/${stageName}/output`);
  if (!response.ok) {
    throw new Error('获取阶段输出失败');
  }
  return response.json();
}

async function fetchMultiAgentProgress(projectId: string): Promise<MultiAgentProgress> {
  const response = await fetch(`${API_BASE}/${projectId}/multi-agent/progress`);
  if (!response.ok) {
    throw new Error('获取多Agent进度失败');
  }
  return response.json();
}

async function pauseWorkflow(projectId: string, reason?: string): Promise<ControlResponse> {
  const response = await fetch(`${API_BASE}/${projectId}/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '暂停工作流失败');
  }
  return response.json();
}

async function resumeWorkflow(projectId: string, fromStage?: string): Promise<ControlResponse> {
  const response = await fetch(`${API_BASE}/${projectId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_stage: fromStage }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '恢复工作流失败');
  }
  return response.json();
}

async function stopWorkflow(projectId: string): Promise<ControlResponse> {
  const response = await fetch(`${API_BASE}/${projectId}/stop`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '停止工作流失败');
  }
  return response.json();
}

async function restartWorkflow(
  projectId: string, 
  fromStage: string, 
  clearSubsequent: boolean = true
): Promise<ControlResponse> {
  const response = await fetch(`${API_BASE}/${projectId}/restart`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_stage: fromStage, clear_subsequent: clearSubsequent }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '重启工作流失败');
  }
  return response.json();
}

// ============== Query Keys ==============

export const workflowKeys = {
  all: ['workflow'] as const,
  status: (projectId: string) => [...workflowKeys.all, 'status', projectId] as const,
  stage: (projectId: string, stageName: string) => [...workflowKeys.all, 'stage', projectId, stageName] as const,
  metrics: (projectId: string) => [...workflowKeys.all, 'metrics', projectId] as const,
  stageOutput: (projectId: string, stageName: string) => [...workflowKeys.all, 'output', projectId, stageName] as const,
  multiAgent: (projectId: string) => [...workflowKeys.all, 'multi-agent', projectId] as const,
};

// ============== Hooks ==============

/**
 * 获取工作流状态
 */
export function useWorkflowStatus(projectId: string, options?: { enabled?: boolean; refetchInterval?: number | false }) {
  return useQuery({
    queryKey: workflowKeys.status(projectId),
    queryFn: () => fetchWorkflowStatus(projectId),
    enabled: Boolean(projectId) && (options?.enabled !== false),
    staleTime: 5_000,
    refetchInterval: options?.refetchInterval ?? ((query) => {
      const data = query.state.data;
      if (!data) return false;
      // 如果工作流正在运行，每3秒刷新一次
      const isRunning = data.control_status === 'running' && 
        (data.status === 'building' || data.status === 'pending');
      return isRunning ? 3_000 : false;
    }),
  });
}

/**
 * 获取阶段状态
 */
export function useStageStatus(projectId: string, stageName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: workflowKeys.stage(projectId, stageName),
    queryFn: () => fetchStageStatus(projectId, stageName),
    enabled: Boolean(projectId) && Boolean(stageName) && (options?.enabled !== false),
    staleTime: 10_000,
  });
}

/**
 * 获取工作流指标
 */
export function useWorkflowMetrics(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: workflowKeys.metrics(projectId),
    queryFn: () => fetchWorkflowMetrics(projectId),
    enabled: Boolean(projectId) && (options?.enabled !== false),
    staleTime: 30_000,
  });
}

/**
 * 获取阶段输出
 */
export function useStageOutput(projectId: string, stageName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: workflowKeys.stageOutput(projectId, stageName),
    queryFn: () => fetchStageOutput(projectId, stageName),
    enabled: Boolean(projectId) && Boolean(stageName) && (options?.enabled !== false),
    staleTime: 60_000,
  });
}

/**
 * 获取多Agent进度
 */
export function useMultiAgentProgress(projectId: string, options?: { enabled?: boolean; refetchInterval?: number | false }) {
  return useQuery({
    queryKey: workflowKeys.multiAgent(projectId),
    queryFn: () => fetchMultiAgentProgress(projectId),
    enabled: Boolean(projectId) && (options?.enabled !== false),
    staleTime: 5_000,
    refetchInterval: options?.refetchInterval,
  });
}

/**
 * 暂停工作流
 */
export function usePauseWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ projectId, reason }: { projectId: string; reason?: string }) => 
      pauseWorkflow(projectId, reason),
    onSuccess: (data, variables) => {
      toast.success('工作流已暂停');
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(variables.projectId) });
    },
    onError: (error: Error) => {
      toast.error(`暂停失败: ${error.message}`);
    },
  });
}

/**
 * 恢复工作流
 */
export function useResumeWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ projectId, fromStage }: { projectId: string; fromStage?: string }) => 
      resumeWorkflow(projectId, fromStage),
    onSuccess: (data, variables) => {
      toast.success('工作流已恢复');
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(variables.projectId) });
    },
    onError: (error: Error) => {
      toast.error(`恢复失败: ${error.message}`);
    },
  });
}

/**
 * 停止工作流
 */
export function useStopWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (projectId: string) => stopWorkflow(projectId),
    onSuccess: (data, projectId) => {
      toast.success('工作流已停止');
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(projectId) });
    },
    onError: (error: Error) => {
      toast.error(`停止失败: ${error.message}`);
    },
  });
}

/**
 * 重启工作流
 */
export function useRestartWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ projectId, fromStage, clearSubsequent = true }: { 
      projectId: string; 
      fromStage: string; 
      clearSubsequent?: boolean;
    }) => restartWorkflow(projectId, fromStage, clearSubsequent),
    onSuccess: (data, variables) => {
      toast.success(`工作流已从 ${variables.fromStage} 重启`);
      queryClient.invalidateQueries({ queryKey: workflowKeys.status(variables.projectId) });
    },
    onError: (error: Error) => {
      toast.error(`重启失败: ${error.message}`);
    },
  });
}

/**
 * 组合 hook：工作流控制面板所需的所有功能
 */
export function useWorkflowControl(projectId: string) {
  const status = useWorkflowStatus(projectId);
  const metrics = useWorkflowMetrics(projectId);
  const multiAgent = useMultiAgentProgress(projectId);
  
  const pause = usePauseWorkflow();
  const resume = useResumeWorkflow();
  const stop = useStopWorkflow();
  const restart = useRestartWorkflow();
  
  const isLoading = status.isLoading || metrics.isLoading;
  const isRunning = status.data?.control_status === 'running';
  const isPaused = status.data?.control_status === 'paused';
  const isStopped = status.data?.control_status === 'stopped';
  const isCompleted = status.data?.status === 'completed';
  const isFailed = status.data?.status === 'failed';
  
  return {
    // 状态数据
    status: status.data,
    metrics: metrics.data,
    multiAgent: multiAgent.data,
    isLoading,
    
    // 状态标志
    isRunning,
    isPaused,
    isStopped,
    isCompleted,
    isFailed,
    
    // 控制操作
    pause: (reason?: string) => pause.mutate({ projectId, reason }),
    resume: (fromStage?: string) => resume.mutate({ projectId, fromStage }),
    stop: () => stop.mutate(projectId),
    restart: (fromStage: string, clearSubsequent?: boolean) => 
      restart.mutate({ projectId, fromStage, clearSubsequent }),
    
    // 操作状态
    isPausing: pause.isPending,
    isResuming: resume.isPending,
    isStopping: stop.isPending,
    isRestarting: restart.isPending,
    
    // 刷新
    refetch: () => {
      status.refetch();
      metrics.refetch();
      multiAgent.refetch();
    },
  };
}
