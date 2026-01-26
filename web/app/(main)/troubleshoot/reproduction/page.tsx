'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import styles from './reproduction.module.css';

const ENV_OPTIONS = ['Sandbox', 'Staging', 'Production'];

const TIMELINE = [
  '09:30 复制生产日志至沙箱环境',
  '09:32 注入多语言测试数据',
  '09:34 已重放 3 轮对话，等待人工确认',
];

export default function TroubleshootReproductionPage() {
  const [env, setEnv] = useState(ENV_OPTIONS[0]);
  const [input, setInput] = useState('');

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.title}>🔁 复现流程</div>
        <div className={styles.formGrid}>
          <label>
            环境选择
            <select className={styles.select} value={env} onChange={(event) => setEnv(event.target.value)}>
              {ENV_OPTIONS.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
          <label>
            工具开关
            <select className={styles.select}>
              <option>启用全部工具</option>
              <option>仅启用核心工具</option>
              <option>禁用外部 API</option>
            </select>
          </label>
        </div>
        <label>
          输入记录
          <textarea
            className={styles.textarea}
            placeholder="粘贴测试输入或对话脚本"
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
        </label>
        <div className={styles.actionRow}>
          <button type="button" className={styles.primaryButton} onClick={() => toast.success('已触发重放流程')}>
            开始重放
          </button>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('已记录输入与环境')}>
            保存场景
          </button>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.title}>操作时间线</div>
        <div className={styles.timeline}>
          {TIMELINE.map((item) => (
            <div key={item} className={styles.timelineItem}>
              {item}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
