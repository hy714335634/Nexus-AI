'use client';

import styles from './ops.module.css';
import Link from 'next/link';
import { toast } from 'sonner';

const METRICS = [
  { label: '在运行 Agent', value: '42' },
  { label: '今日部署', value: '6' },
  { label: '告警 (24h)', value: '3' },
  { label: 'SLA ≥ 99%', value: '38' },
];

const ALERTS = [
  '09:32 Salesforce 工具限流，自动退避中…',
  '09:05 提示词版本 1.3.2 请求超时，已重试',
  '08:47 Agent Runtime 节点 us-west-2 负载 78%',
];

const SLA_ITEMS = [
  '客服质检助手 · SLA 99.2%',
  '销售线索分析器 · SLA 98.7%，建议关注',
  '金融风控审核员 · SLA 99.8%',
];

export default function OpsDashboardPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🚀 AgentOps 运维总览</div>
        <div style={{ color: '#666' }}>查看运行状况、告警信息与部署节奏。</div>
        <div>
          <Link href="/tools/build" style={{ color: 'var(--accent, #667eea)', marginRight: 12 }}>
            查看工具构建流水线 →
          </Link>
          <button
            type="button"
            onClick={() => toast('已生成运维日报')}
            style={{ border: 'none', background: 'rgba(102, 126, 234, 0.12)', padding: '8px 16px', borderRadius: 12 }}
          >
            导出日报
          </button>
        </div>
      </section>

      <div className={styles.metrics}>
        {METRICS.map((metric) => (
          <div key={metric.label} className={styles.metricCard}>
            <div className={styles.metricValue}>{metric.value}</div>
            <div>{metric.label}</div>
          </div>
        ))}
      </div>

      <div className={styles.layout}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>部署节奏 / 流水</div>
          <div className={styles.chartPlaceholder}>折线图占位：展示过去 7 日部署次数与失败率。</div>
        </section>

        <aside className={styles.card}>
          <div className={styles.cardTitle}>告警列表</div>
          <div className={styles.alertList}>
            {ALERTS.map((alert) => (
              <div key={alert} className={styles.alertItem}>
                {alert}
              </div>
            ))}
          </div>
        </aside>
      </div>

      <div className={styles.layout}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>运行状况 (占位)</div>
          <div className={styles.chartPlaceholder}>拓扑占位：运行节点、工具、外部服务之间的调用关系。</div>
        </section>

        <aside className={styles.card}>
          <div className={styles.cardTitle}>SLA 快照</div>
          <div className={styles.slaList}>
            {SLA_ITEMS.map((item) => (
              <div key={item} className={styles.slaItem}>
                {item}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
