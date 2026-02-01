/**
 * Agent Graph 类型定义
 */

// 节点类型枚举
export type NodeType = 'agent' | 'agent_version' | 'tool' | 'tool_group';

// 边类型枚举
export type EdgeType = 'uses_tool' | 'has_version' | 'calls_agent' | 'belongs_to' | 'agent_as_tool';

// 图节点
export interface GraphNode {
  id: string;
  name: string;
  type: NodeType;
  description?: string;
  category?: string;
  tags?: string[];
  version?: string;
  status?: string;
  created_date?: string;
  author?: string;
  supported_models?: string[];
  tools_count?: number;
  tool_path?: string;
  tool_type?: string;
  color?: string;
  size?: number;
  parent_id?: string | null;
  // 用于力导向图
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
}

// 图边
export interface GraphEdge {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: EdgeType;
  label?: string;
  weight?: number;
  color?: string;
}

// 图统计信息
export interface GraphStats {
  agent_count: number;
  version_count: number;
  tool_count: number;
  edge_count: number;
}

// 筛选选项
export interface GraphFilters {
  categories: string[];
  tags: string[];
  tool_types: string[];
}

// 完整图数据
export interface AgentGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
  filters: GraphFilters;
}

// API响应
export interface AgentGraphResponse {
  success: boolean;
  data: AgentGraphData;
}

// 节点详情响应
export interface NodeDetailsResponse {
  success: boolean;
  data: GraphNode & {
    related_edges?: GraphEdge[];
    used_by?: string[];
  };
}

// 图统计响应
export interface GraphStatsResponse {
  success: boolean;
  data: {
    stats: GraphStats;
    filters: GraphFilters;
  };
}

// 筛选参数
export interface GraphFilterParams {
  include_tools?: boolean;
  include_versions?: boolean;
  category?: string;
  tag?: string;
  tool_type?: string;
}

// 高亮配置
export interface HighlightConfig {
  nodeIds: Set<string>;
  edgeIds: Set<string>;
}

// 群集信息
export interface ClusterInfo {
  id: string;
  name: string;
  nodes: string[];
  color: string;
}
