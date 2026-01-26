'use client';

import styles from './config.module.css';
import { useMemo } from 'react';
import { useParams } from 'next/navigation';

const ENV_VARS = [
  'CRM_API_KEY = ************',
  'MAX_RETRIES = 3',
  'TIMEOUT_SECONDS = 30',
];

const PERMISSIONS = [
  '读取 CRM 工单',
  '写入 CRM 更新',
  '访问 统一日志服务',
];

const CALLBACKS = [
  'on_success → /callbacks/crm/success',
  'on_failure → /callbacks/crm/failure',
  'timeout → 触发 PagerDuty 告警',
];

export default function ToolConfigPage() {
  const params = useParams<{ id: string }>();
  const title = useMemo(() => decodeURIComponent(params.id ?? '工具配置'), [params.id]);

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>⚙️ 工具配置 · {title}</div>
        <div style={{ color: '#666' }}>配置环境变量、权限与回调策略。</div>
      </section>

      <div className={styles.grid}>
        <section className={styles.card}>
          <div className={styles.cardTitle}>环境变量</div>
          <div className={styles.list}>
            {ENV_VARS.map((item) => (
              <div key={item} className={styles.listItem}>
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardTitle}>权限配置</div>
          <div className={styles.list}>
            {PERMISSIONS.map((item) => (
              <div key={item} className={styles.listItem}>
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardTitle}>回调 & 超时</div>
          <div className={styles.list}>
            {CALLBACKS.map((item) => (
              <div key={item} className={styles.listItem}>
                {item}
              </div>
            ))}
          </div>
          <div className={styles.cardTitle}>Code Snippet</div>
          <pre className={styles.codeBlock}>{`def on_failure(event: dict):\n    # TODO: 触发告警 & 回滚\n    pass`}</pre>
        </section>
      </div>
    </div>
  );
}
