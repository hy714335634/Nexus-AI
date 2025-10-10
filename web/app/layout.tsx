import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { AppShell } from '@components/app-shell';

export const metadata: Metadata = {
  title: 'Nexus-AI 控制台',
  description: '让 AI 帮你构建 AI，统一管理与运维智能体。',
};

interface RootLayoutProps {
  readonly children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
