'use client';

import { useState } from 'react';
import styles from './dialog.module.css';
import { toast } from 'sonner';

const TEMPLATES = ['客户服务', '知识库问答', '销售线索', '多语言客服'];

export default function AgentDialogPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({
    name: '客户投诉质检助手',
    description: '自动分析客诉内容，给出处理建议并同步 CRM，支持 SLA 告警。',
    priority: 'high',
    owner: '张强 · 企业业务部门',
  });

  const submit = () => {
    setModalOpen(false);
    toast.success('构建任务已提交', {
      description: `${form.name} 将由 Orchestrator 自动生成流程配置。`,
    });
  };

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>📝 构建配置确认</div>
        <div className={styles.actions}>
          <button type="button" className={styles.secondaryButton} onClick={() => setModalOpen(true)}>
            风险提示
          </button>
          <button type="button" className={styles.primaryButton} onClick={submit}>
            提交构建
          </button>
        </div>
      </section>

      <div className={styles.formLayout}>
        <section className={styles.card}>
          <h3 className={styles.cardTitle}>基础信息</h3>
          <label className={styles.field}>
            <span className={styles.label}>Agent 名称</span>
            <input
              className={styles.input}
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>需求描述</span>
            <textarea
              className={styles.textarea}
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>优先级</span>
            <select
              className={styles.select}
              value={form.priority}
              onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value }))}
            >
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </label>

          <div className={styles.field}>
            <span className={styles.label}>模板推荐</span>
            <div className={styles.tagList}>
              {TEMPLATES.map((template) => (
                <span key={template} className={styles.tag}>
                  {template}
                </span>
              ))}
            </div>
          </div>
        </section>

        <aside className={styles.card}>
          <h3 className={styles.cardTitle}>交付概要</h3>
          <div className={styles.summaryGrid}>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>负责人</span>
              <span className={styles.summaryValue}>{form.owner}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>交付时效</span>
              <span className={styles.summaryValue}>45 分钟（预计）</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>核心风险</span>
              <span className={styles.summaryValue}>外部工单限流、PII 数据合规</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>所需工具</span>
              <span className={styles.summaryValue}>CRM API · PagerDuty · 向量检索</span>
            </div>
          </div>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => toast('已导出构建概览报告')}
          >
            导出报告
          </button>
        </aside>
      </div>

      {modalOpen ? (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>⚠️ 风险提示</div>
              <button type="button" className={styles.modalClose} onClick={() => setModalOpen(false)}>
                ×
              </button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.warningBox}>
                • 外部工单系统存在 QPS 限制，建议启用缓冲队列。<br />
                • 对话日志中包含 PII 数据，请确认脱敏策略。<br />
                • 部署前建议在 Sandbox 执行 5 轮回归测试。
              </div>
              <div>
                当前配置将触发以下步骤：<br />
                1. 自动生成架构蓝图与工具编排<br />
                2. 生成提示词、Agent 代码与测试集<br />
                3. 推送至 Agent Runtime 并开启灰度
              </div>
            </div>
            <div className={styles.modalFooter}>
              <button type="button" className={styles.secondaryButton} onClick={() => setModalOpen(false)}>
                返回调整
              </button>
              <button type="button" className={styles.primaryButton} onClick={submit}>
                确认构建
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
