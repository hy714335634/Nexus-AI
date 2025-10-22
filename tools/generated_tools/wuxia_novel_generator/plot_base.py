import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool

class PlotManager:
    """Plot management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the plot manager."""
        self.cache_dir = cache_dir
        self.plots_dir = os.path.join(cache_dir, "plots")
        os.makedirs(self.plots_dir, exist_ok=True)
    
    def _get_plot_path(self, novel_id: str) -> str:
        """Get the path to a plot file."""
        return os.path.join(self.plots_dir, f"{novel_id}.json")
    
    def create_plot(self, novel_id: str, plot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new plot or update existing one."""
        now = datetime.now().isoformat()
        
        # Check if plot already exists
        existing_plot = self.get_plot(novel_id)
        
        if existing_plot:
            # Update existing plot
            plot = {
                **existing_plot,
                **plot_data,
                "last_updated": now
            }
        else:
            # Create new plot
            plot = {
                "novel_id": novel_id,
                "created_date": now,
                "last_updated": now,
                **plot_data
            }
        
        # Save plot to file
        file_path = self._get_plot_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plot, f, ensure_ascii=False, indent=2)
        
        return plot
    
    def get_plot(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """Get a plot by novel ID."""
        file_path = self._get_plot_path(novel_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def update_plot(self, novel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a plot."""
        plot = self.get_plot(novel_id)
        if plot is None:
            return None
        
        # Update plot data
        plot.update(updates)
        plot["last_updated"] = datetime.now().isoformat()
        
        # Save updated plot
        file_path = self._get_plot_path(novel_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plot, f, ensure_ascii=False, indent=2)
        
        return plot
    
    def delete_plot(self, novel_id: str) -> bool:
        """Delete a plot."""
        file_path = self._get_plot_path(novel_id)
        if not os.path.exists(file_path):
            return False
        
        os.remove(file_path)
        return True

# Initialize the plot manager
_plot_manager = PlotManager()

@tool
def create_plot(novel_id: str, plot_data: Dict[str, Any]) -> str:
    """创建或更新武侠小说的情节大纲。
    
    使用场景：当需要为小说创建情节大纲或更新现有大纲时使用，适用于故事规划、情节设计和结构安排。
    建议条件：plot_data应包含完整的故事要素，如背景设定、主要冲突、主题等，章节大纲可选。
    
    Args:
        novel_id: 小说ID
        plot_data: 情节数据，包括：
            - title: 小说标题
            - setting: 小说背景设定描述
            - time_period: 故事时间背景
            - main_conflict: 主要冲突
            - themes: 主题列表
            - synopsis: 故事简介
            - chapters: 章节大纲列表（可选）
    
    Returns:
        包含创建/更新情节数据的JSON字符串
    """
    try:
        plot = _plot_manager.create_plot(novel_id, plot_data)
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_plot(novel_id: str) -> str:
    """根据小说ID获取情节大纲。
    
    使用场景：当需要查看小说的情节大纲时使用，适用于故事回顾、情节分析或大纲修改前的查询。
    建议条件：确保novel_id有效，适用于需要了解故事结构和情节安排的场景。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含情节数据或错误信息的JSON字符串
    """
    try:
        plot = _plot_manager.get_plot(novel_id)
        if plot is None:
            return json.dumps({"error": "Plot not found"})
        return json.dumps(plot, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})