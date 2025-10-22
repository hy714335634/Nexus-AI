import json
import os
import uuid
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from strands import tool

class CharacterManager:
    """Character management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the character manager.
        
        Args:
            cache_dir: Directory to store character data
        """
        self.cache_dir = cache_dir
        self.characters_dir = os.path.join(cache_dir, "characters")
        os.makedirs(self.characters_dir, exist_ok=True)
    
    def _get_character_path(self, novel_id: str, character_id: str) -> str:
        """Get the path to a character file.
        
        Args:
            novel_id: ID of the novel
            character_id: ID of the character
            
        Returns:
            Path to the character file
        """
        novel_dir = os.path.join(self.characters_dir, novel_id)
        os.makedirs(novel_dir, exist_ok=True)
        return os.path.join(novel_dir, f"{character_id}.json")
    
    def create_character(self, novel_id: str, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new character.
        
        Args:
            novel_id: ID of the novel
            character_data: Character data
            
        Returns:
            Created character data with ID
        """
        character_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Ensure required fields exist
        if "name" not in character_data:
            raise ValueError("Character must have a name")
        
        # Create character with metadata
        character = {
            "id": character_id,
            "created_date": now,
            "last_updated": now,
            **character_data
        }
        
        # Save character to file
        file_path = self._get_character_path(novel_id, character_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(character, f, ensure_ascii=False, indent=2)
        
        return character
    
    def get_character(self, novel_id: str, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a character by ID.
        
        Args:
            novel_id: ID of the novel
            character_id: ID of the character
            
        Returns:
            Character data or None if not found
        """
        file_path = self._get_character_path(novel_id, character_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def update_character(self, novel_id: str, character_id: str, 
                        updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a character.
        
        Args:
            novel_id: ID of the novel
            character_id: ID of the character
            updates: Data to update
            
        Returns:
            Updated character data or None if not found
        """
        character = self.get_character(novel_id, character_id)
        if character is None:
            return None
        
        # Update character data
        character.update(updates)
        character["last_updated"] = datetime.now().isoformat()
        
        # Save updated character
        file_path = self._get_character_path(novel_id, character_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(character, f, ensure_ascii=False, indent=2)
        
        return character
    
    def delete_character(self, novel_id: str, character_id: str) -> bool:
        """Delete a character.
        
        Args:
            novel_id: ID of the novel
            character_id: ID of the character
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_character_path(novel_id, character_id)
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True
    
    def list_characters(self, novel_id: str) -> List[Dict[str, Any]]:
        """List all characters in a novel.
        
        Args:
            novel_id: ID of the novel
            
        Returns:
            List of character data
        """
        novel_dir = os.path.join(self.characters_dir, novel_id)
        if not os.path.exists(novel_dir):
            return []
        
        characters = []
        for filename in os.listdir(novel_dir):
            if filename.endswith(".json"):
                with open(os.path.join(novel_dir, filename), "r", encoding="utf-8") as f:
                    characters.append(json.load(f))
        
        return characters
    
    def search_characters(self, novel_id: str, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search characters based on criteria.
        
        Args:
            novel_id: ID of the novel
            criteria: Search criteria (e.g., {"faction": "Shaolin"})
            
        Returns:
            List of matching character data
        """
        all_characters = self.list_characters(novel_id)
        
        # Filter characters based on criteria
        results = []
        for character in all_characters:
            matches = True
            for key, value in criteria.items():
                # Handle nested fields with dot notation (e.g., "relationships.allies")
                if "." in key:
                    parts = key.split(".")
                    char_value = character
                    for part in parts:
                        if part in char_value:
                            char_value = char_value[part]
                        else:
                            matches = False
                            break
                    
                    # Check if the final value matches
                    if matches and char_value != value:
                        matches = False
                
                # Handle direct field match
                elif key not in character or character[key] != value:
                    matches = False
            
            if matches:
                results.append(character)
        
        return results
    
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
        
        character["relationships"].append(relationship)
        
        # Save updated character
        file_path = self._get_character_path(novel_id, character_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(character, f, ensure_ascii=False, indent=2)
        
        return character


# Initialize the character manager
_character_manager = CharacterManager()

@tool
def create_character(novel_id: str, character_data: Dict[str, Any]) -> str:
    """创建武侠小说中的新角色。
    
    使用场景：当需要为武侠小说添加新角色时使用，适用于小说创作初期建立角色体系或故事发展中引入新人物。
    建议条件：确保novel_id有效且character_data包含必要的角色信息。
    
    Args:
        novel_id: 小说ID
        character_data: 角色数据，包括：
            - name: 角色姓名（必需）
            - gender: 角色性别
            - age: 角色年龄
            - faction: 角色所属门派或势力
            - martial_arts: 角色掌握的武功列表
            - personality: 角色性格特征列表
            - background: 角色背景故事
            - status: 角色状态（如"alive", "dead"）
            - appearance: 角色外貌描述
            - 其他需要的字段
    
    Returns:
        包含创建角色数据和ID的JSON字符串
    """
    try:
        character = _character_manager.create_character(novel_id, character_data)
        return json.dumps(character, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_character(novel_id: str, character_id: str) -> str:
    """根据ID获取角色信息。
    
    使用场景：当需要查看特定角色的详细信息时使用，适用于角色关系建立、情节发展或角色信息更新前的查询。
    建议条件：确保novel_id和character_id都存在且有效。
    
    Args:
        novel_id: 小说ID
        character_id: 角色ID
    
    Returns:
        包含角色数据或错误信息的JSON字符串
    """
    try:
        character = _character_manager.get_character(novel_id, character_id)
        if character is None:
            return json.dumps({"error": "Character not found"})
        return json.dumps(character, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

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
    建议条件：criteria应包含明确的搜索条件，支持嵌套字段的点号表示法，适用于角色数量较多时的精确查找。
    
    Args:
        novel_id: 小说ID
        criteria: 搜索条件（如{"faction": "Shaolin", "age": 25}）
                 支持嵌套字段的点号表示法（如{"relationships.type": "master"}）
    
    Returns:
        包含匹配角色的JSON字符串
    """
    try:
        characters = _character_manager.search_characters(novel_id, criteria)
        return json.dumps({"characters": characters}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

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