'use client';

import styles from './progress.module.css';

const PROGRESS = [
  { label: '整体进度', value: '68%' },
  { label: '里程碑完成', value: '5 / 8' },
  { label: '燃尽剩余', value: '12 天' },
  { label: '依赖风险', value: '低' },
];

const MILESTONES = [
  { title: '完成需求细化', meta: '负责人：张强 · 08:18 完成' },
  { title: '架构评审通过', meta: '负责人：Architect Agent · 计划 08:45' },
  { title: '提示词评估', meta: '负责人：Prompt Agent · 进行中' },
  { title: '自动化回归', meta: '负责人：QA Agent · 待开始' },
];

export default function EvolutionProgressPage() {
  return (
    <div className={styles.page}>
      <section className={styles.summary}>
        <div className={styles.title}>📊 进度追踪</div>
        <div style={{ color: '#666', marginTop: 6 }}>查看里程碑、燃尽图与依赖状态。</div>
        <div className={styles.progressGrid}>
          {PROGRESS.map((item) => (
            <div key={item.label} className={styles.progressCard}>
              <div className={styles.progressValue}>{item.value}</div>
              <div>{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.chartCard}>
        <h3>燃尽图</h3>
        <div className={styles.chartPlaceholder}>即将接入实际燃尽图数据，展示每日剩余工作量趋势。</div>
      </section>

      <section className={styles.chartCard}>
        <h3>依赖关系</h3>
        <div className={styles.chartPlaceholder}>依赖拓扑图占位：展示工具、数据源、审批环节之间的关系。</div>
      </section>

      <section className={styles.timeline}>
        <h3>里程碑时间线</h3>
        {MILESTONES.map((milestone) => (
          <div key={milestone.title} className={styles.milestone}>
            <div>{milestone.title}</div>
            <div className={styles.milestoneMeta}>{milestone.meta}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
