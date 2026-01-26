'use client';

import { useState } from 'react';
import styles from './pfr.module.css';
import { toast } from 'sonner';

const QUEUE = [
  {
    id: 'req-105',
    title: '销售线索分析器 · Prompt 调整',
    owner: '增长团队 · 李宁',
    status: '待评审',
  },
  {
    id: 'req-104',
    title: '客服质检助手 · 增加多语言',
    owner: '企业业务部 · 张强',
    status: '进行中',
  },
  {
    id: 'req-103',
    title: '金融风控审核员 · 风险提示优化',
    owner: '风控团队 · 王敏',
    status: '待评审',
  },
];

const CONTEXTS = {
  conversation: `User: 你好，我想投诉最近到账延迟的问题\nAgent: 您好，我来帮您处理，请提供订单号\nUser: #A1022`,
  prompt: `You are an enterprise QA assistant. Provide detailed feedback and improvement suggestion in Chinese, keep professional tone.`,
  feedback: `上轮评审中建议：强化 SLA 提醒 + 优化敏感词过滤策略。`,
};

export default function PfrPage() {
  const [activeContext, setActiveContext] = useState<'conversation' | 'prompt' | 'feedback'>('conversation');
  const [comment, setComment] = useState('');
  const [score, setScore] = useState('4');

  const submit = () => {
    toast.success('已提交评审反馈', {
      description: '反馈已同步到 PFR 流水线，将触发提示词更新。',
    });
    setComment('');
  };

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🧠 Prompt Feedback Review</div>
        <div style={{ color: '#666' }}>评审队列、上下文预览与反馈操作。</div>
      </section>

      <section className={styles.agentCard}>
        <div style={{ fontWeight: 600 }}>当前 Agent：客服质检助手</div>
        <div className={styles.agentInfo}>
          <div>
            <div>版本</div>
            <strong>v1.3.2</strong>
          </div>
          <div>
            <div>本周评审</div>
            <strong>12 次</strong>
          </div>
          <div>
            <div>满意度</div>
            <strong>4.6 / 5</strong>
          </div>
        </div>
      </section>

      <div className={styles.reviewLayout}>
        <section className={styles.queueCard}>
          <h3>评审队列</h3>
          <div className={styles.queueList}>
            {QUEUE.map((item) => (
              <div key={item.id} className={styles.queueItem}>
                <strong>{item.title}</strong>
                <span>{item.owner}</span>
                <span>状态：{item.status}</span>
              </div>
            ))}
          </div>
        </section>

        <aside className={styles.contextCard}>
          <div>
            <h3>上下文预览</h3>
            <div className={styles.contextTabs}>
              <button
                type="button"
                className={
                  activeContext === 'conversation'
                    ? `${styles.contextButton} ${styles.contextButtonActive}`
                    : styles.contextButton
                }
                onClick={() => setActiveContext('conversation')}
              >
                对话上下文
              </button>
              <button
                type="button"
                className={
                  activeContext === 'prompt'
                    ? `${styles.contextButton} ${styles.contextButtonActive}`
                    : styles.contextButton
                }
                onClick={() => setActiveContext('prompt')}
              >
                当前提示词
              </button>
              <button
                type="button"
                className={
                  activeContext === 'feedback'
                    ? `${styles.contextButton} ${styles.contextButtonActive}`
                    : styles.contextButton
                }
                onClick={() => setActiveContext('feedback')}
              >
                历史建议
              </button>
            </div>
          </div>
          <pre className={styles.contextBody}>{CONTEXTS[activeContext]}</pre>
        </aside>
      </div>

      <section className={styles.feedbackCard}>
        <div className={styles.field}>
          <span className={styles.label}>评审评分（1-5）</span>
          <select
            className={styles.select}
            value={score}
            onChange={(event) => setScore(event.target.value)}
          >
            <option value="5">5 - 优秀</option>
            <option value="4">4 - 良好</option>
            <option value="3">3 - 合格</option>
            <option value="2">2 - 待改进</option>
            <option value="1">1 - 不通过</option>
          </select>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>改进建议</span>
          <textarea
            required
            className={styles.textarea}
            placeholder="请给出针对提示词 / 工具调用 / 记忆策略的具体建议。"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </label>

        <div className={styles.actions}>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('已保存草稿')}>
            保存草稿
          </button>
          <button type="button" className={styles.primaryButton} onClick={submit}>
            提交反馈
          </button>
        </div>
      </section>
    </div>
  );
}
