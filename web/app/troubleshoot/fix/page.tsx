'use client';

import styles from './fix.module.css';
import { toast } from 'sonner';

const TASKS = [
  '生成多语言提示词补丁',
  '更新工具限流策略配置',
  '回归测试 5 轮多语言对话',
  '推送补丁至生产环境',
];

const TIMELINE = [
  '09:40 生成补丁完成，等待审批',
  '09:45 QA 回归中，预计 10 分钟',
  '10:00 计划部署并监控 30% 流量',
];

export default function TroubleshootFixPage() {
  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.title}>🛠 修复执行</div>
        <div className={styles.taskList}>
          {TASKS.map((task) => (
            <div key={task} className={styles.taskItem}>
              {task}
            </div>
          ))}
        </div>
        <button type="button" className={styles.title} onClick={() => toast.success('已通知部署团队')}>
          通知部署团队
        </button>
      </section>

      <section className={styles.card}>
        <div className={styles.title}>时间线</div>
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
