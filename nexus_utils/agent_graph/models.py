"""
Agent Graph 数据模型

定义图数据结构，包括节点、边和图数据
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(str, Enum):
    """节点类型枚举"""
    AGENT = "agent"
    AGENT_VERSION = "agent_version"
    TOOL = "tool"
    TOOL_GROUP = "tool_group"  # 工具组（如strands_tools）


class EdgeType(str, Enum):
    """边类型枚举"""
    USES_TOOL = "uses_tool"           # Agent使用工具
    HAS_VERSION = "has_version"       # Agent有版本
    CALLS_AGENT = "calls_agent"       # Agent调用Agent（Agent as Tool）
    BELONGS_TO = "belongs_to"         # 工具属于工具组
    AGENT_AS_TOOL = "agent_as_tool"   # Agent被封装为工具


@dataclass
class AgentNode:
    """Agent节点"""
    id: str
    name: str
    node_type: NodeType
    description: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    version: str = ""
    status: str = ""
    created_date: str = ""
    author: str = ""
    # Agent特有属性
    supported_models: list[str] = field(default_factory=list)
    tools_count: int = 0
    # 用于可视化
    color: str = ""
    size: int = 1
    # 父Agent ID（用于版本节点）
    parent_id: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "version": self.version,
            "status": self.status,
            "created_date": self.created_date,
            "author": self.author,
            "supported_models": self.supported_models,
            "tools_count": self.tools_count,
            "color": self.color,
            "size": self.size,
            "parent_id": self.parent_id,
        }


@dataclass
class ToolNode:
    """工具节点"""
    id: str
    name: str
    node_type: NodeType
    tool_path: str = ""
    tool_type: str = ""  # strands_tools, generated_tools, system_tools, template_tools
    description: str = ""
    # 用于可视化
    color: str = ""
    size: int = 1
    # 父工具组ID
    parent_id: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "tool_path": self.tool_path,
            "tool_type": self.tool_type,
            "description": self.description,
            "color": self.color,
            "size": self.size,
            "parent_id": self.parent_id,
        }


@dataclass
class GraphEdge:
    """图边"""
    id: str
    source: str
    target: str
    edge_type: EdgeType
    label: str = ""
    weight: float = 1.0
    # 用于可视化
    color: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.edge_type.value,
            "label": self.label,
            "weight": self.weight,
            "color": self.color,
        }


@dataclass
class AgentGraphData:
    """完整的图数据"""
    nodes: list[AgentNode | ToolNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    # 统计信息
    agent_count: int = 0
    version_count: int = 0
    tool_count: int = 0
    edge_count: int = 0
    # 分类信息
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    tool_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "agent_count": self.agent_count,
                "version_count": self.version_count,
                "tool_count": self.tool_count,
                "edge_count": self.edge_count,
            },
            "filters": {
                "categories": self.categories,
                "tags": self.tags,
                "tool_types": self.tool_types,
            },
        }
