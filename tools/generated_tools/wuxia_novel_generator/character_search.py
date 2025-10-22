import json
from typing import Dict, List, Any
from strands import tool

# Import the character manager from the first part
from .character_tools import _character_manager

@tool
def list_characters(novel_id: str) -> str:
    """列出小说中的所有角色。
    
    使用场景：当需要查看小说中所有角色概览时使用，适用于角色管理、关系梳理或故事规划。
    建议条件：确保novel_id有效，适用于角色数量较多需要统一管理的情况。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含角色列表的JSON字符串
    """
    try:
        characters = _character_manager.list_characters(novel_id)
        return json.dumps({"characters": characters}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def search_characters(novel_id: str, criteria: Dict[str, Any]) -> str:
    """根据条件搜索角色。
    
    使用场景：当需要根据特定条件查找角色时使用，如查找特定门派、年龄范围或关系类型的角色。
    建议条件：criteria应包含明确的搜索条件，适用于角色数量较多时的精确查找。
    
    Args:
        novel_id: 小说ID
        criteria: 搜索条件（如{"faction": "Shaolin", "age": 25}）
    
    Returns:
        包含匹配角色的JSON字符串
    """
    try:
        characters = _character_manager.search_characters(novel_id, criteria)
        return json.dumps({"characters": characters}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})