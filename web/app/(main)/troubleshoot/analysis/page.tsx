'use client';

import styles from './analysis.module.css';

const LOG_SAMPLE = `09:32:10 WARN  agent.pipeline - tool.crm_write 限流，正在退避
09:32:12 INFO  agent.memory - fallback 到知识库检索
09:32:14 ERROR agent.runtime - 多语言翻译失败，触发告警`;

const METRICS = [
  { label: '最近错误率', value: '12%' },
  { label: '平均响应', value: '2.9 秒' },
  { label: '工具超时', value: '3 次 / 小时' },
];

const RECOMMENDATIONS = [
  '为 CRM 工具增加重试和缓冲队列配置。',
  '将提示词中的敏感词替换为中性表述，避免误触发。',
  '建议加入多语言场景的回退响应模板。',
];

export default function TroubleshootAnalysisPage() {
  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.title}>🧾 日志与指标</div>
        <pre className={styles.logPanel}>{LOG_SAMPLE}</pre>
        <div className={styles.metricGrid}>
          {METRICS.map((metric) => (
            <div key={metric.label} className={styles.metricCard}>
              <strong>{metric.value}</strong>
              <div>{metric.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.title}>根因建议</div>
        {RECOMMENDATIONS.map((item) => (
          <div key={item} className={styles.recommendCard}>
            {item}
          </div>
        ))}
      </section>
    </div>
  );
}
