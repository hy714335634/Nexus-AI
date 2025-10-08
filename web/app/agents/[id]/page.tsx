'use client';

import Link from 'next/link';
import styles from './detail.module.css';

interface AgentVersion {
  readonly id: string;
  readonly label: string;
  readonly changelog: string;
}

const VERSIONS: AgentVersion[] = [
  {
    id: 'v1.3.2',
    label: 'v1.3.2 · 生产',
    changelog: '新增 QPS 限流策略，优化知识库召回率。',
  },
  {
    id: 'v1.3.0',
    label: 'v1.3.0 · 灰度',
    changelog: '引入 CRM 自动归档，支持 SLA 告警。',
  },
  {
    id: 'v1.2.5',
    label: 'v1.2.5 · 历史',
    changelog: '初版上线，支持基础投诉分类。',
  },
];

const METRICS = [
  { label: '调用次数', value: '3,285' },
  { label: '成功率', value: '98.7%' },
  { label: '平均响应', value: '2.4s' },
  { label: '满意度', value: '4.7 / 5' },
];

const TIMELINE = [
  { time: '09:18', content: '完成部署并发布到生产环境。' },
  { time: '09:02', content: '通过自动化回归测试（12 项用例）。' },
  { time: '08:45', content: '完成提示词微调与记忆胶囊校准。' },
  { time: '08:10', content: '生成工具编排脚本并配置限流。' },
];

const featureList = [
  '多渠道投诉解析（邮件 / 工单 / 电话记录）',
  '情感与紧急度双重分析，自动推送至专家队列',
  '知识库召回 + LLM 建议回复，保持语气一致',
  '回传 CRM 系统并生成日报 / SLA 追踪报告',
];

export default function AgentDetailPage({ params }: { readonly params: { id: string } }) {
  const agentId = params.id;
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.titleGroup}>
          <div className={styles.title}>🤖 客户投诉质检助手</div>
          <div className={styles.subtitle}>
            Agent ID：{agentId} · 负责人：张强 · 部门：企业业务
          </div>
        </div>
        <div className={styles.headerActions}>
          <Link href="/build" className={styles.button}>
            查看构建流程
          </Link>
          <Link href="/build/graph" className={styles.button}>
            工作流拓扑
          </Link>
        </div>
      </section>

      <div className={styles.layout}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>版本切换</div>
          <div className={styles.versionTabs}>
            {VERSIONS.map((version, index) => (
              <button
                key={version.id}
                type="button"
                className={index === 0 ? `${styles.versionButton} ${styles.versionButtonActive}` : styles.versionButton}
              >
                {version.label}
              </button>
            ))}
          </div>
          <div className={styles.sectionList}>
            {VERSIONS.map((version) => (
              <div key={version.id} className={styles.sectionBlock}>
                <strong>{version.label}</strong>
                <br />
                {version.changelog}
              </div>
            ))}
          </div>
        </section>

        <aside className={styles.card}>
          <div className={styles.cardTitle}>运行指标</div>
          <div className={styles.metricGrid}>
            {METRICS.map((metric) => (
              <div key={metric.label} className={styles.metricCard}>
                <div className={styles.metricValue}>{metric.value}</div>
                <div>{metric.label}</div>
              </div>
            ))}
          </div>
          <div className={styles.cardTitle}>最近动向</div>
          <div className={styles.timeline}>
            {TIMELINE.map((item) => (
              <div key={item.time} className={styles.timelineItem}>
                <div className={styles.timelineTime}>{item.time}</div>
                <div>{item.content}</div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <section className={styles.card}>
        <div className={styles.cardTitle}>核心能力</div>
        <div className={styles.sectionList}>
          {featureList.map((feature) => (
            <div key={feature} className={styles.sectionBlock}>
              {feature}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardTitle}>接入信息</div>
        <div className={styles.detailGrid}>
          <div className={styles.detailItem}>
            <div className={styles.detailLabel}>运行环境</div>
            <div className={styles.detailValue}>Agent Runtime · us-west-2</div>
          </div>
          <div className={styles.detailItem}>
            <div className={styles.detailLabel}>工具集合</div>
            <div className={styles.detailValue}>Salesforce · PagerDuty · OpenSearch</div>
          </div>
          <div className={styles.detailItem}>
            <div className={styles.detailLabel}>记忆策略</div>
            <div className={styles.detailValue}>短期：会话缓存 · 长期：向量知识库</div>
          </div>
          <div className={styles.detailItem}>
            <div className={styles.detailLabel}>发布策略</div>
            <div className={styles.detailValue}>30% 灰度 → 全量发布</div>
          </div>
        </div>
      </section>
    </div>
  );
}
