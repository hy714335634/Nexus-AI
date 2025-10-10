interface LoadingStateProps {
  readonly message?: string;
}

export function LoadingState({ message = 'Loading data…' }: LoadingStateProps) {
  return (
    <div
      style={{
        display: 'grid',
        gap: '12px',
        padding: '24px',
        borderRadius: '12px',
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(79, 70, 229, 0.35)',
      }}
    >
      <span style={{ fontSize: '14px', color: 'var(--muted)' }}>{message}</span>
      <div
        style={{
          height: '4px',
          width: '100%',
          borderRadius: '999px',
          overflow: 'hidden',
          background: 'rgba(79, 70, 229, 0.25)',
        }}
      >
        <div
          style={{
            height: '100%',
            width: '40%',
            background: 'var(--primary)',
            animation: 'pulse 1.4s ease-in-out infinite',
          }}
        />
      </div>
    </div>
  );
}
