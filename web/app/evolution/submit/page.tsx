'use client';

import { useState } from 'react';
import styles from './submit.module.css';
import { toast } from 'sonner';

const OWNER_OPTIONS = ['张强', '李宁', '王敏', '刘洋'];
const TAGS = ['客服', '销售', '金融', '增长', '多语言'];

export default function EvolutionSubmitPage() {
  const [form, setForm] = useState({
    title: '',
    owner: OWNER_OPTIONS[0],
    priority: 'high',
    description: '',
  });

  const submit = () => {
    toast.success('演进需求已提交', {
      description: '已生成任务卡片，并通知协作团队。',
    });
    setForm({ title: '', owner: OWNER_OPTIONS[0], priority: 'high', description: '' });
  };

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🗂️ 提交演进需求</div>
        <div style={{ color: '#666' }}>描述你希望改进的场景、选择负责人与标签，我们会自动安排迭代。</div>
      </section>

      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label className={styles.field}>
          <span className={styles.label}>需求标题</span>
          <input
            required
            className={styles.input}
            placeholder="例如：客服质检助手 · 引入多语言模型"
            value={form.title}
            onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
          />
        </label>

        <div className={styles.inlineFields}>
          <label className={styles.field}>
            <span className={styles.label}>负责人</span>
            <select
              className={styles.select}
              value={form.owner}
              onChange={(event) => setForm((prev) => ({ ...prev, owner: event.target.value }))}
            >
              {OWNER_OPTIONS.map((owner) => (
                <option key={owner} value={owner}>
                  {owner}
                </option>
              ))}
            </select>
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
        </div>

        <label className={styles.field}>
          <span className={styles.label}>需求描述</span>
          <textarea
            required
            className={styles.textarea}
            placeholder="说明你希望改进的业务目标、痛点与预期结果。"
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
          />
        </label>

        <div className={styles.field}>
          <span className={styles.label}>标签</span>
          <div className={styles.tagList}>
            {TAGS.map((tag) => (
              <span key={tag} className={styles.tag}>
                #{tag}
              </span>
            ))}
          </div>
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('已保存草稿')}>
            保存草稿
          </button>
          <button type="submit" className={styles.primaryButton}>
            提交需求
          </button>
        </div>
      </form>
    </div>
  );
}
