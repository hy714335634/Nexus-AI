import Link from 'next/link';

interface DeployPageProps {
  params: { id: string };
}

export default function ProjectDeployPage({ params }: DeployPageProps) {
  const projectId = decodeURIComponent(params.id);

  return (
    <section style={{ display: 'grid', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>部署项目</h1>
          <p style={{ margin: '6px 0 0', fontSize: '14px', color: 'var(--muted)' }}>
            项目 ID：{projectId}
          </p>
        </div>
        <Link href={`/projects/${projectId}`} style={{ fontSize: '13px', textDecoration: 'underline' }}>
          返回项目详情
        </Link>
      </header>

      <section
        style={{
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '24px',
          background: 'rgba(14, 16, 24, 0.92)',
          display: 'grid',
          gap: '16px',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '20px' }}>部署到 AgentCore</h2>
        <p style={{ margin: 0, fontSize: '14px', color: 'var(--muted)' }}>
          在下一阶段中将集成实际的部署 API。现在可以填写参数并提交预检。
        </p>

        <form
          style={{
            display: 'grid',
            gap: '16px',
            maxWidth: '420px',
          }}
        >
          <label style={{ display: 'grid', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--muted)' }}>Region</span>
            <input
              defaultValue="us-west-2"
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#fff',
              }}
            />
          </label>

          <label style={{ display: 'grid', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--muted)' }}>Project ID Override</span>
            <input
              placeholder="可选"
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#fff',
              }}
            />
          </label>

          <label style={{ display: 'grid', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--muted)' }}>备注</span>
            <textarea
              rows={4}
              placeholder="用于描述部署上下文或发布说明"
              style={{
                padding: '10px 12px',
                borderRadius: '10px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#fff',
                resize: 'vertical',
              }}
            />
          </label>

          <button
            type="button"
            style={{
              padding: '12px 18px',
              borderRadius: '12px',
              border: 'none',
              background: 'linear-gradient(135deg, #22d3ee, #6366f1)',
              color: '#fff',
              fontWeight: 600,
              cursor: 'not-allowed',
            }}
          >
            即将上线
          </button>
        </form>
      </section>
    </section>
  );
}
