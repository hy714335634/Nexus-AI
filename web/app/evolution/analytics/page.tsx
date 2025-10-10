'use client';

import styles from './analytics.module.css';

const TOP_FAILURES = [
  '外部 API 限流 · 发生 4 次 · 影响客服场景',
  '提示词兼容性 · 发生 3 次 · 影响销售线索',
  '知识库同步延迟 · 发生 2 次 · 影响质检助手',
];

export default function EvolutionAnalyticsPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>📊 分析面板</div>
        <div style={{ color: '#666' }}>集中查看成功率、耗时分布与风险 TopN。</div>
      </section>

      <div className={styles.grid}>
        <section className={styles.card}>
          <h3>成功率趋势</h3>
          <div className={styles.placeholder}>折线图占位 · 展示最近 7 日迭代成功率曲线。</div>
        </section>
        <section className={styles.card}>
          <h3>耗时箱线图</h3>
          <div className={styles.placeholder}>箱线图占位 · 各阶段耗时分布与异常值。</div>
        </section>
        <section className={styles.card}>
          <h3>风险 Top N</h3>
          <div className={styles.list}>
            {TOP_FAILURES.map((item) => (
              <div key={item} className={styles.listItem}>
                {item}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
