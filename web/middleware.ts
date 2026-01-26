import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 不需要认证的路径
const PUBLIC_PATHS = [
  '/login',
  '/api/v1/auth/login',
  '/api/v2/auth/login',
  '/api/v1/auth/check',
  '/api/v2/auth/check',
  '/_next',
  '/favicon.ico',
  '/health',
];

// 静态资源扩展名
const STATIC_EXTENSIONS = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 检查是否是公开路径
  const isPublicPath = PUBLIC_PATHS.some(path => pathname.startsWith(path));
  if (isPublicPath) {
    return NextResponse.next();
  }

  // 检查是否是静态资源
  const isStaticResource = STATIC_EXTENSIONS.some(ext => pathname.endsWith(ext));
  if (isStaticResource) {
    return NextResponse.next();
  }

  // 检查 cookie 中的 token
  const token = request.cookies.get('access_token')?.value;

  // 如果没有 token，重定向到登录页
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 有 token，继续请求
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * 匹配所有路径，除了:
     * - _next/static (静态文件)
     * - _next/image (图片优化)
     * - favicon.ico (网站图标)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
