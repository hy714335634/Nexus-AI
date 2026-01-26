'use client';

import styles from './codeReview.module.css';

const DIFF_SNIPPET = `- if response.language == 'en':
-     return generate_english_reply(context)
+ if response.language in ['en', 'fr', 'de']:
+     return generate_multilingual_reply(context)
+ log_usage("multi-language")`;

const ALERTS = [
  '检测到未处理的异常分支：工具返回 429 未回退。',
  '建议添加多语言场景下的 SLA 告警。',
];

export default function TroubleshootCodeReviewPage() {
  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.title}>🧮 代码差异 & 风险提示</div>
        <pre className={styles.diffBlock}>{DIFF_SNIPPET}</pre>
      </section>

      <section className={styles.card}>
        <div className={styles.title}>风险提示</div>
        <div className={styles.alertList}>
          {ALERTS.map((alert) => (
            <div key={alert} className={styles.alertItem}>
              {alert}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
