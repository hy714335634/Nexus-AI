import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool

class CharacterManager:
    """Character management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the character manager."""
        self.cache_dir = cache_dir
        self.characters_dir = os.path.join(cache_dir, "characters")
        os.makedirs(self.characters_dir, exist_ok=True)
    
    def _get_character_path(self, novel_id: str, character_id: str) -> str:
        """Get the path to a character file."""
        novel_dir = os.path.join(self.characters_dir, novel_id)
        os.makedirs(novel_dir, exist_ok=True)
        return os.path.join(novel_dir, f"{character_id}.json")
    
    def create_character(self, novel_id: str, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new character."""
        character_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if "name" not in character_data:
            raise ValueError("Character must have a name")
        
        character = {
            "id": character_id,
            "created_date": now,
            "last_updated": now,
            **character_data
        }
        
        file_path = self._get_character_path(novel_id, character_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(character, f, ensure_ascii=False, indent=2)
        
        return character
    
    def get_character(self, novel_id: str, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a character by ID."""
        file_path = self._get_character_path(novel_id, character_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def update_character(self, novel_id: str, character_id: str, 
                        updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a character."""
        character = self.get_character(novel_id, character_id)
        if character is None:
            return None
        
        character.update(updates)
        character["last_updated"] = datetime.now().isoformat()
        
        file_path = self._get_character_path(novel_id, character_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(character, f, ensure_ascii=False, indent=2)
        
        return character
    
    def delete_character(self, novel_id: str, character_id: str) -> bool:
        """Delete a character."""
        file_path = self._get_character_path(novel_id, character_id)
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True
    
    def list_characters(self, novel_id: str) -> List[Dict[str, Any]]:
        """List all characters in a novel."""
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
        """Search characters based on criteria."""
        all_characters = self.list_characters(novel_id)
        
        results = []
        for character in all_characters:
            matches = True
            for key, value in criteria.items():
                if key not in character or character[key] != value:
                    matches = False
                    break
            
            if matches:
                results.append(character)
        
        return results

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