'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useMemo } from 'react';
import styles from './app-shell.module.css';
import { useProjectSummaries } from '@/hooks/use-projects';

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

function getNavSections(buildingCount?: number, hasBuilding?: boolean): NavSection[] {
  return [
    {
      title: '核心模块',
      items: [
        { label: '首页概览', href: '/', icon: '🏠' },
        { label: '新建构建', href: '/agents/new', icon: '➕' },
        {
          label: '构建模块',
          href: '/build/modules',
          icon: '🔨',
          badge: buildingCount && buildingCount > 0 ? String(buildingCount) : undefined,
          status: hasBuilding ? 'building' : undefined,
        },
        { label: '与Agent聊天', href: '/agents/dialog', icon: '💬' },
        // { label: '管理模块', href: '/management', icon: '⚙️' },
        // { label: '迭代模块', href: '/iteration', icon: '🔄' },
        // { label: '问题排查', href: '/troubleshoot', icon: '🐛' },
        // { label: '日志分析', href: '/troubleshoot/analysis', icon: '📄' },
        // { label: '复现流程', href: '/troubleshoot/reproduction', icon: '🔁' },
        // { label: '代码诊断', href: '/troubleshoot/code-review', icon: '🧮' },
        // { label: '运维管理', href: '/operations', icon: '🔧' },
        // { label: '监控中心', href: '/monitoring', icon: '📊' },
        // { label: '工具&MCP', href: '/tools', icon: '🛠️' },
      ],
    },
    // {
    //   title: '系统功能',
    //   items: [
    //     { label: 'Agent库', href: '/agent-library', icon: '🤖' },
    //     { label: '构建配置', href: '/agents/config', icon: '📝' },
    //     { label: '多Agent编排', href: '/multi-agent', icon: '🔗' },
    //     { label: '自举式进化', href: '/evolution', icon: '🔄', badge: 'Beta' },
    //     { label: '系统分析', href: '/analytics', icon: '📈' },
    //   ],
    // },
    // {
    //   title: '用户管理',
    //   items: [
    //     { label: '个人中心', href: '/profile', icon: '👤' },
    //     { label: '团队管理', href: '/team', icon: '👥' },
    //     { label: '帮助文档', href: '/help', icon: '📚' },
    //     { label: '系统设置', href: '/settings', icon: '⚙️' },
    //   ],
    // },
  ];
}

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
  const { data: projectSummaries } = useProjectSummaries();

  const buildingCount = useMemo(() => {
    if (!projectSummaries) return 0;
    return projectSummaries.filter((p) => p.status === 'building').length;
  }, [projectSummaries]);

  const hasBuilding = buildingCount > 0;

  const NAV_SECTIONS = useMemo(
    () => getNavSections(buildingCount, hasBuilding),
    [buildingCount, hasBuilding],
  );

  const allItems = useMemo(() => NAV_SECTIONS.flatMap((section) => section.items), [NAV_SECTIONS]);

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
                    <Link key={item.label} href={item.href as any} className={className}>
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
