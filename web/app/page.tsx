'use client';

import { useMemo, useState } from 'react';
import styles from './home.module.css';
import { toast } from 'sonner';

interface TemplateItem {
  readonly id: string;
  readonly icon: string;
  readonly name: string;
  readonly description: string;
}

interface ModalProps {
  readonly open: boolean;
  readonly title: string;
  readonly onClose: () => void;
  readonly items: TemplateItem[];
  readonly onSelect: (item: TemplateItem) => void;
}

function Modal({ open, title, onClose, items, onSelect }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <div className={styles.modalTitle}>{title}</div>
          <button type="button" className={styles.modalClose} onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
        <div className={styles.modalBody}>
          <div className={styles.templateList}>
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={styles.templateItem}
                onClick={() => onSelect(item)}
              >
                <div className={styles.templateIcon}>{item.icon}</div>
                <div className={styles.templateInfo}>
                  <div className={styles.templateName}>{item.name}</div>
                  <div className={styles.templateDesc}>{item.description}</div>
                </div>
                <div className={styles.templateAction}>选择</div>
              </button>
            ))}
          </div>
        </div>
        <div className={styles.modalFooter}>
          <button type="button" className={styles.modalButton} onClick={onClose}>
            取消
          </button>
        </div>
      </div>
    </div>
  );
}

const PLATFORM_STATS = [
  { label: '已构建Agent', value: '125' },
  { label: '活跃用户', value: '45' },
  { label: '平均构建时间', value: '3.2小时' },
  { label: '系统可用性', value: '98.5%' },
];

const QUICK_START = [
  { id: 'tutorial', icon: '🎓', label: '观看5分钟入门视频' },
  { id: 'templates', icon: '📚', label: '查看示例Agent模板' },
  { id: 'scenarios', icon: '🛠️', label: '使用预置业务场景' },
  { id: 'contact', icon: '📞', label: '联系解决方案架构师' },
];

const MY_AGENTS = [
  {
    id: 'complaint-bot',
    name: '客户投诉处理机器人',
    description: '运行中 • 今日处理 23 个案例',
    status: 'running' as const,
    actionIcon: '⚙️',
  },
  {
    id: 'sales-lead',
    name: '销售线索分析器',
    description: '构建中 • 预计完成时间 15 分钟',
    status: 'building' as const,
    actionIcon: '⏸️',
  },
  {
    id: 'risk-monitor',
    name: '金融风险监控助手',
    description: '告警 • 需查看最新异常事件',
    status: 'warning' as const,
    actionIcon: '⚠️',
  },
];

const ACTIVITIES = [
  { time: '15分钟前', description: '李工程师 更新了 "客服机器人" 的配置' },
  { time: '1小时前', description: '王分析师 完成了 "销售数据分析" 任务' },
  { time: '2小时前', description: '系统自动备份完成，共备份 <span class="highlight">125个Agent</span>' },
];

const TEMPLATE_ITEMS: TemplateItem[] = [
  {
    id: 'customer-service',
    icon: '📞',
    name: '智能客服机器人',
    description: '适用于售后服务，支持多轮对话和问题分类',
  },
  {
    id: 'data-analysis',
    icon: '📊',
    name: '数据分析助手',
    description: '自动生成报表，支持多种数据源和可视化',
  },
  {
    id: 'finance-audit',
    icon: '💰',
    name: '财务审核员',
    description: '智能发票审核，自动识别异常和风险',
  },
  {
    id: 'compliance-check',
    icon: '📋',
    name: '合规检查器',
    description: '文档合规性检查，支持多种标准',
  },
];

const SCENARIO_ITEMS: TemplateItem[] = [
  {
    id: 'ecommerce',
    icon: '🛒',
    name: '电商客服场景',
    description: '多渠道接入、售前售后统一处理',
  },
  {
    id: 'finance',
    icon: '🏦',
    name: '金融风控场景',
    description: '实时监控交易异常，接入风控模型',
  },
  {
    id: 'operation',
    icon: '🚀',
    name: '运营增长场景',
    description: '投放策略自动优化，效果追踪与复盘',
  },
];

function getAgentStatusClass(status: 'running' | 'building' | 'warning') {
  switch (status) {
    case 'running':
      return styles.statusRunning;
    case 'building':
      return styles.statusBuilding;
    case 'warning':
      return styles.statusWarning;
    default:
      return styles.statusRunning;
  }
}

export default function HomePage() {
  const [requirement, setRequirement] = useState('');
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [scenarioModalOpen, setScenarioModalOpen] = useState(false);

  const handleStartBuild = () => {
    if (!requirement.trim()) {
      toast.error('请先描述你的需求');
      return;
    }
    toast.success('构建流程已启动', {
      description: '我们将根据你的需求启动自动化 Agent 构建流水线。',
    });
    setRequirement('');
  };

  const handleTemplateSelect = (item: TemplateItem) => {
    toast.success(`已选择模板：${item.name}`);
    setTemplateModalOpen(false);
  };

  const handleScenarioSelect = (item: TemplateItem) => {
    toast.success(`已应用场景：${item.name}`);
    setScenarioModalOpen(false);
  };

  const activityNodes = useMemo(() => {
    return ACTIVITIES.map((activity, index) => (
      <div key={`${activity.time}-${index}`} className={styles.activityItem}>
        <div className={styles.activityTime}>{activity.time}</div>
        <div
          className={styles.activityDesc}
          dangerouslySetInnerHTML={{
            __html: activity.description.replace(
              '<span class="highlight">',
              `<span class="${styles.activityHighlight}">`,
            ),
          }}
        />
      </div>
    ));
  }, []);

  return (
    <div className={styles.container}>
      <section className={styles.heroSection}>
        <h1 className={styles.heroTitle}>💡 让 AI 帮你构建 AI</h1>
        <p className={styles.heroSubtitle}>从想法到实现，只需要一句话描述</p>
        <p className={styles.heroDescription}>More Agent, More Intelligence, More Business Impact</p>
      </section>

      <section className={styles.inputSection}>
        <textarea
          className={styles.inputTextarea}
          placeholder={`📝 描述你的需求...\n\n例如：我需要一个客服代理，能够自动处理客户投诉，根据问题严重程度分配给不同的专家，并自动生成处理报告`}
          value={requirement}
          onChange={(event) => setRequirement(event.target.value)}
        />
        <div className={styles.inputActions}>
          <button type="button" className={styles.primaryButton} onClick={handleStartBuild}>
            开始构建 🚀
          </button>
          <button type="button" className={styles.secondaryButton} onClick={() => setTemplateModalOpen(true)}>
            选择模板 📋
          </button>
        </div>
      </section>

      <section className={styles.dashboardGrid}>
        <div className={styles.card}>
          <h3 className={styles.cardTitle}>📊 平台统计</h3>
          <div className={styles.statsGrid}>
            {PLATFORM_STATS.map((stat) => (
              <div key={stat.label} className={styles.statItem}>
                <div className={styles.statNumber}>{stat.value}</div>
                <div className={styles.statLabel}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.card} ${styles.quickStartCard}`}>
          <h3 className={styles.cardTitle}>🎯 快速入门</h3>
          <div className={styles.quickStartList}>
            {QUICK_START.map((item) => (
              <button
                key={item.id}
                type="button"
                className={styles.quickStartItem}
                onClick={() => {
                  if (item.id === 'templates') {
                    setTemplateModalOpen(true);
                  } else if (item.id === 'scenarios') {
                    setScenarioModalOpen(true);
                  } else if (item.id === 'tutorial') {
                    toast('即将推出 5 分钟入门视频');
                  } else {
                    toast.success('已为你连接解决方案架构师');
                  }
                }}
              >
                <span>{item.icon}</span>
                <span className={styles.quickStartText}>{item.label}</span>
                <span className={styles.quickStartAction}>→</span>
              </button>
            ))}
          </div>
        </div>

        <div className={styles.card}>
          <h3 className={styles.cardTitle}>🏆 我的 Agent (5)</h3>
          <div className={styles.agentList}>
            {MY_AGENTS.map((agent) => (
              <div key={agent.id} className={styles.agentItem}>
                <span className={`${styles.agentStatus} ${getAgentStatusClass(agent.status)}`} />
                <div className={styles.agentInfo}>
                  <div className={styles.agentName}>{agent.name}</div>
                  <div className={styles.agentDesc}>{agent.description}</div>
                </div>
                <button
                  type="button"
                  className={styles.agentAction}
                  onClick={() => toast('即将开放更多管理动作')}
                  aria-label="管理 Agent"
                >
                  {agent.actionIcon}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.activityCard}>
        <h3 className={styles.cardTitle}>📝 最新动态</h3>
        <div className={styles.activityList}>{activityNodes}</div>
      </section>

      <Modal
        open={templateModalOpen}
        title="📋 选择 Agent 模板"
        items={TEMPLATE_ITEMS}
        onClose={() => setTemplateModalOpen(false)}
        onSelect={handleTemplateSelect}
      />

      <Modal
        open={scenarioModalOpen}
        title="🛠️ 预置业务场景"
        items={SCENARIO_ITEMS}
        onClose={() => setScenarioModalOpen(false)}
        onSelect={handleScenarioSelect}
      />
    </div>
  );
}
