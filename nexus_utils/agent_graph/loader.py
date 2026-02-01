"""
Agent Graph 加载器

负责从YAML文件加载Agent信息并构建图数据
"""

import os
import yaml
from pathlib import Path
from typing import Optional

from .models import (
    AgentNode,
    ToolNode,
    GraphEdge,
    AgentGraphData,
    NodeType,
    EdgeType,
)


# 节点颜色配置
NODE_COLORS = {
    NodeType.AGENT: "#6366f1",           # 紫色 - Agent主节点
    NodeType.AGENT_VERSION: "#8b5cf6",   # 浅紫色 - Agent版本
    NodeType.TOOL: "#10b981",            # 绿色 - 工具
    NodeType.TOOL_GROUP: "#14b8a6",      # 青色 - 工具组
}

# 边颜色配置
EDGE_COLORS = {
    EdgeType.USES_TOOL: "#94a3b8",       # 灰色 - 使用工具
    EdgeType.HAS_VERSION: "#c4b5fd",     # 浅紫色 - 版本关系
    EdgeType.CALLS_AGENT: "#f97316",     # 橙色 - Agent调用Agent
    EdgeType.BELONGS_TO: "#5eead4",      # 青色 - 属于工具组
    EdgeType.AGENT_AS_TOOL: "#ef4444",   # 红色 - Agent被封装为工具
}

# 工具类型颜色
TOOL_TYPE_COLORS = {
    "strands_tools": "#3b82f6",      # 蓝色
    "generated_tools": "#22c55e",    # 绿色
    "system_tools": "#f59e0b",       # 黄色
    "template_tools": "#8b5cf6",     # 紫色
    "mcp": "#ec4899",                # 粉色
}


class AgentGraphLoader:
    """Agent图数据加载器"""

    def __init__(self, prompts_base_path: str = "prompts/generated_agents_prompts"):
        """
        初始化加载器

        参数:
            prompts_base_path: Agent提示词目录路径
        """
        self.prompts_base_path = Path(prompts_base_path)
        self._nodes: dict[str, AgentNode | ToolNode] = {}
        self._edges: list[GraphEdge] = []
        self._categories: set[str] = set()
        self._tags: set[str] = set()
        self._tool_types: set[str] = set()

    def load_all_agents(self) -> AgentGraphData:
        """
        加载所有Agent并构建图数据

        返回:
            AgentGraphData: 完整的图数据
        """
        self._nodes.clear()
        self._edges.clear()
        self._categories.clear()
        self._tags.clear()
        self._tool_types.clear()

        # 遍历所有Agent目录
        if not self.prompts_base_path.exists():
            return AgentGraphData()

        for agent_dir in self.prompts_base_path.iterdir():
            if agent_dir.is_dir():
                self._load_agent_from_directory(agent_dir)

        # 构建图数据
        return self._build_graph_data()

    def _load_agent_from_directory(self, agent_dir: Path) -> None:
        """
        从目录加载单个Agent

        参数:
            agent_dir: Agent目录路径
        """
        # 查找YAML文件
        yaml_files = list(agent_dir.glob("*.yaml")) + list(agent_dir.glob("*.yml"))
        if not yaml_files:
            return

        # 加载第一个YAML文件
        yaml_file = yaml_files[0]
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading {yaml_file}: {e}")
            return

        if not data or 'agent' not in data:
            return

        agent_data = data['agent']
        agent_name = agent_data.get('name', agent_dir.name)
        agent_id = f"agent_{agent_name}"

        # 创建Agent主节点
        agent_node = AgentNode(
            id=agent_id,
            name=agent_name,
            node_type=NodeType.AGENT,
            description=agent_data.get('description', ''),
            category=agent_data.get('category', ''),
            tags=[],
            color=NODE_COLORS[NodeType.AGENT],
            size=3,
        )

        # 收集分类
        if agent_node.category:
            self._categories.add(agent_node.category)

        # 处理版本信息
        versions = agent_data.get('versions', [])
        for idx, version_data in enumerate(versions):
            self._process_version(agent_id, agent_name, version_data, idx)

        # 更新Agent节点的工具数量
        tools_count = sum(
            1 for edge in self._edges
            if edge.source.startswith(agent_id) and edge.edge_type == EdgeType.USES_TOOL
        )
        agent_node.tools_count = tools_count

        self._nodes[agent_id] = agent_node

    def _process_version(
        self,
        agent_id: str,
        agent_name: str,
        version_data: dict,
        version_idx: int
    ) -> None:
        """
        处理Agent版本信息

        参数:
            agent_id: Agent ID
            agent_name: Agent名称
            version_data: 版本数据
            version_idx: 版本索引
        """
        version = version_data.get('version', f'v{version_idx + 1}')
        version_id = f"{agent_id}_v_{version.replace('.', '_')}"

        # 创建版本节点
        version_node = AgentNode(
            id=version_id,
            name=f"{agent_name} ({version})",
            node_type=NodeType.AGENT_VERSION,
            description=version_data.get('description', ''),
            version=version,
            status=version_data.get('status', ''),
            created_date=version_data.get('created_date', ''),
            author=version_data.get('author', ''),
            color=NODE_COLORS[NodeType.AGENT_VERSION],
            size=2,
            parent_id=agent_id,
        )

        # 处理metadata
        metadata = version_data.get('metadata', {})
        if metadata:
            # 处理tags
            tags = metadata.get('tags', [])
            version_node.tags = tags
            for tag in tags:
                self._tags.add(tag)

            # 处理支持的模型
            version_node.supported_models = metadata.get('supported_models', [])

            # 处理工具依赖
            tools_deps = metadata.get('tools_dependencies', [])
            self._process_tools_dependencies(version_id, tools_deps)

        self._nodes[version_id] = version_node

        # 创建Agent到版本的边
        edge = GraphEdge(
            id=f"edge_{agent_id}_to_{version_id}",
            source=agent_id,
            target=version_id,
            edge_type=EdgeType.HAS_VERSION,
            label=version,
            color=EDGE_COLORS[EdgeType.HAS_VERSION],
        )
        self._edges.append(edge)

    def _process_tools_dependencies(
        self,
        version_id: str,
        tools_deps: list[str]
    ) -> None:
        """
        处理工具依赖关系

        参数:
            version_id: 版本节点ID
            tools_deps: 工具依赖列表
        """
        for tool_path in tools_deps:
            tool_id = f"tool_{tool_path.replace('/', '_')}"
            tool_name = tool_path.split('/')[-1]

            # 确定工具类型
            tool_type = self._get_tool_type(tool_path)
            self._tool_types.add(tool_type)

            # 检查是否是Agent as Tool（调用其他Agent）
            is_agent_tool = self._is_agent_tool(tool_path)

            if is_agent_tool:
                # 创建Agent调用Agent的边
                target_agent_id = self._get_target_agent_id(tool_path)
                if target_agent_id:
                    edge = GraphEdge(
                        id=f"edge_{version_id}_calls_{target_agent_id}",
                        source=version_id,
                        target=target_agent_id,
                        edge_type=EdgeType.CALLS_AGENT,
                        label="calls",
                        color=EDGE_COLORS[EdgeType.CALLS_AGENT],
                        weight=2.0,
                    )
                    self._edges.append(edge)
            else:
                # 创建工具节点（如果不存在）
                if tool_id not in self._nodes:
                    tool_node = ToolNode(
                        id=tool_id,
                        name=tool_name,
                        node_type=NodeType.TOOL,
                        tool_path=tool_path,
                        tool_type=tool_type,
                        color=TOOL_TYPE_COLORS.get(tool_type, NODE_COLORS[NodeType.TOOL]),
                        size=1,
                    )
                    self._nodes[tool_id] = tool_node

                # 创建版本到工具的边
                edge = GraphEdge(
                    id=f"edge_{version_id}_uses_{tool_id}",
                    source=version_id,
                    target=tool_id,
                    edge_type=EdgeType.USES_TOOL,
                    label="uses",
                    color=EDGE_COLORS[EdgeType.USES_TOOL],
                )
                self._edges.append(edge)

    def _get_tool_type(self, tool_path: str) -> str:
        """
        获取工具类型

        参数:
            tool_path: 工具路径

        返回:
            str: 工具类型
        """
        if tool_path.startswith("strands_tools/"):
            return "strands_tools"
        elif tool_path.startswith("generated_tools/"):
            return "generated_tools"
        elif tool_path.startswith("system_tools/"):
            return "system_tools"
        elif tool_path.startswith("template_tools/"):
            return "template_tools"
        elif tool_path.startswith("mcp/"):
            return "mcp"
        else:
            return "unknown"

    def _is_agent_tool(self, tool_path: str) -> bool:
        """
        判断是否是Agent as Tool

        参数:
            tool_path: 工具路径

        返回:
            bool: 是否是Agent工具
        """
        # 检查工具路径是否指向另一个Agent
        # 例如: generated_tools/some_agent/agent_tool
        # 或者工具名称包含 "agent" 且在 generated_tools 下
        parts = tool_path.split('/')
        if len(parts) >= 2:
            # 检查是否是 agent_as_tool 模式
            if 'agent_tool' in tool_path.lower() or 'agent_as_tool' in tool_path.lower():
                return True
        return False

    def _get_target_agent_id(self, tool_path: str) -> Optional[str]:
        """
        获取目标Agent ID

        参数:
            tool_path: 工具路径

        返回:
            Optional[str]: 目标Agent ID
        """
        parts = tool_path.split('/')
        if len(parts) >= 2:
            # 假设路径格式为 generated_tools/agent_name/...
            agent_name = parts[1]
            return f"agent_{agent_name}"
        return None

    def _build_graph_data(self) -> AgentGraphData:
        """
        构建最终的图数据

        返回:
            AgentGraphData: 完整的图数据
        """
        nodes = list(self._nodes.values())

        # 统计各类型节点数量
        agent_count = sum(1 for n in nodes if isinstance(n, AgentNode) and n.node_type == NodeType.AGENT)
        version_count = sum(1 for n in nodes if isinstance(n, AgentNode) and n.node_type == NodeType.AGENT_VERSION)
        tool_count = sum(1 for n in nodes if isinstance(n, ToolNode))

        return AgentGraphData(
            nodes=nodes,
            edges=self._edges,
            agent_count=agent_count,
            version_count=version_count,
            tool_count=tool_count,
            edge_count=len(self._edges),
            categories=sorted(list(self._categories)),
            tags=sorted(list(self._tags)),
            tool_types=sorted(list(self._tool_types)),
        )

    def get_agent_details(self, agent_id: str) -> Optional[dict]:
        """
        获取Agent详细信息

        参数:
            agent_id: Agent ID

        返回:
            Optional[dict]: Agent详细信息
        """
        if agent_id in self._nodes:
            node = self._nodes[agent_id]
            if isinstance(node, AgentNode):
                # 获取相关的边
                related_edges = [
                    e.to_dict() for e in self._edges
                    if e.source == agent_id or e.target == agent_id
                ]
                result = node.to_dict()
                result['related_edges'] = related_edges
                return result
        return None

    def get_tool_details(self, tool_id: str) -> Optional[dict]:
        """
        获取工具详细信息

        参数:
            tool_id: 工具ID

        返回:
            Optional[dict]: 工具详细信息
        """
        if tool_id in self._nodes:
            node = self._nodes[tool_id]
            if isinstance(node, ToolNode):
                # 获取使用该工具的Agent
                using_agents = [
                    e.source for e in self._edges
                    if e.target == tool_id and e.edge_type == EdgeType.USES_TOOL
                ]
                result = node.to_dict()
                result['used_by'] = using_agents
                return result
        return None
