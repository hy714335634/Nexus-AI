/**
 * 认证工具函数
 */

export interface User {
  username: string;
  authenticated: boolean;
}

/**
 * 检查用户是否已登录
 */
export async function checkAuth(): Promise<User | null> {
  try {
    const response = await fetch('/api/v1/auth/check', {
      credentials: 'include',
    });

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch {
    return null;
  }
}

/**
 * 登出
 */
export async function logout(): Promise<void> {
  try {
    await fetch('/api/v1/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // 忽略错误
  }

  // 清除本地存储
  localStorage.removeItem('access_token');
  localStorage.removeItem('username');

  // 跳转到登录页
  window.location.href = '/login';
}

/**
 * 获取当前用户名
 */
export function getCurrentUsername(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('username');
}
