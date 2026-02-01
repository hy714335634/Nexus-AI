"""
Agent Graph API 路由

提供Agent关系图数据的API端点
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from nexus_utils.agent_graph import AgentGraphLoader

router = APIRouter(prefix="/agent-graph", tags=["Agent Graph"])


@router.get("")
async def get_agent_graph(
    include_tools: bool = Query(True, description="是否包含工具节点"),
    include_versions: bool = Query(True, description="是否包含版本节点"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    tool_type: Optional[str] = Query(None, description="按工具类型筛选"),
):
    """
    获取Agent关系图数据

    返回所有Agent、工具及其关系的图数据，支持筛选
    """
    try:
        loader = AgentGraphLoader()
        graph_data = loader.load_all_agents()

        # 转换为字典
        result = graph_data.to_dict()

        # 应用筛选
        if not include_tools:
            result["nodes"] = [
                n for n in result["nodes"]
                if n["type"] not in ["tool", "tool_group"]
            ]
            result["edges"] = [
                e for e in result["edges"]
                if e["type"] != "uses_tool"
            ]

        if not include_versions:
            result["nodes"] = [
                n for n in result["nodes"]
                if n["type"] != "agent_version"
            ]
            result["edges"] = [
                e for e in result["edges"]
                if e["type"] != "has_version"
            ]

        if category:
            # 筛选指定分类的Agent及其相关节点
            agent_ids = {
                n["id"] for n in result["nodes"]
                if n.get("category") == category
            }
            # 包含版本节点
            version_ids = {
                n["id"] for n in result["nodes"]
                if n.get("parent_id") in agent_ids
            }
            # 获取相关工具
            tool_ids = {
                e["target"] for e in result["edges"]
                if e["source"] in (agent_ids | version_ids) and e["type"] == "uses_tool"
            }
            all_ids = agent_ids | version_ids | tool_ids
            result["nodes"] = [n for n in result["nodes"] if n["id"] in all_ids]
            result["edges"] = [
                e for e in result["edges"]
                if e["source"] in all_ids and e["target"] in all_ids
            ]

        if tag:
            # 筛选包含指定标签的节点
            tagged_ids = {
                n["id"] for n in result["nodes"]
                if tag in n.get("tags", [])
            }
            # 包含父Agent
            parent_ids = {
                n.get("parent_id") for n in result["nodes"]
                if n["id"] in tagged_ids and n.get("parent_id")
            }
            # 获取相关工具
            tool_ids = {
                e["target"] for e in result["edges"]
                if e["source"] in tagged_ids and e["type"] == "uses_tool"
            }
            all_ids = tagged_ids | parent_ids | tool_ids
            result["nodes"] = [n for n in result["nodes"] if n["id"] in all_ids]
            result["edges"] = [
                e for e in result["edges"]
                if e["source"] in all_ids and e["target"] in all_ids
            ]

        if tool_type:
            # 筛选指定类型的工具
            tool_ids = {
                n["id"] for n in result["nodes"]
                if n.get("tool_type") == tool_type
            }
            # 获取使用这些工具的Agent
            agent_ids = {
                e["source"] for e in result["edges"]
                if e["target"] in tool_ids and e["type"] == "uses_tool"
            }
            # 获取父Agent
            parent_ids = {
                n.get("parent_id") for n in result["nodes"]
                if n["id"] in agent_ids and n.get("parent_id")
            }
            all_ids = tool_ids | agent_ids | parent_ids
            result["nodes"] = [n for n in result["nodes"] if n["id"] in all_ids]
            result["edges"] = [
                e for e in result["edges"]
                if e["source"] in all_ids and e["target"] in all_ids
            ]

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_id}")
async def get_node_details(node_id: str):
    """
    获取节点详细信息

    参数:
        node_id: 节点ID
    """
    try:
        loader = AgentGraphLoader()
        loader.load_all_agents()

        # 尝试获取Agent详情
        details = loader.get_agent_details(node_id)
        if details:
            return {"success": True, "data": details}

        # 尝试获取工具详情
        details = loader.get_tool_details(node_id)
        if details:
            return {"success": True, "data": details}

        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats():
    """
    获取图统计信息
    """
    try:
        loader = AgentGraphLoader()
        graph_data = loader.load_all_agents()

        return {
            "success": True,
            "data": {
                "stats": {
                    "agent_count": graph_data.agent_count,
                    "version_count": graph_data.version_count,
                    "tool_count": graph_data.tool_count,
                    "edge_count": graph_data.edge_count,
                },
                "filters": {
                    "categories": graph_data.categories,
                    "tags": graph_data.tags,
                    "tool_types": graph_data.tool_types,
                },
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
