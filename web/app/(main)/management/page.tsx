'use client';

import { useMemo, useState } from 'react';
import styles from './management.module.css';
import Link from 'next/link';
import { toast } from 'sonner';

type Status = 'running' | 'building' | 'paused';

interface AgentRow {
  readonly id: string;
  readonly name: string;
  readonly owner: string;
  readonly status: Status;
  readonly category: string;
  readonly updatedAt: string;
}

const AGENTS: AgentRow[] = [
  {
    id: 'agent-support-01',
    name: '客服质检助手',
    owner: '企业业务部 · 张强',
    status: 'running',
    category: '客服',
    updatedAt: '09:18',
  },
  {
    id: 'agent-sales-02',
    name: '销售线索分析器',
    owner: '增长团队 · 李宁',
    status: 'building',
    category: '销售',
    updatedAt: '09:05',
  },
  {
    id: 'agent-risk-03',
    name: '金融风控审核员',
    owner: '风控团队 · 王敏',
    status: 'running',
    category: '金融',
    updatedAt: '08:42',
  },
  {
    id: 'agent-qa-04',
    name: '产品质量巡检官',
    owner: '研发 QA · 刘洋',
    status: 'paused',
    category: '质量',
    updatedAt: '昨日',
  },
];

const STATUS_LABEL: Record<Status, string> = {
  running: '运行中',
  building: '构建中',
  paused: '已暂停',
};

function getStatusClass(status: Status) {
  if (status === 'running') return `${styles.statusTag} ${styles.statusRunning}`;
  if (status === 'building') return `${styles.statusTag} ${styles.statusBuilding}`;
  return `${styles.statusTag} ${styles.statusPaused}`;
}

export default function ManagementPage() {
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | Status>('all');

  const stats = useMemo(
    () => [
      { label: '总计 Agent', value: AGENTS.length.toString() },
      { label: '运行中', value: AGENTS.filter((agent) => agent.status === 'running').length.toString() },
      { label: '构建中', value: AGENTS.filter((agent) => agent.status === 'building').length.toString() },
      { label: '待关注', value: '3 个风险告警' },
    ],
    [],
  );

  const filteredAgents = useMemo(() => {
    return AGENTS.filter((agent) => {
      const keywordMatch = keyword.trim()
        ? agent.name.includes(keyword.trim()) || agent.owner.includes(keyword.trim())
        : true;
      const statusMatch = statusFilter === 'all' ? true : agent.status === statusFilter;
      return keywordMatch && statusMatch;
    });
  }, [keyword, statusFilter]);

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.headerTop}>
          <div className={styles.titleGroup}>
            <div className={styles.title}>📈 Agent 管理中心</div>
            <div className={styles.subtitle}>统一查看、筛选、批量处理全部智能体。</div>
          </div>
          <div className={styles.actions}>
            <Link href="/agents/new" className={styles.primaryButton}>
              新建 Agent
            </Link>
            <Link href="/evolution/submit" className={styles.secondaryButton}>
              提交迭代需求
            </Link>
          </div>
        </div>

        <div className={styles.filters}>
          <div className={styles.filterRow}>
            <input
              className={styles.input}
              placeholder="搜索 Agent / 负责人 / 部门"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <select
              className={styles.select}
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}
            >
              <option value="all">全部状态</option>
              <option value="running">运行中</option>
              <option value="building">构建中</option>
              <option value="paused">已暂停</option>
            </select>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => toast('即将上线批量操作')}
            >
              批量操作
            </button>
          </div>

          <div className={styles.statsGrid}>
            {stats.map((stat) => (
              <div key={stat.label} className={styles.statCard}>
                <div className={styles.statValue}>{stat.value}</div>
                <div className={styles.statLabel}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <h3>Agent 列表 ({filteredAgents.length})</h3>
          <div className={styles.tableActions}>
            <button type="button" className={styles.secondaryButton} onClick={() => toast('已导出 CSV')}>
              导出列表
            </button>
            <button type="button" className={styles.secondaryButton} onClick={() => toast('已应用智能排序')}>
              智能排序
            </button>
          </div>
        </div>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Agent 名称</th>
              <th>负责人</th>
              <th>分类</th>
              <th>状态</th>
              <th>最近更新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredAgents.map((agent) => (
              <tr key={agent.id}>
                <td>{agent.name}</td>
                <td>{agent.owner}</td>
                <td>{agent.category}</td>
                <td>
                  <span className={getStatusClass(agent.status)}>{STATUS_LABEL[agent.status]}</span>
                </td>
                <td>{agent.updatedAt}</td>
                <td>
                  <Link href={`/agents/${agent.id}`} style={{ color: 'var(--accent, #667eea)' }}>
                    查看详情
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <h3>快速入口</h3>
        </div>
        <div className={styles.quickLinks}>
          <Link href="/evolution" className={styles.quickLink}>
            <span>项目演进总览 · 查看甘特泳道与节点状态</span>
            <span>→</span>
          </Link>
          <Link href="/evolution/analytics" className={styles.quickLink}>
            <span>分析面板 · 成功率 / 耗时箱线图 / 风险 TopN</span>
            <span>→</span>
          </Link>
          <Link href="/evolution/history" className={styles.quickLink}>
            <span>历史版本 · 对比回滚 & 枢纽事件</span>
            <span>→</span>
          </Link>
        </div>
      </section>
    </div>
  );
}
