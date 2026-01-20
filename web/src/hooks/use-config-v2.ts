'use client';

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions, useQueryClient } from '@tanstack/react-query';

// ============== Types ==============
export interface ConfigFile {
  name: string;
  path: string;
  size: number;
  modified_at: string;
  type: 'yaml' | 'json';
}

export interface ConfigFileContent {
  filename: string;
  content: Record<string, unknown>;
  raw_content: string;
  type: 'yaml' | 'json';
}

export interface ConfigListResponse {
  success: boolean;
  data?: {
    files: ConfigFile[];
    config_dir: string;
  };
  message?: string;
}

export interface ConfigDetailResponse {
  success: boolean;
  data?: ConfigFileContent;
  message?: string;
}

export interface ConfigValidateResponse {
  success: boolean;
  data?: {
    valid: boolean;
    parsed?: Record<string, unknown>;
    error?: string;
  };
  message?: string;
}

// ============== API Functions ==============
const API_BASE = '/api/v2';

async function fetchConfigFiles(): Promise<ConfigListResponse> {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) {
    const errorText = await response.text();
    console.error('Failed to fetch config files:', response.status, errorText);
    throw new Error('获取配置文件列表失败');
  }
  const data = await response.json();
  console.log('Config files response:', data);
  return data;
}

async function fetchConfigFile(filename: string): Promise<ConfigDetailResponse> {
  const response = await fetch(`${API_BASE}/config/${encodeURIComponent(filename)}`);
  if (!response.ok) {
    throw new Error(`获取配置文件 ${filename} 失败`);
  }
  return response.json();
}

async function updateConfigFile(filename: string, rawContent: string): Promise<{ success: boolean; message?: string }> {
  const response = await fetch(`${API_BASE}/config/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_content: rawContent }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || '更新配置文件失败');
  }
  return response.json();
}

async function validateConfig(filename: string, rawContent: string): Promise<ConfigValidateResponse> {
  const response = await fetch(`${API_BASE}/config/${encodeURIComponent(filename)}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_content: rawContent }),
  });
  if (!response.ok) {
    throw new Error('验证配置失败');
  }
  return response.json();
}

async function restoreConfigBackup(filename: string): Promise<{ success: boolean; message?: string }> {
  const response = await fetch(`${API_BASE}/config/${encodeURIComponent(filename)}/restore`, {
    method: 'POST',
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || '恢复配置备份失败');
  }
  return response.json();
}

// ============== Query Keys ==============
export const configKeys = {
  all: ['v2', 'config'] as const,
  list: () => [...configKeys.all, 'list'] as const,
  detail: (filename: string) => [...configKeys.all, 'detail', filename] as const,
};

// ============== Hooks ==============

export function useConfigFilesV2(
  options?: Omit<UseQueryOptions<ConfigFile[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ConfigFile[]>({
    queryKey: configKeys.list(),
    queryFn: async () => {
      const response = await fetchConfigFiles();
      return response.data?.files || [];
    },
    staleTime: 30_000,
    ...options,
  });
}

export function useConfigFileV2(
  filename: string,
  options?: Omit<UseQueryOptions<ConfigFileContent | null, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ConfigFileContent | null>({
    queryKey: configKeys.detail(filename),
    queryFn: async () => {
      const response = await fetchConfigFile(filename);
      return response.data || null;
    },
    enabled: Boolean(filename),
    staleTime: 10_000,
    ...options,
  });
}

export function useUpdateConfigV2(
  options?: UseMutationOptions<
    { success: boolean; message?: string },
    Error,
    { filename: string; rawContent: string }
  >
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ filename, rawContent }) => {
      return updateConfigFile(filename, rawContent);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: configKeys.detail(variables.filename) });
      queryClient.invalidateQueries({ queryKey: configKeys.list() });
    },
    ...options,
  });
}

export function useValidateConfigV2(
  options?: UseMutationOptions<
    { valid: boolean; parsed?: Record<string, unknown>; error?: string },
    Error,
    { filename: string; rawContent: string }
  >
) {
  return useMutation({
    mutationFn: async ({ filename, rawContent }) => {
      const response = await validateConfig(filename, rawContent);
      return response.data || { valid: false, error: '验证失败' };
    },
    ...options,
  });
}

export function useRestoreConfigV2(
  options?: UseMutationOptions<{ success: boolean; message?: string }, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (filename: string) => {
      return restoreConfigBackup(filename);
    },
    onSuccess: (_, filename) => {
      queryClient.invalidateQueries({ queryKey: configKeys.detail(filename) });
    },
    ...options,
  });
}
