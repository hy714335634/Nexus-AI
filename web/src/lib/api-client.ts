import type { ApiResponse } from '@/types/api';

const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Get the base URL for API calls.
 * In browser environment, use relative paths so requests go through the same tunnel/proxy.
 * In server-side (SSR), use the configured absolute URL.
 */
function getBaseUrl(): string {
  // In browser environment, use relative path (empty string) to automatically use current origin
  // This ensures API calls go through the same tunnel/proxy as the frontend
  if (typeof window !== 'undefined') {
    return '';
  }
  
  // In server-side (SSR), use the configured absolute URL
  return DEFAULT_BASE_URL;
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly payload?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

async function parseJSON<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new ApiError(response.status, '无法解析服务器返回的数据', text);
  }
}

export async function apiFetch<TData>(
  path: string,
  init: RequestInit = {},
  baseUrl?: string,
): Promise<TData> {
  // Use provided baseUrl, or get default based on environment
  const effectiveBaseUrl = baseUrl ?? getBaseUrl();
  
  // If path is already absolute (starts with http:// or https://), use it directly
  // Otherwise, construct URL from baseUrl and path
  const url = path.startsWith('http') 
    ? path 
    : effectiveBaseUrl 
      ? `${effectiveBaseUrl.replace(/\/$/, '')}${path}`
      : path; // Relative path (empty baseUrl means use current origin)

  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const errorPayload = await parseJSON<ApiResponse<unknown>>(response).catch(() => undefined);
    const message =
      (errorPayload && typeof errorPayload === 'object' && 'error' in errorPayload
        ? String((errorPayload as { error?: { message?: string } }).error?.message ?? '请求失败')
        : '请求失败');
    throw new ApiError(response.status, message, errorPayload);
  }

  return parseJSON<TData>(response);
}
