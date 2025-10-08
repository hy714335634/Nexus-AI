'use client';

import styles from '../iteration.module.css';
import { useParams } from 'next/navigation';

const DIFF_TEXT = `- 你是一名企业客服质检助手\n+ 你是一名企业客服质检专家，需要输出改进建议\n- 遇到敏感词时直接报警\n+ 遇到敏感词时给出风险提示，并建议人工检查`;

const FEEDBACKS = [
  '建议加强对 SLA 超时的提醒，加入语气指引',
  '多语言场景下，请保持统一的品牌问候语',
];

export default function IterationDetailPage() {
  const params = useParams<{ id: string }>();
  const iterationId = params.id;

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🔍 迭代详情 · {iterationId}</div>
        <div style={{ color: '#666' }}>比较前后差异、查看评分与批注。</div>
      </section>

      <div className={styles.grid}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>提示词差异对比</div>
          <pre className={styles.diffBlock}>{DIFF_TEXT}</pre>
        </section>

        <aside className={styles.card}>
          <div className={styles.cardTitle}>评分与批注</div>
          <div className={styles.feedbackList}>
            {FEEDBACKS.map((item) => (
              <div key={item} className={styles.feedbackItem}>
                {item}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
