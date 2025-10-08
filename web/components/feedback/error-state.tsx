interface ErrorStateProps {
  readonly title?: string;
  readonly description?: string;
  readonly onRetry?: () => void;
}

export function ErrorState({
  title = '无法加载数据',
  description = '请检查网络连接或稍后重试。',
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      style={{
        display: 'grid',
        gap: '12px',
        padding: '24px',
        borderRadius: '12px',
        border: '1px solid rgba(220, 38, 38, 0.35)',
        background: 'rgba(220, 38, 38, 0.08)',
      }}
    >
      <div style={{ fontWeight: 600 }}>{title}</div>
      <div style={{ fontSize: '14px', color: 'var(--muted)' }}>{description}</div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          style={{
            justifySelf: 'flex-start',
            padding: '8px 16px',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            background: 'transparent',
            color: '#fff',
            cursor: 'pointer',
          }}
        >
          重试
        </button>
      ) : null}
    </div>
  );
}
