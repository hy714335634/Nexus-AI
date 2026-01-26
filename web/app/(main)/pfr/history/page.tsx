'use client';

import { useState } from 'react';
import styles from './history.module.css';
import Link from 'next/link';

const HISTORY_ROWS = [
  {
    id: 'pfr-210',
    agent: '客服质检助手',
    reviewer: '李宁',
    score: '4',
    status: '已合入',
    date: '2024-03-12',
  },
  {
    id: 'pfr-209',
    agent: '销售线索分析器',
    reviewer: '张强',
    score: '3',
    status: '待复盘',
    date: '2024-03-11',
  },
];

export default function PfrHistoryPage() {
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('all');

  const filteredRows = HISTORY_ROWS.filter((row) => {
    const keyMatch = keyword ? row.agent.includes(keyword) || row.reviewer.includes(keyword) : true;
    const statusMatch = status === 'all' ? true : row.status === status;
    return keyMatch && statusMatch;
  });

  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <div className={styles.title}>📚 PFR 历史记录</div>
        <div className={styles.filters}>
          <input
            className={styles.input}
            placeholder="搜索 Agent / 评审人"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <select className={styles.select} value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">全部状态</option>
            <option value="已合入">已合入</option>
            <option value="待复盘">待复盘</option>
          </select>
          <button type="button" className={styles.select}>导出 CSV</button>
        </div>
      </section>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Agent</th>
            <th>评审人</th>
            <th>评分</th>
            <th>状态</th>
            <th>日期</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          {filteredRows.map((row) => (
            <tr key={row.id}>
              <td>{row.id}</td>
              <td>{row.agent}</td>
              <td>{row.reviewer}</td>
              <td>{row.score}</td>
              <td>{row.status}</td>
              <td>{row.date}</td>
              <td>
                <Link href={`/pfr/iterations/${row.id}`}>查看</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
