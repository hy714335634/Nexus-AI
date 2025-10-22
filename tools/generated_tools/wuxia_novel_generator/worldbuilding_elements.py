import json
from typing import Dict, Any
from strands import tool

# Import the worldbuilding manager from the first part
from .worldbuilding_manager import _world_manager

@tool
def add_location(novel_id: str, location_data: Dict[str, Any]) -> str:
    """向小说的世界观构建数据中添加地点。
    
    使用场景：当需要为小说世界添加新地点时使用，适用于世界构建、场景设定或故事环境扩展。
    建议条件：location_data应包含地点的详细信息，如名称、类型、描述等，确保与整体世界观一致。
    
    Args:
        novel_id: 小说ID
        location_data: 地点数据，包括：
            - name: 地点名称
            - type: 地点类型（如"city", "mountain", "temple"）
            - description: 地点描述
            - significance: 地点对故事的重要性
            - inhabitants: 重要居民
            - features: 地点特色
    
    Returns:
        包含更新后世界观构建数据或错误信息的JSON字符串
    """
    try:
        world = _world_manager.add_location(novel_id, location_data)
        return json.dumps(world, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def add_faction(novel_id: str, faction_data: Dict[str, Any]) -> str:
    """向小说的世界观构建数据中添加势力。
    
    使用场景：当需要为小说世界添加新势力时使用，适用于门派设定、政治体系构建或势力关系建立。
    建议条件：faction_data应包含势力的详细信息，如名称、类型、理念等，确保与整体世界观协调。
    
    Args:
        novel_id: 小说ID
        faction_data: 势力数据，包括：
            - name: 势力名称
            - type: 势力类型（如"martial sect", "imperial court", "bandit group"）
            - description: 势力描述
            - leadership: 领导结构
            - philosophy: 势力理念或信仰
            - strengths: 势力优势
            - weaknesses: 势力弱点
            - notable_members: 重要成员
            - relationships: 与其他势力的关系
    
    Returns:
        包含更新后世界观构建数据或错误信息的JSON字符串
    """
    try:
        world = _world_manager.add_faction(novel_id, faction_data)
        return json.dumps(world, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def add_martial_art(novel_id: str, martial_art_data: Dict[str, Any]) -> str:
    """向小说的世界观构建数据中添加武功。
    
    使用场景：当需要为小说世界添加新武功时使用，适用于武功体系构建、门派特色设定或战斗系统设计。
    建议条件：martial_art_data应包含武功的详细信息，如名称、类型、特点等，确保与整体武功体系协调。
    
    Args:
        novel_id: 小说ID
        martial_art_data: 武功数据，包括：
            - name: 武功名称
            - type: 武功类型（如"internal", "external", "weapon-based"）
            - description: 武功描述
            - origin: 武功起源
            - techniques: 重要招式
            - requirements: 学习要求
            - strengths: 武功优势
            - weaknesses: 武功弱点
            - famous_practitioners: 著名修炼者
            - associated_faction: 关联势力（如有）
    
    Returns:
        包含更新后世界观构建数据或错误信息的JSON字符串
    """
    try:
        world = _world_manager.add_martial_art(novel_id, martial_art_data)
        return json.dumps(world, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})