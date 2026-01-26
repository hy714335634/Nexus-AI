'use client';

import { useState } from 'react';
import styles from '../mcp.module.css';
import { toast } from 'sonner';

export default function McpCreatePage() {
  const [form, setForm] = useState({
    name: '',
    endpoint: 'https://',
    capabilities: '',
    token: '',
  });

  const submit = () => {
    toast.success('MCP 连接已创建', {
      description: `${form.name || '新连接'} 已添加到监控列表。`,
    });
    setForm({ name: '', endpoint: 'https://', capabilities: '', token: '' });
  };

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🔗 创建 MCP 连接</div>
        <div style={{ color: '#666' }}>配置能力声明、认证信息与连接测试。</div>
      </section>

      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label className={styles.field}>
          <span className={styles.label}>连接名称</span>
          <input
            required
            className={styles.input}
            value={form.name}
            onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Endpoint</span>
          <input
            required
            className={styles.input}
            value={form.endpoint}
            onChange={(event) => setForm((prev) => ({ ...prev, endpoint: event.target.value }))}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>能力声明</span>
          <textarea
            className={styles.textarea}
            placeholder="列出工具能力、输入输出结构、限制。"
            value={form.capabilities}
            onChange={(event) => setForm((prev) => ({ ...prev, capabilities: event.target.value }))}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>鉴权 Token</span>
          <input
            className={styles.input}
            value={form.token}
            onChange={(event) => setForm((prev) => ({ ...prev, token: event.target.value }))}
          />
        </label>

        <div className={styles.footer}>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('测试连接成功')}>
            测试连接
          </button>
          <button type="submit" className={styles.primaryButton}>
            创建连接
          </button>
        </div>
      </form>
    </div>
  );
}
