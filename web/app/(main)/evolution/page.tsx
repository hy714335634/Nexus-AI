'use client';

import Link from 'next/link';
import styles from './evolution.module.css';
import { toast } from 'sonner';

const METRICS = [
  { label: '进行中项目', value: '6' },
  { label: '即将到期', value: '2 个迭代' },
  { label: '本周交付', value: '4 项' },
  { label: '风险事件', value: '3 条告警' },
];

const LANES = [
  {
    title: '规划中',
    badge: '2',
    tickets: [
      '客服机器人 · 支持多语言场景',
      '营销助理 · 引入意图识别',
    ],
  },
  {
    title: '执行中',
    badge: '3',
    tickets: [
      '销售线索分析 · 工具限流优化',
      '金融风控审核 · 提示词重训',
      '质检助手 · 案例回归测试',
    ],
  },
  {
    title: '验证中',
    badge: '1',
    tickets: [
      '多渠道客服 · 沙箱回归 + 灰度',
    ],
  },
  {
    title: '已上线',
    badge: '4',
    tickets: [
      '知识库检索助手 · 版本 v1.3',
      '智能报表生成 · 版本 v2.0',
      '产品 FAQ bot · 版本 v1.1',
      '售后质检 · 版本 v1.0',
    ],
  },
];

const ACTIVITIES = [
  { time: '09:32', desc: '“客服质检助手” 完成灰度，切换 30% 流量。' },
  { time: '09:08', desc: '“销售线索分析器” 提示词重训完成，准确率 +8%。' },
  { time: '08:45', desc: '新增风险：工单系统 QPS 限流触发，已自动开启缓冲。' },
  { time: '昨晚', desc: '“金融风控审核员” 发布 v1.3，并同步发布总结。' },
];

export default function EvolutionOverviewPage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <div className={styles.title}>🌊 项目演进总览</div>
            <div style={{ color: '#666' }}>掌握当前迭代进度、关键风险与最新动态。</div>
          </div>
          <div className={styles.actions}>
            <Link href="/evolution/submit" className={styles.primaryButton}>
              提交演进需求
            </Link>
            <button type="button" className={styles.secondaryButton} onClick={() => toast('已生成日报') }>
              导出演进日报
            </button>
          </div>
        </div>

        <div className={styles.metrics}>
          {METRICS.map((metric) => (
            <div key={metric.label} className={styles.metricCard}>
              <div className={styles.metricValue}>{metric.value}</div>
              <div>{metric.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.board}>
        <h3>泳道视图</h3>
        <div className={styles.laneGrid}>
          {LANES.map((lane) => (
            <div key={lane.title} className={styles.lane}>
              <div className={styles.laneHeader}>
                <div className={styles.laneTitle}>{lane.title}</div>
                <span style={{ fontSize: '0.8rem', color: '#888' }}>{lane.badge}</span>
              </div>
              {lane.tickets.map((ticket) => (
                <div key={ticket} className={styles.ticket}>
                  {ticket}
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.activityPanel}>
        <h3>右侧事件流</h3>
        {ACTIVITIES.map((activity) => (
          <div key={activity.desc} className={styles.activityItem}>
            <div className={styles.activityTime}>{activity.time}</div>
            <div>{activity.desc}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
