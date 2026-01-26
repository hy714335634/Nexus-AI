'use client';

import styles from './history.module.css';

const EVENTS = [
  {
    title: 'v1.3.2 发布',
    meta: '2024-03-12 · 负责人：张强',
    detail: '引入多语言模型、支持 5 个渠道的投诉处理。',
  },
  {
    title: 'v1.3.0 灰度完成',
    meta: '2024-03-05 · 灰度 30% → 全量 100%',
    detail: '新增 CRM 自动归档，并输出日报模板。',
  },
  {
    title: 'v1.2.5 上线',
    meta: '2024-02-26 · 初版交付',
    detail: '支持工单分类、自动生成处理建议。',
  },
];

const DIFFS = [
  '提示词：加入敏感词拦截、客户情绪识别。',
  '工具：新增 Salesforce API v3，支持批量写入。',
  '监控：增加 Token 使用、响应时间指标。',
];

export default function EvolutionHistoryPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🕰️ 历史版本时间轴</div>
        <div style={{ color: '#666' }}>回顾迭代历程，支持对比与回滚。</div>
      </section>

      <section className={styles.timeline}>
        {EVENTS.map((event) => (
          <div key={event.title} className={styles.timelineItem}>
            <div style={{ fontWeight: 600 }}>{event.title}</div>
            <div className={styles.itemMeta}>{event.meta}</div>
            <div>{event.detail}</div>
          </div>
        ))}
      </section>

      <section className={styles.compareCard}>
        <h3>版本差异对比</h3>
        <div className={styles.diffGrid}>
          {DIFFS.map((diff) => (
            <div key={diff} className={styles.diffItem}>
              {diff}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
