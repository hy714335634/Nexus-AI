import json
from typing import Dict, List, Optional, Any
from strands import tool

# Import the character manager from the first part
from .character_tools import _character_manager, CharacterManager

# Extend the CharacterManager class with relationship functionality
def add_relationship(self, novel_id: str, character_id: str, 
                   related_id: str, relationship_type: str, 
                   description: str = "") -> Optional[Dict[str, Any]]:
    """Add a relationship between characters.
    
    Args:
        novel_id: ID of the novel
        character_id: ID of the character
        related_id: ID of the related character
        relationship_type: Type of relationship (e.g., "ally", "enemy", "master", "disciple")
        description: Description of the relationship
        
    Returns:
        Updated character data or None if not found
    """
    character = self.get_character(novel_id, character_id)
    related = self.get_character(novel_id, related_id)
    
    if character is None or related is None:
        return None
    
    # Initialize relationships if not exist
    if "relationships" not in character:
        character["relationships"] = []
    
    # Add relationship
    relationship = {
        "character_id": related_id,
        "character_name": related["name"],
        "type": relationship_type,
        "description": description
    }
    
    # Check if relationship already exists
    for idx, rel in enumerate(character["relationships"]):
        if rel["character_id"] == related_id and rel["type"] == relationship_type:
            # Update existing relationship
            character["relationships"][idx] = relationship
            break
    else:
        # Add new relationship
        character["relationships"].append(relationship)
    
    # Save updated character
    file_path = self._get_character_path(novel_id, character_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(character, f, ensure_ascii=False, indent=2)
    
    return character

def remove_relationship(self, novel_id: str, character_id: str, 
                      related_id: str, relationship_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Remove a relationship between characters.
    
    Args:
        novel_id: ID of the novel
        character_id: ID of the character
        related_id: ID of the related character
        relationship_type: Type of relationship (optional, if not provided, all relationships with the related character will be removed)
        
    Returns:
        Updated character data or None if not found
    """
    character = self.get_character(novel_id, character_id)
    
    if character is None:
        return None
    
    # Check if relationships exist
    if "relationships" not in character:
        return character
    
    # Filter relationships
    if relationship_type:
        character["relationships"] = [
            rel for rel in character["relationships"] 
            if not (rel["character_id"] == related_id and rel["type"] == relationship_type)
        ]
    else:
        character["relationships"] = [
            rel for rel in character["relationships"] 
            if rel["character_id"] != related_id
        ]
    
    # Save updated character
    file_path = self._get_character_path(novel_id, character_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(character, f, ensure_ascii=False, indent=2)
    
    return character

def get_character_relationships(self, novel_id: str, character_id: str, 
                              relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get relationships for a character.
    
    Args:
        novel_id: ID of the novel
        character_id: ID of the character
        relationship_type: Type of relationship to filter by (optional)
        
    Returns:
        List of relationships
    """
    character = self.get_character(novel_id, character_id)
    
    if character is None or "relationships" not in character:
        return []
    
    # Filter by relationship type if provided
    if relationship_type:
        return [rel for rel in character["relationships"] if rel["type"] == relationship_type]
    
    return character["relationships"]

# Add the methods to the CharacterManager class
CharacterManager.add_relationship = add_relationship
CharacterManager.remove_relationship = remove_relationship
CharacterManager.get_character_relationships = get_character_relationships

@tool
def add_character_relationship(novel_id: str, character_id: str, 
                             related_id: str, relationship_type: str, 
                             description: str = "") -> str:
    """添加角色之间的关系。
    
    使用场景：当需要建立角色之间的关系时使用，如师徒关系、敌对关系、盟友关系等，适用于构建复杂的人物关系网络。
    建议条件：确保两个角色都存在，relationship_type应使用标准的关系类型，description可提供关系的具体细节。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
        related_id: 相关角色ID
        relationship_type: 关系类型（如"ally", "enemy", "master", "disciple"）
        description: 关系描述
    
    Returns:
        包含更新后角色数据或错误信息的JSON字符串
    """
    try:
        character = _character_manager.add_relationship(
            novel_id, character_id, related_id, relationship_type, description
        )
        if character is None:
            return json.dumps({"error": "Character not found"})
        return json.dumps(character, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def remove_character_relationship(novel_id: str, character_id: str, 
                                related_id: str, relationship_type: Optional[str] = None) -> str:
    """移除角色之间的关系。
    
    使用场景：当角色关系发生变化时使用，如关系破裂、角色死亡或故事发展需要调整关系网络。
    建议条件：如果不指定relationship_type，将移除与相关角色的所有关系；指定类型则只移除特定类型的关系。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
        related_id: 相关角色ID
        relationship_type: 关系类型（可选，如不提供则移除与相关角色的所有关系）
    
    Returns:
        包含更新后角色数据或错误信息的JSON字符串
    """
    try:
        character = _character_manager.remove_relationship(
            novel_id, character_id, related_id, relationship_type
        )
        if character is None:
            return json.dumps({"error": "Character not found"})
        return json.dumps(character, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_character_relationships(novel_id: str, character_id: str, 
                              relationship_type: Optional[str] = None) -> str:
    """获取角色的关系信息。
    
    使用场景：当需要查看角色的所有关系或特定类型的关系时使用，适用于角色分析、情节规划或关系网络梳理。
    建议条件：可指定relationship_type来筛选特定类型的关系，如不指定则返回所有关系。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
        relationship_type: 要筛选的关系类型（可选）
    
    Returns:
        包含角色关系的JSON字符串
    """
    try:
        relationships = _character_manager.get_character_relationships(
            novel_id, character_id, relationship_type
        )
        return json.dumps({"relationships": relationships}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})