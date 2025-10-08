'use client';

import Link from 'next/link';
import styles from './detail.module.css';
import { useParams } from 'next/navigation';

const EXEC_HISTORY = [
  { time: '09:32', result: '成功', agent: '客服质检助手', latency: '510 ms' },
  { time: '09:08', result: '限流', agent: '销售线索分析器', latency: '—' },
  { time: '08:45', result: '成功', agent: '金融风控审核员', latency: '620 ms' },
];

const WARNINGS = [
  '09:08 工具触发限流，已自动退避重试。',
  '昨日 使用量超出阈值 10%，建议扩容。',
];

export default function ToolDetailPage() {
  const params = useParams<{ id: string }>();
  const toolName = decodeURIComponent(params.id ?? '工具详情');

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🧪 工具详情 · {toolName}</div>
        <div style={{ color: '#666' }}>查看执行历史、告警与关联 Agent。</div>
      </section>

      <div className={styles.grid}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>执行历史</div>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>时间</th>
                <th>结果</th>
                <th>调用 Agent</th>
                <th>耗时</th>
              </tr>
            </thead>
            <tbody>
              {EXEC_HISTORY.map((row) => (
                <tr key={`${row.agent}-${row.time}`}>
                  <td>{row.time}</td>
                  <td>
                    <span className={styles.badge}>{row.result}</span>
                  </td>
                  <td>
                    <Link href={`/agents/${encodeURIComponent(row.agent)}`}>{row.agent}</Link>
                  </td>
                  <td>{row.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <aside className={styles.card}>
          <div className={styles.cardTitle}>告警 & 备注</div>
          <div className={styles.timeline}>
            {WARNINGS.map((warning) => (
              <div key={warning} className={styles.timelineItem}>
                {warning}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
