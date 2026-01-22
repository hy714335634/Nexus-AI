'use client';

import { useCallback, useState, useEffect, useRef } from 'react';
import { Highlight, themes } from 'prism-react-renderer';

interface EditableCodeViewerProps {
  readonly content: string;
  readonly language?: string;
  readonly filename?: string;
  readonly downloadName?: string;
  readonly emptyFallback?: string;
  readonly editable?: boolean;
  readonly onSave?: (content: string) => Promise<void>;
  readonly saving?: boolean;
  readonly maxHeight?: string;
}

export function EditableCodeViewer({
  content: initialContent,
  language = 'javascript',
  filename,
  downloadName,
  emptyFallback = '暂无可显示的内容。',
  editable = false,
  onSave,
  saving = false,
  maxHeight = '500px',
}: EditableCodeViewerProps) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(initialContent);
  const [hasChanges, setHasChanges] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 当初始内容变化时更新
  useEffect(() => {
    setEditedContent(initialContent);
    setHasChanges(false);
  }, [initialContent]);

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(isEditing ? editedContent : initialContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error('复制失败', error);
    }
  }, [initialContent, editedContent, isEditing]);

  const onDownload = useCallback(() => {
    try {
      const blob = new Blob([isEditing ? editedContent : initialContent], { type: 'text/plain;charset=utf-8' });
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
  }, [initialContent, editedContent, isEditing, downloadName, filename]);

  const handleEdit = useCallback(() => {
    setIsEditing(true);
    // 聚焦到文本框
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  }, []);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditedContent(initialContent);
    setHasChanges(false);
  }, [initialContent]);

  const handleSave = useCallback(async () => {
    if (onSave && hasChanges) {
      await onSave(editedContent);
      setIsEditing(false);
      setHasChanges(false);
    }
  }, [onSave, editedContent, hasChanges]);

  const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setEditedContent(newContent);
    setHasChanges(newContent !== initialContent);
  }, [initialContent]);

  // 处理 Tab 键
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newContent = editedContent.substring(0, start) + '    ' + editedContent.substring(end);
      setEditedContent(newContent);
      setHasChanges(newContent !== initialContent);
      // 设置光标位置
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4;
      }, 0);
    }
    // Ctrl/Cmd + S 保存
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      if (hasChanges && onSave) {
        handleSave();
      }
    }
    // Escape 取消编辑
    if (e.key === 'Escape') {
      handleCancel();
    }
  }, [editedContent, initialContent, hasChanges, onSave, handleSave, handleCancel]);

  const displayContent = isEditing ? editedContent : initialContent;

  if (!displayContent?.trim() && !isEditing) {
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
      {/* 头部工具栏 */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>{filename ?? downloadName ?? 'artifact'}</span>
          {hasChanges && (
            <span style={{ 
              color: '#f59e0b', 
              fontSize: '11px',
              padding: '2px 6px',
              background: 'rgba(245, 158, 11, 0.15)',
              borderRadius: '4px'
            }}>
              未保存
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {isEditing ? (
            <>
              <button
                type="button"
                onClick={handleCancel}
                disabled={saving}
                style={{
                  padding: '4px 8px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  background: 'transparent',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.5 : 1,
                }}
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={!hasChanges || saving}
                style={{
                  padding: '4px 12px',
                  borderRadius: '8px',
                  border: '1px solid rgba(34, 197, 94, 0.45)',
                  background: hasChanges ? 'rgba(34, 197, 94, 0.25)' : 'rgba(34, 197, 94, 0.1)',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: hasChanges && !saving ? 'pointer' : 'not-allowed',
                  opacity: hasChanges && !saving ? 1 : 0.5,
                }}
              >
                {saving ? '保存中...' : '保存'}
              </button>
            </>
          ) : (
            <>
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
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  background: 'transparent',
                  color: '#fff',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                下载
              </button>
              {editable && (
                <button
                  type="button"
                  onClick={handleEdit}
                  style={{
                    padding: '4px 12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(79, 70, 229, 0.45)',
                    background: 'rgba(79, 70, 229, 0.18)',
                    color: '#fff',
                    fontSize: '12px',
                    cursor: 'pointer',
                  }}
                >
                  编辑
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* 内容区域 */}
      <div style={{ maxHeight, overflow: 'auto' }}>
        {isEditing ? (
          <textarea
            ref={textareaRef}
            value={editedContent}
            onChange={handleContentChange}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            style={{
              width: '100%',
              minHeight: '400px',
              height: '100%',
              padding: '16px',
              margin: 0,
              border: 'none',
              outline: 'none',
              background: 'rgba(10, 12, 20, 0.95)',
              color: '#e2e8f0',
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              fontSize: '13px',
              lineHeight: '1.6',
              resize: 'vertical',
              tabSize: 4,
            }}
          />
        ) : (
          <Highlight theme={themes.nightOwl} code={displayContent} language={language as any}>
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
              <pre className={className} style={{ ...style, margin: 0, padding: '16px' }}>
                {tokens.map((line, i) => (
                  <div key={i} {...getLineProps({ line, key: i })}>
                    <span style={{ 
                      display: 'inline-block', 
                      width: '40px', 
                      color: 'rgba(255,255,255,0.3)',
                      userSelect: 'none',
                      textAlign: 'right',
                      paddingRight: '16px',
                      fontSize: '12px',
                    }}>
                      {i + 1}
                    </span>
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token, key })} />
                    ))}
                  </div>
                ))}
              </pre>
            )}
          </Highlight>
        )}
      </div>
    </div>
  );
}
