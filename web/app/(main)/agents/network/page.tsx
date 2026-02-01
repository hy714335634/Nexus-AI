'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Button } from '@/components/ui';
import { useAgentGraph, useGraphStats } from '@/hooks/use-agent-graph';
import type { GraphNode, GraphFilterParams } from '@/types/agent-graph';
import { ArrowLeft, ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react';
import styles from './network.module.css';

// 力导向图的节点和边类型（兼容react-force-graph-2d）
interface ForceGraphNode {
  id: string;
  name: string;
  type: string;
  color?: string;
  val?: number;
  [key: string]: unknown;
}

interface ForceGraphLink {
  id: string;
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
  type: string;
  color?: string;
  [key: string]: unknown;
}

interface ForceGraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}

// 动态导入ForceGraph2D以避免SSR问题
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => <div className={styles.loading}>加载图形引擎...</div>,
});

// 节点类型配置
const NODE_TYPE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  agent: { label: 'Agent', icon: '🤖', color: '#6366f1' },
  agent_version: { label: '版本', icon: '📦', color: '#8b5cf6' },
  tool: { label: '工具', icon: '🔧', color: '#10b981' },
  tool_group: { label: '工具组', icon: '📁', color: '#14b8a6' },
};

// 工具类型颜色
const TOOL_TYPE_COLORS: Record<string, string> = {
  strands_tools: '#3b82f6',
  generated_tools: '#22c55e',
  system_tools: '#f59e0b',
  template_tools: '#8b5cf6',
  mcp: '#ec4899',
};

// 边类型配置
const EDGE_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  uses_tool: { label: '使用工具', color: '#94a3b8' },
  has_version: { label: '版本关系', color: '#c4b5fd' },
  calls_agent: { label: '调用Agent', color: '#f97316' },
  belongs_to: { label: '属于', color: '#5eead4' },
  agent_as_tool: { label: 'Agent作为工具', color: '#ef4444' },
};

export default function AgentNetworkPage() {
  // 筛选状态
  const [filters, setFilters] = useState<GraphFilterParams>({
    include_tools: true,
    include_versions: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedTag, setSelectedTag] = useState<string>('');
  const [selectedToolType, setSelectedToolType] = useState<string>('');

  // 选中节点
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());

  // 图引用
  const graphRef = useRef<any>(null);

  // 获取数据
  const { data: graphResponse, isLoading, error } = useAgentGraph({
    ...filters,
    category: selectedCategory || undefined,
    tag: selectedTag || undefined,
    tool_type: selectedToolType || undefined,
  });
  const { data: statsResponse } = useGraphStats();

  // 处理图数据
  const graphData: ForceGraphData = useMemo(() => {
    if (!graphResponse?.data) {
      return { nodes: [], links: [] };
    }

    let nodes = graphResponse.data.nodes;
    let edges = graphResponse.data.edges;

    // 搜索筛选
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchedNodeIds = new Set(
        nodes
          .filter(
            (n) =>
              n.name.toLowerCase().includes(query) ||
              n.description?.toLowerCase().includes(query) ||
              n.tags?.some((t) => t.toLowerCase().includes(query))
          )
          .map((n) => n.id)
      );

      // 包含相关节点
      edges.forEach((e) => {
        const sourceId = typeof e.source === 'string' ? e.source : (e.source as ForceGraphNode).id;
        const targetId = typeof e.target === 'string' ? e.target : (e.target as ForceGraphNode).id;
        if (matchedNodeIds.has(sourceId)) matchedNodeIds.add(targetId);
        if (matchedNodeIds.has(targetId)) matchedNodeIds.add(sourceId);
      });

      nodes = nodes.filter((n) => matchedNodeIds.has(n.id));
      edges = edges.filter((e) => {
        const sourceId = typeof e.source === 'string' ? e.source : (e.source as ForceGraphNode).id;
        const targetId = typeof e.target === 'string' ? e.target : (e.target as ForceGraphNode).id;
        return matchedNodeIds.has(sourceId) && matchedNodeIds.has(targetId);
      });
    }

    return {
      nodes: nodes.map((n): ForceGraphNode => ({
        id: n.id,
        name: n.name,
        type: n.type,
        description: n.description,
        category: n.category,
        tags: n.tags,
        version: n.version,
        status: n.status,
        tool_type: n.tool_type,
        tool_path: n.tool_path,
        color: n.tool_type
          ? TOOL_TYPE_COLORS[n.tool_type] || NODE_TYPE_CONFIG[n.type]?.color
          : NODE_TYPE_CONFIG[n.type]?.color || '#6b7280',
        val: n.type === 'agent' ? 8 : n.type === 'agent_version' ? 5 : 3,
      })),
      links: edges.map((e): ForceGraphLink => ({
        id: e.id,
        source: typeof e.source === 'string' ? e.source : (e.source as { id: string }).id,
        target: typeof e.target === 'string' ? e.target : (e.target as { id: string }).id,
        type: e.type,
        color: EDGE_TYPE_CONFIG[e.type]?.color || '#94a3b8',
      })),
    };
  }, [graphResponse, searchQuery]);


  // 节点点击处理
  const handleNodeClick = useCallback((node: ForceGraphNode) => {
    // 将节点数据转换为GraphNode用于显示详情
    const graphNode: GraphNode = {
      id: node.id,
      name: node.name,
      type: node.type as any,
      description: node.description as string | undefined,
      category: node.category as string | undefined,
      tags: node.tags as string[] | undefined,
      version: node.version as string | undefined,
      status: node.status as string | undefined,
      tool_type: node.tool_type as string | undefined,
      tool_path: node.tool_path as string | undefined,
      color: node.color,
    };
    setSelectedNode(graphNode);
    const nodeIds = new Set<string>([node.id]);
    const linkIds = new Set<string>();

    graphData.links.forEach((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as ForceGraphNode).id;
      const targetId = typeof link.target === 'string' ? link.target : (link.target as ForceGraphNode).id;
      if (sourceId === node.id || targetId === node.id) {
        linkIds.add(link.id);
        nodeIds.add(sourceId);
        nodeIds.add(targetId);
      }
    });

    setHighlightNodes(nodeIds);
    setHighlightLinks(linkIds);
  }, [graphData.links]);

  // 背景点击处理
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
  }, []);

  // 节点悬停处理
  const handleNodeHover = useCallback((node: ForceGraphNode | null) => {
    if (!node) {
      if (!selectedNode) {
        setHighlightNodes(new Set());
        setHighlightLinks(new Set());
      }
      return;
    }
    if (selectedNode) return;

    const nodeIds = new Set<string>([node.id]);
    const linkIds = new Set<string>();

    graphData.links.forEach((link) => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as ForceGraphNode).id;
      const targetId = typeof link.target === 'string' ? link.target : (link.target as ForceGraphNode).id;
      if (sourceId === node.id || targetId === node.id) {
        linkIds.add(link.id);
        nodeIds.add(sourceId);
        nodeIds.add(targetId);
      }
    });

    setHighlightNodes(nodeIds);
    setHighlightLinks(linkIds);
  }, [graphData.links, selectedNode]);

  // 自定义节点绘制
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name;
      const fontSize = Math.max(12 / globalScale, 3);
      const nodeSize = node.val || 5;
      const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);

      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI);
      ctx.fillStyle = isHighlighted ? node.color : `${node.color}40`;
      ctx.fill();

      if (selectedNode?.id === node.id) {
        ctx.strokeStyle = '#111827';
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      if (globalScale > 0.5 || highlightNodes.has(node.id)) {
        ctx.font = `${fontSize}px Sans-Serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = isHighlighted ? '#111827' : '#9ca3af';
        ctx.fillText(label, node.x, node.y + nodeSize + fontSize);
      }
    },
    [highlightNodes, selectedNode]
  );

  // 自定义边绘制
  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(link.id);

      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.strokeStyle = isHighlighted ? link.color : `${link.color}30`;
      ctx.lineWidth = isHighlighted ? 1.5 / globalScale : 0.5 / globalScale;
      ctx.stroke();

      if (link.type === 'calls_agent' && isHighlighted) {
        const arrowLength = 8 / globalScale;
        const dx = link.target.x - link.source.x;
        const dy = link.target.y - link.source.y;
        const angle = Math.atan2(dy, dx);
        const targetNodeSize = link.target.val || 5;
        const endX = link.target.x - Math.cos(angle) * targetNodeSize;
        const endY = link.target.y - Math.sin(angle) * targetNodeSize;

        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
          endX - arrowLength * Math.cos(angle - Math.PI / 6),
          endY - arrowLength * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
          endX - arrowLength * Math.cos(angle + Math.PI / 6),
          endY - arrowLength * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fillStyle = link.color;
        ctx.fill();
      }
    },
    [highlightLinks]
  );

  // 图控制函数
  const handleZoomIn = () => graphRef.current?.zoom(graphRef.current.zoom() * 1.5, 300);
  const handleZoomOut = () => graphRef.current?.zoom(graphRef.current.zoom() / 1.5, 300);
  const handleFitView = () => graphRef.current?.zoomToFit(400, 50);
  const handleReset = () => {
    graphRef.current?.zoomToFit(400, 50);
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
  };

  useEffect(() => {
    if (graphData.nodes.length > 0 && graphRef.current) {
      setTimeout(() => graphRef.current?.zoomToFit(400, 50), 500);
    }
  }, [graphData.nodes.length]);

  const stats = statsResponse?.data?.stats;
  const filterOptions = statsResponse?.data?.filters;


  return (
    <div className="page-container">
      <Header
        title="交互网络"
        description="可视化展示Agent、工具之间的调用关系和依赖网络"
        actions={
          <Link href="/agents">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4" />
              返回Agent列表
            </Button>
          </Link>
        }
      />

      <div className={styles.container}>
        <div className={styles.toolbar}>
          <div className={styles.filterGroup}>
            <input
              type="text"
              placeholder="搜索节点..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>

          <div className={styles.divider} />

          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>分类:</span>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className={styles.select}
            >
              <option value="">全部</option>
              {filterOptions?.categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>标签:</span>
            <select
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              className={styles.select}
            >
              <option value="">全部</option>
              {filterOptions?.tags.map((tag) => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>
          </div>

          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>工具类型:</span>
            <select
              value={selectedToolType}
              onChange={(e) => setSelectedToolType(e.target.value)}
              className={styles.select}
            >
              <option value="">全部</option>
              {filterOptions?.tool_types.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className={styles.divider} />

          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={filters.include_tools}
              onChange={(e) => setFilters((f) => ({ ...f, include_tools: e.target.checked }))}
            />
            显示工具
          </label>

          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={filters.include_versions}
              onChange={(e) => setFilters((f) => ({ ...f, include_versions: e.target.checked }))}
            />
            显示版本
          </label>
        </div>

        <div className={styles.mainContent}>
          <div className={styles.graphContainer}>
            {isLoading ? (
              <div className={styles.loading}>加载中...</div>
            ) : error ? (
              <div className={styles.error}>加载失败: {String(error)}</div>
            ) : (
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeId="id"
                nodeLabel="name"
                nodeCanvasObject={nodeCanvasObject}
                nodeCanvasObjectMode={() => 'replace'}
                linkCanvasObject={linkCanvasObject}
                linkCanvasObjectMode={() => 'replace'}
                onNodeClick={handleNodeClick as any}
                onNodeHover={handleNodeHover as any}
                onBackgroundClick={handleBackgroundClick}
                enableNodeDrag={true}
                enableZoomInteraction={true}
                enablePanInteraction={true}
                cooldownTicks={100}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                backgroundColor="#ffffff"
              />
            )}

            <div className={styles.graphControls}>
              <button className={styles.controlButton} onClick={handleZoomIn} title="放大">
                <ZoomIn size={18} />
              </button>
              <button className={styles.controlButton} onClick={handleZoomOut} title="缩小">
                <ZoomOut size={18} />
              </button>
              <button className={styles.controlButton} onClick={handleFitView} title="适应视图">
                <Maximize2 size={18} />
              </button>
              <button className={styles.controlButton} onClick={handleReset} title="重置">
                <RotateCcw size={18} />
              </button>
            </div>
          </div>


          <div className={styles.sidebar}>
            <div className={styles.statsCard}>
              <div className={styles.statsTitle}>图统计</div>
              <div className={styles.statsGrid}>
                <div className={styles.statItem}>
                  <div className={styles.statValue}>{stats?.agent_count || 0}</div>
                  <div className={styles.statLabel}>Agent</div>
                </div>
                <div className={styles.statItem}>
                  <div className={styles.statValue}>{stats?.version_count || 0}</div>
                  <div className={styles.statLabel}>版本</div>
                </div>
                <div className={styles.statItem}>
                  <div className={styles.statValue}>{stats?.tool_count || 0}</div>
                  <div className={styles.statLabel}>工具</div>
                </div>
                <div className={styles.statItem}>
                  <div className={styles.statValue}>{stats?.edge_count || 0}</div>
                  <div className={styles.statLabel}>关系</div>
                </div>
              </div>
            </div>

            <div className={styles.detailsCard}>
              <div className={styles.detailsTitle}>📋 节点详情</div>
              {selectedNode ? (
                <div className={styles.nodeInfo}>
                  <div className={styles.nodeHeader}>
                    <div
                      className={styles.nodeIcon}
                      style={{ backgroundColor: `${selectedNode.color}20` }}
                    >
                      {NODE_TYPE_CONFIG[selectedNode.type]?.icon || '📦'}
                    </div>
                    <div>
                      <div className={styles.nodeName}>{selectedNode.name}</div>
                      <div className={styles.nodeType}>
                        {NODE_TYPE_CONFIG[selectedNode.type]?.label || selectedNode.type}
                      </div>
                    </div>
                  </div>

                  {selectedNode.description && (
                    <div className={styles.nodeDescription}>{selectedNode.description}</div>
                  )}

                  <div className={styles.nodeMetadata}>
                    {selectedNode.category && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>分类:</span>
                        <span className={styles.metadataValue}>{selectedNode.category}</span>
                      </div>
                    )}
                    {selectedNode.version && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>版本:</span>
                        <span className={styles.metadataValue}>{selectedNode.version}</span>
                      </div>
                    )}
                    {selectedNode.status && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>状态:</span>
                        <span className={styles.metadataValue}>{selectedNode.status}</span>
                      </div>
                    )}
                    {selectedNode.tool_type && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>类型:</span>
                        <span className={styles.metadataValue}>{selectedNode.tool_type}</span>
                      </div>
                    )}
                    {selectedNode.tool_path && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>路径:</span>
                        <span className={styles.metadataValue}>{selectedNode.tool_path}</span>
                      </div>
                    )}
                    {selectedNode.tags && selectedNode.tags.length > 0 && (
                      <div className={styles.metadataItem}>
                        <span className={styles.metadataLabel}>标签:</span>
                        <div className={styles.tagList}>
                          {selectedNode.tags.map((tag) => (
                            <span key={tag} className={styles.tag}>{tag}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className={styles.detailsEmpty}>点击节点查看详情</div>
              )}
            </div>

            <div className={styles.legend}>
              <div className={styles.legendTitle}>图例</div>
              <div className={styles.legendItems}>
                {Object.entries(NODE_TYPE_CONFIG).map(([type, config]) => (
                  <div key={type} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ backgroundColor: config.color }} />
                    <span>{config.icon} {config.label}</span>
                  </div>
                ))}
                <div style={{ height: '0.5rem' }} />
                {Object.entries(EDGE_TYPE_CONFIG).map(([type, config]) => (
                  <div key={type} className={styles.legendItem}>
                    <span className={styles.legendLine} style={{ backgroundColor: config.color }} />
                    <span>{config.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
