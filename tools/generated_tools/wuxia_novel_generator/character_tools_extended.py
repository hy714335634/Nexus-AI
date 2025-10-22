import json
import os
from typing import Dict, List, Optional, Any
from strands import tool

# Import the character manager from the first part
from .character_tools import _character_manager

@tool
def update_character(novel_id: str, character_id: str, updates: Dict[str, Any]) -> str:
    """更新角色信息。
    
    使用场景：当角色信息发生变化时使用，如角色成长、状态改变、新技能习得或背景故事补充。
    建议条件：确保角色存在，updates只包含需要更新的字段，避免覆盖不需要修改的信息。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
        updates: 要更新的数据（仅包含需要更新的字段）
    
    Returns:
        包含更新后角色数据或错误信息的JSON字符串
    """
    try:
        character = _character_manager.update_character(novel_id, character_id, updates)
        if character is None:
            return json.dumps({"error": "Character not found"})
        return json.dumps(character, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def delete_character(novel_id: str, character_id: str) -> str:
    """删除角色。
    
    使用场景：当角色不再需要时使用，如角色死亡、故事线结束或角色设计需要重新开始。
    建议条件：删除前请确认该角色没有重要的关系或情节依赖，避免影响故事完整性。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
    
    Returns:
        包含操作结果的JSON字符串
    """
    try:
        result = _character_manager.delete_character(novel_id, character_id)
        return json.dumps({"success": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

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