'use client';

import { useState } from 'react';
import styles from './create.module.css';
import { toast } from 'sonner';

const CATEGORIES = ['检索工具', '通知工具', '数据同步', '自定义'];

export default function ToolCreatePage() {
  const [form, setForm] = useState({
    name: '',
    category: CATEGORIES[0],
    description: '',
    entrypoint: 'tools/sample_tool.py',
  });

  const submit = () => {
    toast.success('工具创建任务已提交', {
      description: `${form.name || '新工具'} 将启动构建流程。`,
    });
    setForm({ name: '', category: CATEGORIES[0], description: '', entrypoint: 'tools/sample_tool.py' });
  };

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🛠️ 新建工具向导</div>
        <div style={{ color: '#666' }}>填写工具信息，我们会自动生成代码模板与依赖检查。</div>
      </section>

      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label className={styles.field}>
          <span className={styles.label}>工具名称</span>
          <input
            required
            className={styles.input}
            value={form.name}
            placeholder="例如：CRM 工单写入"
            onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
          />
        </label>

        <div className={styles.gridTwo}>
          <label className={styles.field}>
            <span className={styles.label}>分类</span>
            <select
              className={styles.select}
              value={form.category}
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
            >
              {CATEGORIES.map((category) => (
                <option key={category}>{category}</option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.label}>入口文件</span>
            <input
              className={styles.input}
              value={form.entrypoint}
              onChange={(event) => setForm((prev) => ({ ...prev, entrypoint: event.target.value }))}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>功能描述</span>
          <textarea
            required
            className={styles.textarea}
            placeholder="说明工具的输入参数、调用外部服务与返回结果。"
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
          />
        </label>

        <div className={styles.field}>
          <span className={styles.label}>代码模板预览</span>
          <div className={styles.templateBox}>
            {`def handler(payload: dict) -> dict:\n    # TODO: 引入参数校验 / API 调用 / 日志上报\n    return {"status": "ok"}`}
          </div>
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.secondaryButton} onClick={() => toast('已保存草稿')}>
            保存草稿
          </button>
          <button type="submit" className={styles.primaryButton}>
            提交构建
          </button>
        </div>
      </form>
    </div>
  );
}
