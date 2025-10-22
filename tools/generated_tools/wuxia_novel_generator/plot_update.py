import json
from typing import Dict, Any
from strands import tool

# Import the plot manager from the base module
from .plot_base import _plot_manager

@tool
def update_plot(novel_id: str, updates: Dict[str, Any]) -> str:
    """更新小说的情节大纲。
    
    使用场景：当需要修改情节大纲时使用，如调整故事设定、更新主要冲突或修改主题等。
    建议条件：确保情节大纲存在，updates只包含需要更新的字段，保持故事逻辑的一致性。
    
    Args:
        novel_id: 小说ID
        updates: 要更新的数据（仅包含需要更新的字段）
    
    Returns:
        包含更新后情节数据或错误信息的JSON字符串
    """
    try:
        plot = _plot_manager.update_plot(novel_id, updates)
        if plot is None:
            return json.dumps({"error": "Plot not found"})
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def delete_plot(novel_id: str) -> str:
    """删除小说的情节大纲。
    
    使用场景：当需要删除情节大纲时使用，如重新规划故事结构或清理不需要的大纲。
    建议条件：删除前请确认该大纲没有重要的关联数据，避免影响其他相关功能。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含操作结果的JSON字符串
    """
    try:
        result = _plot_manager.delete_plot(novel_id)
        return json.dumps({"success": result})
    except Exception as e:
        return json.dumps({"error": str(e)})