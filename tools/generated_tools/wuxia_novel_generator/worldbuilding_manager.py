import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool

class WorldbuildingManager:
    """Worldbuilding management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the worldbuilding manager."""
        self.cache_dir = cache_dir
        self.world_dir = os.path.join(cache_dir, "worldbuilding")
        os.makedirs(self.world_dir, exist_ok=True)
    
    def _get_world_path(self, novel_id: str) -> str:
        """Get the path to a worldbuilding file."""
        return os.path.join(self.world_dir, f"{novel_id}.json")
    
    def get_world(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """Get worldbuilding data by novel ID."""
        file_path = self._get_world_path(novel_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def create_or_update_world(self, novel_id: str, world_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update worldbuilding data."""
        now = datetime.now().isoformat()
        
        # Check if worldbuilding data already exists
        existing_world = self.get_world(novel_id)
        
        if existing_world:
            # Update existing worldbuilding data
            world = {
                **existing_world,
                **world_data,
                "last_updated": now
            }
        else:
            # Create new worldbuilding data
            world = {
                "novel_id": novel_id,
                "created_date": now,
                "last_updated": now,
                **world_data
            }
        
        # Save worldbuilding data to file
        file_path = self._get_world_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(world, f, ensure_ascii=False, indent=2)
        
        return world
    
    def add_location(self, novel_id: str, location_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a location to worldbuilding data."""
        world = self.get_world(novel_id)
        if world is None:
            world = {"novel_id": novel_id}
        
        # Initialize locations if not exist
        if "locations" not in world:
            world["locations"] = []
        
        # Generate location ID if not provided
        if "id" not in location_data:
            location_data["id"] = str(uuid.uuid4())
        
        # Add creation timestamp
        location_data["created_date"] = datetime.now().isoformat()
        
        # Add location
        world["locations"].append(location_data)
        
        # Update worldbuilding data
        world["last_updated"] = datetime.now().isoformat()
        
        # Save updated worldbuilding data
        file_path = self._get_world_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(world, f, ensure_ascii=False, indent=2)
        
        return world
    
    def add_faction(self, novel_id: str, faction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a faction to worldbuilding data."""
        world = self.get_world(novel_id)
        if world is None:
            world = {"novel_id": novel_id}
        
        # Initialize factions if not exist
        if "factions" not in world:
            world["factions"] = []
        
        # Generate faction ID if not provided
        if "id" not in faction_data:
            faction_data["id"] = str(uuid.uuid4())
        
        # Add creation timestamp
        faction_data["created_date"] = datetime.now().isoformat()
        
        # Add faction
        world["factions"].append(faction_data)
        
        # Update worldbuilding data
        world["last_updated"] = datetime.now().isoformat()
        
        # Save updated worldbuilding data
        file_path = self._get_world_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(world, f, ensure_ascii=False, indent=2)
        
        return world
    
    def add_martial_art(self, novel_id: str, martial_art_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a martial art to worldbuilding data."""
        world = self.get_world(novel_id)
        if world is None:
            world = {"novel_id": novel_id}
        
        # Initialize martial_arts if not exist
        if "martial_arts" not in world:
            world["martial_arts"] = []
        
        # Generate martial art ID if not provided
        if "id" not in martial_art_data:
            martial_art_data["id"] = str(uuid.uuid4())
        
        # Add creation timestamp
        martial_art_data["created_date"] = datetime.now().isoformat()
        
        # Add martial art
        world["martial_arts"].append(martial_art_data)
        
        # Update worldbuilding data
        world["last_updated"] = datetime.now().isoformat()
        
        # Save updated worldbuilding data
        file_path = self._get_world_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(world, f, ensure_ascii=False, indent=2)
        
        return world

# Initialize the worldbuilding manager
_world_manager = WorldbuildingManager()

@tool
def get_world(novel_id: str) -> str:
    """获取武侠小说的世界观构建数据。
    
    使用场景：当需要查看小说的世界观构建数据时使用，适用于世界设定回顾、元素查询或世界观完善。
    建议条件：确保novel_id有效，适用于需要了解小说世界设定的场景。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含世界观构建数据或错误信息的JSON字符串
    """
    try:
        world = _world_manager.get_world(novel_id)
        if world is None:
            return json.dumps({"error": "Worldbuilding data not found"})
        return json.dumps(world, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def create_or_update_world(novel_id: str, world_data: Dict[str, Any]) -> str:
    """创建或更新武侠小说的世界观构建数据。
    
    使用场景：当需要为小说创建世界观或更新现有世界观时使用，适用于世界设定、背景构建或世界观完善。
    建议条件：world_data应包含完整的世界观要素，如背景设定、时间背景、武功体系等，确保逻辑一致。
    
    Args:
        novel_id: 小说ID
        world_data: 世界观构建数据，包括：
            - setting: 总体背景设定描述
            - time_period: 世界时间背景
            - magic_system: 武功/内力体系描述
            - cosmology: 世界宇宙观描述
            - cultural_elements: 文化元素列表
            - historical_events: 历史事件列表
            - locations: 地点列表（可选）
            - factions: 势力列表（可选）
            - martial_arts: 武功列表（可选）
    
    Returns:
        包含创建/更新世界观构建数据的JSON字符串
    """
    try:
        world = _world_manager.create_or_update_world(novel_id, world_data)
        return json.dumps(world, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})