'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useMemo } from 'react';
import styles from './app-shell.module.css';

interface AppShellProps {
  readonly children: ReactNode;
}

interface NavItem {
  readonly label: string;
  readonly href: string;
  readonly icon: string;
  readonly badge?: string;
  readonly status?: 'online' | 'building' | 'offline';
}

interface NavSection {
  readonly title: string;
  readonly items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: '核心模块',
    items: [
      { label: '首页概览', href: '/', icon: '🏠', status: 'online' },
      { label: '构建进度', href: '/build', icon: '🔨', badge: '3', status: 'building' },
      { label: '构建模块', href: '/build/modules', icon: '🧩', status: 'online' },
      { label: '管理模块', href: '/management', icon: '⚙️', status: 'online' },
      { label: '迭代模块', href: '/iteration', icon: '🔄', badge: '1', status: 'online' },
      { label: '问题排查', href: '/troubleshoot', icon: '🐛', status: 'online' },
      { label: '日志分析', href: '/troubleshoot/analysis', icon: '📄', status: 'online' },
      { label: '复现流程', href: '/troubleshoot/reproduction', icon: '🔁', status: 'online' },
      { label: '代码诊断', href: '/troubleshoot/code-review', icon: '🧮', status: 'online' },
      { label: '运维管理', href: '/operations', icon: '🔧', status: 'online' },
      { label: '监控中心', href: '/monitoring', icon: '📊', badge: '2', status: 'online' },
      { label: '工具&MCP', href: '/tools', icon: '🛠️', status: 'online' },
    ],
  },
  {
    title: '系统功能',
    items: [
      { label: 'Agent库', href: '/agent-library', icon: '🤖', status: 'online' },
      { label: '构建配置', href: '/agents/dialog', icon: '📝', status: 'online' },
      { label: '多Agent编排', href: '/multi-agent', icon: '🔗', status: 'online' },
      { label: '自举式进化', href: '/evolution', icon: '🔄', badge: 'Beta', status: 'building' },
      { label: '系统分析', href: '/analytics', icon: '📈', status: 'online' },
    ],
  },
  {
    title: '用户管理',
    items: [
      { label: '个人中心', href: '/profile', icon: '👤', status: 'online' },
      { label: '团队管理', href: '/team', icon: '👥', status: 'online' },
      { label: '帮助文档', href: '/help', icon: '📚', status: 'online' },
      { label: '系统设置', href: '/settings', icon: '⚙️', status: 'online' },
    ],
  },
];

function getStatusClass(status?: NavItem['status']) {
  switch (status) {
    case 'online':
      return styles.statusOnline;
    case 'building':
      return styles.statusBuilding;
    case 'offline':
      return styles.statusOffline;
    default:
      return undefined;
  }
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  const allItems = useMemo(() => NAV_SECTIONS.flatMap((section) => section.items), []);

  const activeItem = useMemo(() => {
    return allItems.find((item) => (item.href === '/' ? pathname === '/' : pathname.startsWith(item.href)));
  }, [allItems, pathname]);

  return (
    <div className={styles.appContainer}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>🤖 Nexus-AI</div>
        </div>

        <div className={styles.navModules}>
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className={styles.navSection}>
              <div className={styles.navSectionTitle}>{section.title}</div>
              <div className={styles.navList}>
                {section.items.map((item) => {
                  const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                  const className = isActive
                    ? `${styles.navItem} ${styles.navItemActive}`
                    : styles.navItem;

                  return (
                    <Link key={item.label} href={item.href} className={className}>
                      <span className={styles.navIcon} aria-hidden="true">
                        {item.icon}
                      </span>
                      <span className={styles.navText}>{item.label}</span>
                      {item.badge ? <span className={styles.navBadge}>{item.badge}</span> : null}
                      {item.status ? <span className={`${styles.navStatus} ${getStatusClass(item.status)}`} /> : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </aside>

      <div className={styles.mainContent}>
        <header className={styles.header}>
          <div className={styles.pageTitle}>{activeItem?.label ?? '首页概览'}</div>
          <div className={styles.userInfo}>
            <span>张强 [企业业务部门]</span>
            <div className={styles.userAvatar}>张</div>
          </div>
        </header>
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
