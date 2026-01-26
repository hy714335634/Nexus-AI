'use client';

import Link from 'next/link';
import styles from './agents.module.css';

const AGENT_ROWS = [
  {
    name: '客服质检助手',
    version: 'v1.3.2',
    status: '运行中',
    owner: '张强',
    evolution: '迭代 #104 – 多语言支持',
  },
  {
    name: '销售线索分析器',
    version: 'v1.2.0',
    status: '构建中',
    owner: '李宁',
    evolution: '迭代 #102 – 提示词重训',
  },
  {
    name: '金融风控审核员',
    version: 'v1.1.4',
    status: '运行中',
    owner: '王敏',
    evolution: '迭代 #099 – API 批量同步',
  },
];

const TIMELINE = [
  '09:20 客服质检助手 完成多语言灰度上线。',
  '09:02 销售线索分析器 触发风险提醒：工具限流。',
  '昨日 金融风控审核员 发布 v1.1.4 并生成总结报告。',
];

export default function EvolutionAgentsPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🤖 演进关联 Agent</div>
        <div style={{ color: '#666' }}>查看各 Agent 在当前演进周期中的状态与版本脉络。</div>
      </section>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Agent 名称</th>
            <th>版本</th>
            <th>状态</th>
            <th>负责人</th>
            <th>所属迭代</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {AGENT_ROWS.map((row) => (
            <tr key={row.name}>
              <td>{row.name}</td>
              <td>{row.version}</td>
              <td>
                <span className={styles.badge}>{row.status}</span>
              </td>
              <td>{row.owner}</td>
              <td>{row.evolution}</td>
              <td>
                <Link href={`/agents/${encodeURIComponent(row.name)}`} style={{ color: 'var(--accent, #667eea)' }}>
                  查看详情
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className={styles.timeline}>
        <h3>最近事件</h3>
        {TIMELINE.map((item) => (
          <div key={item} className={styles.timelineItem}>
            {item}
          </div>
        ))}
      </section>
    </div>
  );
}
