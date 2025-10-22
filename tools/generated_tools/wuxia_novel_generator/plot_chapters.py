import json
import uuid
from typing import Dict, Optional, Any
from datetime import datetime
from strands import tool

# Import the plot manager from the base module
from .plot_base import _plot_manager, PlotManager

# Extend PlotManager with chapter management methods
def add_chapter(self, novel_id: str, chapter_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Add a chapter to a plot."""
    plot = self.get_plot(novel_id)
    if plot is None:
        return None
    
    # Initialize chapters if not exist
    if "chapters" not in plot:
        plot["chapters"] = []
    
    # Generate chapter ID if not provided
    if "id" not in chapter_data:
        chapter_data["id"] = str(uuid.uuid4())
    
    # Set chapter number if not provided
    if "number" not in chapter_data:
        chapter_data["number"] = len(plot["chapters"]) + 1
    
    # Add creation timestamp
    chapter_data["created_date"] = datetime.now().isoformat()
    
    # Add chapter
    plot["chapters"].append(chapter_data)
    
    # Update plot
    plot["last_updated"] = datetime.now().isoformat()
    
    # Save updated plot
    file_path = self._get_plot_path(novel_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(plot, f, ensure_ascii=False, indent=2)
    
    return plot

def update_chapter(self, novel_id: str, chapter_id: str, 
                 updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a chapter in a plot."""
    plot = self.get_plot(novel_id)
    if plot is None or "chapters" not in plot:
        return None
    
    # Find chapter
    chapter_index = -1
    for i, chapter in enumerate(plot["chapters"]):
        if chapter.get("id") == chapter_id:
            chapter_index = i
            break
    
    if chapter_index == -1:
        return None
    
    # Update chapter
    plot["chapters"][chapter_index].update(updates)
    
    # Update plot
    plot["last_updated"] = datetime.now().isoformat()
    
    # Save updated plot
    file_path = self._get_plot_path(novel_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(plot, f, ensure_ascii=False, indent=2)
    
    return plot

def delete_chapter(self, novel_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
    """Delete a chapter from a plot."""
    plot = self.get_plot(novel_id)
    if plot is None or "chapters" not in plot:
        return None
    
    # Filter out chapter
    original_length = len(plot["chapters"])
    plot["chapters"] = [ch for ch in plot["chapters"] if ch.get("id") != chapter_id]
    
    # Check if chapter was found and deleted
    if len(plot["chapters"]) == original_length:
        return None
    
    # Update plot
    plot["last_updated"] = datetime.now().isoformat()
    
    # Save updated plot
    file_path = self._get_plot_path(novel_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(plot, f, ensure_ascii=False, indent=2)
    
    return plot

# Add the methods to the PlotManager class
PlotManager.add_chapter = add_chapter
PlotManager.update_chapter = update_chapter
PlotManager.delete_chapter = delete_chapter

@tool
def add_chapter(novel_id: str, chapter_data: Dict[str, Any]) -> str:
    """向小说情节大纲添加章节。
    
    使用场景：当需要在情节大纲中添加新章节时使用，适用于故事扩展、情节细化或结构完善。
    建议条件：chapter_data应包含章节的基本信息，如标题、概要、视角角色等，确保与整体情节连贯。
    
    Args:
        novel_id: 小说ID
        chapter_data: 章节数据，包括：
            - title: 章节标题
            - synopsis: 章节概要
            - pov_character: 视角角色ID或姓名
            - events: 章节中的事件列表
            - locations: 章节中的地点列表
            - characters: 章节中涉及的角色ID列表
    
    Returns:
        包含更新后情节数据或错误信息的JSON字符串
    """
    try:
        plot = _plot_manager.add_chapter(novel_id, chapter_data)
        if plot is None:
            return json.dumps({"error": "Plot not found"})
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def update_chapter(novel_id: str, chapter_id: str, updates: Dict[str, Any]) -> str:
    """更新小说情节大纲中的章节信息。
    
    使用场景：当需要修改章节信息时使用，如调整章节内容、更新事件安排或修改角色参与情况。
    建议条件：确保章节存在，updates只包含需要更新的字段，保持与整体情节的一致性。
    
    Args:
        novel_id: 小说ID
        chapter_id: 章节ID
        updates: 要更新的数据（仅包含需要更新的字段）
    
    Returns:
        包含更新后情节数据或错误信息的JSON字符串
    """
    try:
        plot = _plot_manager.update_chapter(novel_id, chapter_id, updates)
        if plot is None:
            return json.dumps({"error": "Plot or chapter not found"})
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def delete_chapter(novel_id: str, chapter_id: str) -> str:
    """从小说情节大纲中删除章节。
    
    使用场景：当需要删除不需要的章节时使用，如情节调整、结构优化或内容精简。
    建议条件：删除前请确认该章节没有重要的情节依赖，避免影响故事连贯性。
    
    Args:
        novel_id: 小说ID
        chapter_id: 章节ID
    
    Returns:
        包含更新后情节数据或错误信息的JSON字符串
    """
    try:
        plot = _plot_manager.delete_chapter(novel_id, chapter_id)
        if plot is None:
            return json.dumps({"error": "Plot or chapter not found"})
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})