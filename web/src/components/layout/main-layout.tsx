'use client';

import { useState } from 'react';
import { Sidebar, SidebarContext } from './sidebar';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <SidebarContext.Provider value={{ collapsed, setCollapsed }}>
      <div className="min-h-screen bg-gray-50">
        <Sidebar collapsed={collapsed} onCollapsedChange={setCollapsed} />
        <main className={cn(
          'transition-all duration-300',
          collapsed ? 'pl-20' : 'pl-64'
        )}>
          {children}
        </main>
      </div>
    </SidebarContext.Provider>
  );
}
