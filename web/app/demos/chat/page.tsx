'use client';

import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import styles from '../chat.module.css';

interface ChatMessage {
  readonly id: string;
  readonly role: 'user' | 'agent';
  readonly content: string;
  readonly timestamp: string;
  readonly toolCall?: string;
}

const BASE_MESSAGES: ChatMessage[] = [
  {
    id: '1',
    role: 'user',
    content: '你好，我需要查看本周的客服质检报告。',
    timestamp: '09:28',
  },
  {
    id: '2',
    role: 'agent',
    content: '收到，请输入要检索的日期范围，例如“3月1日至3月7日”。',
    timestamp: '09:28',
  },
];

const ACTIVE_MODELS = ['Claude 3 Opus', 'Claude 3 Sonnet', 'GPT-4 Turbo'];

const TIMELINE = [
  '09:32 触发工具：crm.weekly_report 查询',
  '09:33 完成数据聚合，生成表格摘要',
  '09:34 更新知识库记忆胶囊',
];

export default function ChatDemoPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(BASE_MESSAGES);
  const [model, setModel] = useState(ACTIVE_MODELS[0]);
  const [input, setInput] = useState('');
  const [contextInjected, setContextInjected] = useState(false);

  const sendMessage = () => {
    if (!input.trim()) {
      toast.error('请输入测试内容');
      return;
    }

    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    const userMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: input,
      timestamp,
    };

    const agentReply: ChatMessage = {
      id: `${Date.now()}-agent`,
      role: 'agent',
      content: `模型 ${model} 已收到更新，将调用工具生成报告。`,
      timestamp,
      toolCall: 'crm.weekly_report',
    };

    setMessages((prev) => [...prev, userMessage, agentReply]);
    setInput('');
  };

  const contextText = useMemo(() => {
    if (contextInjected) {
      return '已注入上下文：\n• 上周投诉 32 起 \n• 满意度 4.7/5 \n• 建议关注物流延迟问题';
    }
    return '点击“注入上下文”以加载示例环境变量、工具结果等上下文信息。';
  }, [contextInjected]);

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>🧪 对话测试 · 多模型 / 工具回显</div>
        <div style={{ color: '#666' }}>模拟真实对话，支持模型切换、上下文注入与工具调用展示。</div>
      </section>

      <div className={styles.chatLayout}>
        <section className={styles.chatCard}>
          <div className={styles.messageList}>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`${styles.message} ${message.role === 'user' ? styles.messageUser : styles.messageAgent}`}
              >
                <div className={styles.messageMeta}>
                  <strong>{message.role === 'user' ? '你' : 'Agent'}</strong> · {message.timestamp}
                </div>
                <div className={styles.messageContent}>{message.content}</div>
                {message.toolCall ? (
                  <div className={styles.toolsBox}>
                    <strong>工具调用：</strong>
                    <span>{message.toolCall}</span>
                    <span>结果：{`{\"report_id\": \"weekly-2024-10\"}`}</span>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div className={styles.inputArea}>
            <textarea
              className={styles.textarea}
              placeholder="输入测试对话内容..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
            <div className={styles.controls}>
              <select className={styles.select} value={model} onChange={(event) => setModel(event.target.value)}>
                {ACTIVE_MODELS.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => {
                  setContextInjected(true);
                  toast.success('已注入上下文');
                }}
              >
                注入上下文
              </button>
              <button type="button" className={styles.primaryButton} onClick={sendMessage}>
                发送
              </button>
            </div>
          </div>
        </section>

        <aside className={styles.sideCard}>
          <div className={styles.sideCardTitle}>上下文 / 工具日志</div>
          <pre style={{ background: '#0f172a', color: '#cbd5f5', padding: 16, borderRadius: 12 }}>
            {contextText}
          </pre>
          <div className={styles.sideCardTitle}>节点时间线</div>
          <div className={styles.timeline}>
            {TIMELINE.map((item) => (
              <div key={item} className={styles.timelineItem}>
                {item}
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
