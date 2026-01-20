import type { Metadata } from 'next';
import { Toaster } from 'sonner';
import { Providers } from './providers';
import { MainLayout } from '@/components/layout';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nexus AI - Agent Platform',
  description: 'More Agent, More Intelligence, More Business Impact - 从想法到 Agent 自动化构建',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <MainLayout>{children}</MainLayout>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '0.75rem',
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
