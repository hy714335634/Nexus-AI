'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Bot,
  FolderKanban,
  Wrench,
  BarChart3,
  Settings,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  FileText,
  MessageSquare,
} from 'lucide-react';
import { useState, createContext, useContext } from 'react';

// 创建侧边栏状态上下文
interface SidebarContextType {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const SidebarContext = createContext<SidebarContextType>({
  collapsed: false,
  setCollapsed: () => {},
});

export const useSidebar = () => useContext(SidebarContext);

const navigation = [
  { name: '工作台', href: '/', icon: LayoutDashboard },
  { name: 'Agent', href: '/agents', icon: Bot },
  { name: '会话', href: '/chat', icon: MessageSquare },
  { name: '构建项目', href: '/projects', icon: FolderKanban },
  { name: '能力工具', href: '/tools', icon: Wrench },
  { name: '业务洞察', href: '/analytics', icon: BarChart3 },
  { name: '系统配置', href: '/settings/config', icon: FileText },
];

interface SidebarProps {
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function Sidebar({ collapsed: controlledCollapsed, onCollapsedChange }: SidebarProps = {}) {
  const pathname = usePathname();
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  
  // 支持受控和非受控模式
  const collapsed = controlledCollapsed ?? internalCollapsed;
  const setCollapsed = onCollapsedChange ?? setInternalCollapsed;

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen bg-white border-r border-gray-200 transition-all duration-300',
        collapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center bg-gradient-to-br from-primary-500 to-accent-600 relative">
            <Image
              src="/logo.png"
              alt="Nexus AI"
              width={40}
              height={40}
              className="object-contain"
              priority
            />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-lg font-bold bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                Nexus AI
              </span>
              <span className="text-[10px] text-gray-400 -mt-0.5">Agent Platform</span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          title={collapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-1">
        {navigation.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                active
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                collapsed && 'justify-center px-2'
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon className={cn('w-5 h-5 flex-shrink-0', active && 'text-primary-600')} />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      {!collapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="bg-gradient-to-br from-primary-50 via-accent-50 to-agent-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Bot className="w-5 h-5 text-primary-600" />
              <span className="text-sm font-medium text-gray-900">创建 Agent</span>
            </div>
            <p className="text-xs text-gray-600 mb-3">用自然语言描述业务需求，快速构建专属 Agent</p>
            <Link
              href="/agents/new"
              className="block w-full py-2 px-3 text-center text-sm font-medium text-white bg-gradient-to-r from-primary-600 to-accent-600 rounded-lg hover:from-primary-700 hover:to-accent-700 transition-all shadow-sm"
            >
              开始创建
            </Link>
          </div>
        </div>
      )}
    </aside>
  );
}
