export interface StageLogOptions {
  readonly projectId: string;
  readonly stageId: string;
  readonly signal?: AbortSignal;
}

function buildLogPath(projectId: string, stageId: string) {
  // 默认尝试项目级日志，其次阶段细粒度日志
  const normalized = stageId.replace(/[^a-z0-9_-]/gi, '-');
  return [`/logs/stages/${projectId}.txt`, `/logs/stages/${projectId}-${normalized}.txt`];
}

export async function fetchStageLog({ projectId, stageId, signal }: StageLogOptions): Promise<string[]> {
  const paths = buildLogPath(projectId, stageId);
  for (const path of paths) {
    try {
      const response = await fetch(path, { signal, cache: 'no-store' });
      if (!response.ok) {
        continue;
      }
      const text = await response.text();
      if (!text.trim()) {
        continue;
      }
      return text.split('\n');
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        throw error;
      }
    }
  }

  const now = new Date().toISOString();
  return [
    `[${now}] 日志服务暂不可用，已返回示例数据。`,
    `[${now}] stage=${stageId} project=${projectId} 等待后端提供真实日志接口。`,
  ];
}
