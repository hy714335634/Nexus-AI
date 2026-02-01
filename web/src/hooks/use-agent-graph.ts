/**
 * Agent Graph Hooks
 *
 * 提供Agent关系图数据的React Query hooks
 */

import { useQuery } from '@tanstack/react-query';
import type {
  AgentGraphResponse,
  NodeDetailsResponse,
  GraphStatsResponse,
  GraphFilterParams,
} from '@/types/agent-graph';

const API_BASE = '/api/v1';

/**
 * 获取Agent关系图数据
 */
export function useAgentGraph(params?: GraphFilterParams) {
  return useQuery<AgentGraphResponse>({
    queryKey: ['agent-graph', params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();

      if (params?.include_tools !== undefined) {
        searchParams.set('include_tools', String(params.include_tools));
      }
      if (params?.include_versions !== undefined) {
        searchParams.set('include_versions', String(params.include_versions));
      }
      if (params?.category) {
        searchParams.set('category', params.category);
      }
      if (params?.tag) {
        searchParams.set('tag', params.tag);
      }
      if (params?.tool_type) {
        searchParams.set('tool_type', params.tool_type);
      }

      const url = `${API_BASE}/agent-graph${searchParams.toString() ? `?${searchParams}` : ''}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch agent graph');
      }

      return response.json();
    },
    staleTime: 30000, // 30秒缓存
  });
}

/**
 * 获取节点详情
 */
export function useNodeDetails(nodeId: string | null) {
  return useQuery<NodeDetailsResponse>({
    queryKey: ['agent-graph', 'node', nodeId],
    queryFn: async () => {
      if (!nodeId) {
        throw new Error('Node ID is required');
      }

      const response = await fetch(`${API_BASE}/agent-graph/node/${nodeId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch node details');
      }

      return response.json();
    },
    enabled: !!nodeId,
  });
}

/**
 * 获取图统计信息
 */
export function useGraphStats() {
  return useQuery<GraphStatsResponse>({
    queryKey: ['agent-graph', 'stats'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/agent-graph/stats`);

      if (!response.ok) {
        throw new Error('Failed to fetch graph stats');
      }

      return response.json();
    },
    staleTime: 60000, // 1分钟缓存
  });
}
