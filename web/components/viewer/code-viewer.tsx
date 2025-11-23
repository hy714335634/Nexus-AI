'use client';

import { useCallback, useState } from 'react';
import { Highlight, themes } from 'prism-react-renderer';

interface CodeViewerProps {
  readonly content: string;
  readonly language?: string;
  readonly filename?: string;
  readonly downloadName?: string;
  readonly emptyFallback?: string;
}

export function CodeViewer({
  content,
  language = 'javascript',
  filename,
  downloadName,
  emptyFallback = '暂无可显示的内容。',
}: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error('复制失败', error);
    }
  }, [content]);

  const onDownload = useCallback(() => {
    try {
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = downloadName || filename || 'artifact.txt';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    } catch (error) {
      console.error('下载失败', error);
    }
  }, [content, downloadName, filename]);

  if (!content?.trim()) {
    return <div style={{ fontSize: '13px', color: 'var(--muted)' }}>{emptyFallback}</div>;
  }

  return (
    <div
      style={{
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(10, 12, 20, 0.9)',
        overflow: 'hidden',
        display: 'grid',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'rgba(15, 17, 28, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '12px',
          color: 'var(--muted)',
        }}
      >
        <span>{filename ?? downloadName ?? 'artifact'}</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={onCopy}
            style={{
              padding: '4px 8px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              background: 'transparent',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            {copied ? '已复制' : '复制'}
          </button>
          <button
            type="button"
            onClick={onDownload}
            style={{
              padding: '4px 8px',
              borderRadius: '8px',
              border: '1px solid rgba(79, 70, 229, 0.45)',
              background: 'rgba(79, 70, 229, 0.18)',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            下载
          </button>
        </div>
      </div>

      <div style={{ maxHeight: '420px', overflow: 'auto' }}>
        <Highlight theme={themes.nightOwl} code={content} language={language as any}>
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre className={className} style={{ ...style, margin: 0, padding: '16px' }}>
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line, key: i })}>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token, key })} />
                  ))}
                </div>
              ))}
            </pre>
          )}
        </Highlight>
      </div>
    </div>
  );
}
