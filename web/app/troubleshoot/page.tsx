'use client';

import Link from 'next/link';
import styles from './troubleshoot.module.css';
import { toast } from 'sonner';

const CATEGORIES = [
  '对话体验',
  '工具调用',
  '知识库同步',
  '部署异常',
  '监控告警',
];

const STATS = [
  { label: '今日已排查', value: '12' },
  { label: '待处理告警', value: '3' },
  { label: '平均耗时', value: '18 分钟' },
  { label: '自动修复率', value: '72%' },
];

const QUICK_LINKS = [
  { label: '对话分析', href: '/troubleshoot/analysis' },
  { label: '复现流程', href: '/troubleshoot/reproduction' },
  { label: '代码诊断', href: '/troubleshoot/code-review' },
  { label: '修复执行', href: '/troubleshoot/fix' },
  { label: '后续跟踪', href: '/troubleshoot/tracking' },
];

export default function TroubleshootHomePage() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🔍 智能故障诊断入口</div>
        <div style={{ color: '#666' }}>描述问题、选择类别，系统将自动指引排查流程。</div>
      </section>

      <section className={styles.hero}>
        <div className={styles.heroTitle}>让 AI 帮你排查故障</div>
        <div className={styles.heroSubtitle}>一次输入，自动联动日志、指标、代码与修复流程。</div>
      </section>

      <section className={styles.inputSection}>
        <textarea className={styles.textarea} placeholder="描述你的问题，例如：客服质检助手在多语言场景下出现重复回答，且 SLA 告警持续触发。" />
        <div className={styles.categoryGrid}>
          {CATEGORIES.map((category) => (
            <div key={category} className={styles.categoryCard}>
              <strong>{category}</strong>
              <span>点击扩展查看建议流程</span>
            </div>
          ))}
        </div>
        <div className={styles.actionRow}>
          <button type="button" className={styles.primaryButton} onClick={() => toast.success('已生成排查计划')}>
            生成排查计划
          </button>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('已记录到运维日志')}>
            记录问题
          </button>
        </div>
      </section>

      <div className={styles.statsGrid}>
        {STATS.map((stat) => (
          <div key={stat.label} className={styles.statCard}>
            <div className={styles.statValue}>{stat.value}</div>
            <div>{stat.label}</div>
          </div>
        ))}
      </div>

      <section className={styles.inputSection}>
        <h3>快速导航</h3>
        <div className={styles.quickLinks}>
          {QUICK_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className={styles.quickLink}>
              <span>{link.label}</span>
              <span>→</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
