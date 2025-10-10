'use client';

import Link from 'next/link';
import styles from './tools.module.css';
import { toast } from 'sonner';

const STATS = [
  { label: '内置工具', value: '18' },
  { label: '启用率', value: '86%' },
  { label: 'MCP 连接', value: '5 条' },
  { label: '昨日告警', value: '2 条' },
];

const TOOL_ROWS = [
  { name: '知识库检索器', owner: '平台团队', status: '启用', calls: '1.8K', latency: '530ms' },
  { name: 'CRM 工单写入', owner: '企业业务', status: '启用', calls: '970', latency: '420ms' },
  { name: '向量索引刷新', owner: '数据平台', status: '暂停', calls: '120', latency: '—' },
];

const MCP_ROWS = [
  { name: 'OpenAI Tools', status: '连接正常', updated: '09:30', remark: '提供代码解释 / shell' },
  { name: 'Salesforce MCP', status: '限流告警', updated: '08:45', remark: 'CRM 接入，存在 QPS 限制' },
  { name: 'PagerDuty MCP', status: '连接正常', updated: '昨日', remark: '告警通知组件' },
];

export default function ToolsOverviewPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.headerTop}>
          <div className={styles.titleGroup}>
            <div className={styles.title}>🧩 工具 & MCP 管理</div>
            <div className={styles.subtitle}>查看内置工具、集成状态与启用指标。</div>
          </div>
          <div className={styles.actions}>
            <Link href="/tools/create" className={styles.primaryButton}>
              新建工具
            </Link>
            <Link href="/tools/mcp/create" className={styles.secondaryButton}>
              创建 MCP 连接
            </Link>
          </div>
        </div>

        <div className={styles.statsGrid}>
          {STATS.map((stat) => (
            <div key={stat.label} className={styles.statCard}>
              <div className={styles.statValue}>{stat.value}</div>
              <div>{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.toolSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>内置工具</h3>
          <div>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => toast('已执行健康检查')}
            >
              健康检查
            </button>
          </div>
        </div>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>工具名称</th>
              <th>负责人</th>
              <th>状态</th>
              <th>调用量</th>
              <th>平均延迟</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {TOOL_ROWS.map((tool) => (
              <tr key={tool.name}>
                <td>{tool.name}</td>
                <td>{tool.owner}</td>
                <td>
                  <span className={styles.badge}>{tool.status}</span>
                </td>
                <td>{tool.calls}</td>
                <td>{tool.latency}</td>
                <td>
                  <Link href={`/tools/${encodeURIComponent(tool.name)}/detail`} style={{ color: 'var(--accent, #667eea)' }}>
                    查看
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.mcpSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>MCP 集成</h3>
          <Link href="/tools/mcp/create" className={styles.secondaryButton}>
            新增连接
          </Link>
        </div>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>名称</th>
              <th>状态</th>
              <th>最近同步</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            {MCP_ROWS.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>
                  <span className={styles.badge}>{row.status}</span>
                </td>
                <td>{row.updated}</td>
                <td>{row.remark}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.toolSection}>
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>快捷入口</h3>
        </div>
        <div className={styles.quickGrid}>
          <div className={styles.quickCard}>
            <div>生成工具构建流水线</div>
            <Link href="/tools/build" className={styles.quickLink}>
              查看构建进度 →
            </Link>
          </div>
          <div className={styles.quickCard}>
            <div>查看工具执行日志</div>
            <Link href="/tools/sample-tool/logs" className={styles.quickLink}>
              跳转日志流 →
            </Link>
          </div>
          <div className={styles.quickCard}>
            <div>配置回调与超时策略</div>
            <Link href="/tools/sample-tool/config" className={styles.quickLink}>
              打开配置 →
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
