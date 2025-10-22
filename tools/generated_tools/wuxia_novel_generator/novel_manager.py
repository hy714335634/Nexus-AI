import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool

class NovelManager:
    """Novel management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the novel manager."""
        self.cache_dir = cache_dir
        self.novels_dir = os.path.join(cache_dir, "novels")
        os.makedirs(self.novels_dir, exist_ok=True)
    
    def _get_novel_path(self, novel_id: str) -> str:
        """Get the path to a novel file."""
        return os.path.join(self.novels_dir, f"{novel_id}.json")
    
    def create_novel(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new novel."""
        novel_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Ensure required fields exist
        if "title" not in novel_data:
            raise ValueError("Novel must have a title")
        
        # Create novel with metadata
        novel = {
            "id": novel_id,
            "created_date": now,
            "last_updated": now,
            "status": "draft",
            **novel_data
        }
        
        # Save novel to file
        file_path = self._get_novel_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(novel, f, ensure_ascii=False, indent=2)
        
        return novel
    
    def get_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """Get a novel by ID."""
        file_path = self._get_novel_path(novel_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def update_novel(self, novel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a novel."""
        novel = self.get_novel(novel_id)
        if novel is None:
            return None
        
        # Update novel data
        novel.update(updates)
        novel["last_updated"] = datetime.now().isoformat()
        
        # Save updated novel
        file_path = self._get_novel_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(novel, f, ensure_ascii=False, indent=2)
        
        return novel
    
    def delete_novel(self, novel_id: str) -> bool:
        """Delete a novel."""
        file_path = self._get_novel_path(novel_id)
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True
    
    def list_novels(self) -> List[Dict[str, Any]]:
        """List all novels."""
        novels = []
        for filename in os.listdir(self.novels_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.novels_dir, filename), "r", encoding="utf-8") as f:
                    novels.append(json.load(f))
        
        return novels

# Initialize the novel manager
_novel_manager = NovelManager()

@tool
def create_novel(novel_data: Dict[str, Any]) -> str:
    """创建新的武侠小说项目。
    
    使用场景：当开始创作新的武侠小说时使用，适用于小说项目的初始化和基础信息设置。
    建议条件：novel_data应包含必要的小说信息，特别是title字段，其他字段可根据需要添加。
    
    Args:
        novel_data: 小说数据，包括：
            - title: 小说标题（必需）
            - author: 作者姓名
            - description: 小说简介
            - tags: 标签列表
            - language: 小说语言
            - target_audience: 目标读者群体
    
    Returns:
        包含创建小说数据和ID的JSON字符串
    """
    try:
        novel = _novel_manager.create_novel(novel_data)
        return json.dumps(novel, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_novel(novel_id: str) -> str:
    """根据ID获取小说信息。
    
    使用场景：当需要查看特定小说的详细信息时使用，适用于小说管理、信息更新或项目回顾。
    建议条件：确保novel_id有效，适用于需要获取小说基础信息的场景。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含小说数据或错误信息的JSON字符串
    """
    try:
        novel = _novel_manager.get_novel(novel_id)
        if novel is None:
            return json.dumps({"error": "Novel not found"})
        return json.dumps(novel, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def update_novel(novel_id: str, updates: Dict[str, Any]) -> str:
    """更新小说信息。
    
    使用场景：当小说信息需要修改时使用，如标题变更、描述更新、标签调整等。
    建议条件：确保小说存在，updates只包含需要更新的字段，避免覆盖不需要修改的信息。
    
    Args:
        novel_id: 小说ID
        updates: 要更新的数据（仅包含需要更新的字段）
    
    Returns:
        包含更新后小说数据或错误信息的JSON字符串
    """
    try:
        novel = _novel_manager.update_novel(novel_id, updates)
        if novel is None:
            return json.dumps({"error": "Novel not found"})
        return json.dumps(novel, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def delete_novel(novel_id: str) -> str:
    """删除小说项目。
    
    使用场景：当小说项目不再需要时使用，如项目取消、重新开始或清理不需要的作品。
    建议条件：删除前请确认该小说没有重要的关联数据，避免影响其他相关功能。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含操作结果的JSON字符串
    """
    try:
        result = _novel_manager.delete_novel(novel_id)
        return json.dumps({"success": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def list_novels() -> str:
    """列出所有小说项目。
    
    使用场景：当需要查看所有小说项目概览时使用，适用于项目管理、作品回顾或选择特定项目。
    建议条件：适用于需要管理多个小说项目的场景，可帮助了解当前所有作品的状态。
    
    Returns:
        包含小说列表的JSON字符串
    """
    try:
        novels = _novel_manager.list_novels()
        return json.dumps({"novels": novels}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})