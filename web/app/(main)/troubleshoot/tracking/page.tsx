'use client';

import styles from './tracking.module.css';

const METRICS = [
  { label: '告警清零', value: '3/3' },
  { label: '业务指标回归', value: '95%' },
  { label: '待跟踪任务', value: '1' },
];

const EVENTS = [
  '10:15 告警清零完成，SLA 恢复至 99.2%',
  '09:55 多语言场景满意度回升至 4.6/5',
  '09:40 提示词补丁回放通过，监控指标正常',
];

export default function TroubleshootTrackingPage() {
  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.title}>📈 跟踪与验证</div>
        <div className={styles.metrics}>
          {METRICS.map((metric) => (
            <div key={metric.label} className={styles.metricCard}>
              <strong>{metric.value}</strong>
              <div>{metric.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.title}>事件记录</div>
        <div className={styles.timeline}>
          {EVENTS.map((event) => (
            <div key={event} className={styles.timelineItem}>
              {event}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
