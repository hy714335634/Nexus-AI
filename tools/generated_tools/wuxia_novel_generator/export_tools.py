import json
import os
import boto3
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool

# Import managers from other modules
from .novel_manager import _novel_manager
from .plot_base import _plot_manager
from .content_generator import _content_generator

class ExportManager:
    """Export management system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the export manager."""
        self.cache_dir = cache_dir
        self.exports_dir = os.path.join(cache_dir, "exports")
        os.makedirs(self.exports_dir, exist_ok=True)
    
    def _get_export_path(self, novel_id: str, format: str) -> str:
        """Get the path to an export file."""
        return os.path.join(self.exports_dir, f"{novel_id}.{format}")
    
    def export_to_markdown(self, novel_id: str) -> Optional[str]:
        """Export a novel to markdown format."""
        # Get novel data
        novel = _novel_manager.get_novel(novel_id)
        if novel is None:
            return None
        
        # Get plot data
        plot = _plot_manager.get_plot(novel_id)
        if plot is None or "chapters" not in plot:
            return None
        
        # Start building markdown content
        markdown = f"# {novel.get('title', 'Untitled Novel')}\n\n"
        markdown += f"*By {novel.get('author', 'Anonymous')}*\n\n"
        
        if "description" in novel:
            markdown += f"## Description\n\n{novel['description']}\n\n"
        
        # Add chapters
        for chapter in sorted(plot["chapters"], key=lambda x: x.get("number", 999)):
            chapter_id = chapter.get("id")
            chapter_title = chapter.get("title", f"Chapter {chapter.get('number', '?')}")
            
            markdown += f"## {chapter_title}\n\n"
            
            # Get chapter content
            content = _content_generator.get_chapter_content(novel_id, chapter_id)
            if content and "content" in content:
                markdown += f"{content['content']}\n\n"
            else:
                markdown += "*Chapter content not available*\n\n"
        
        # Save to file
        export_path = self._get_export_path(novel_id, "md")
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return export_path
    
    def export_to_json(self, novel_id: str) -> Optional[str]:
        """Export a novel to JSON format."""
        # Get novel data
        novel = _novel_manager.get_novel(novel_id)
        if novel is None:
            return None
        
        # Get plot data
        plot = _plot_manager.get_plot(novel_id)
        
        # Prepare export data
        export_data = {
            "novel": novel,
            "plot": plot,
            "chapters": []
        }
        
        # Add chapter content
        if plot and "chapters" in plot:
            for chapter in plot["chapters"]:
                chapter_id = chapter.get("id")
                content = _content_generator.get_chapter_content(novel_id, chapter_id)
                if content:
                    export_data["chapters"].append({
                        "chapter_info": chapter,
                        "content": content
                    })
        
        # Save to file
        export_path = self._get_export_path(novel_id, "json")
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return export_path
    
    def upload_to_s3(self, file_path: str, bucket_name: str, object_key: str = None) -> Dict[str, Any]:
        """Upload an export file to S3."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use filename as object key if not provided
        if object_key is None:
            object_key = os.path.basename(file_path)
        
        # Upload to S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.upload_file(file_path, bucket_name, object_key)
        
        # Generate presigned URL for easy access
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=604800  # 1 week
        )
        
        return {
            "bucket": bucket_name,
            "key": object_key,
            "url": presigned_url
        }

# Initialize the export manager
_export_manager = ExportManager()

@tool
def export_novel_to_markdown(novel_id: str) -> str:
    """将武侠小说导出为Markdown格式。
    
    使用场景：当需要将小说导出为可读性强的Markdown格式时使用，适用于发布、分享或进一步编辑。
    建议条件：确保小说已完成且包含章节内容，适用于需要格式化输出的场景。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含导出结果或错误信息的JSON字符串
    """
    try:
        export_path = _export_manager.export_to_markdown(novel_id)
        if export_path is None:
            return json.dumps({"error": "Novel not found or has no chapters"})
        
        return json.dumps({
            "success": True,
            "format": "markdown",
            "path": export_path
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def export_novel_to_json(novel_id: str) -> str:
    """将武侠小说导出为JSON格式。
    
    使用场景：当需要将小说导出为结构化数据格式时使用，适用于数据备份、程序处理或系统集成。
    建议条件：确保小说数据完整，适用于需要保持数据结构的场景。
    
    Args:
        novel_id: 小说ID
    
    Returns:
        包含导出结果或错误信息的JSON字符串
    """
    try:
        export_path = _export_manager.export_to_json(novel_id)
        if export_path is None:
            return json.dumps({"error": "Novel not found"})
        
        return json.dumps({
            "success": True,
            "format": "json",
            "path": export_path
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def upload_novel_export(file_path: str, bucket_name: str, object_key: Optional[str] = None) -> str:
    """将小说导出文件上传到S3存储。
    
    使用场景：当需要将导出的小说文件存储到云端时使用，适用于备份、分享或远程访问。
    建议条件：确保文件路径有效且S3存储桶存在，适用于需要云端存储的场景。
    
    Args:
        file_path: 导出文件路径
        bucket_name: S3存储桶名称
        object_key: S3对象键（可选，默认为文件名）
    
    Returns:
        包含上传结果或错误信息的JSON字符串
    """
    try:
        result = _export_manager.upload_to_s3(file_path, bucket_name, object_key)
        return json.dumps({
            "success": True,
            **result
        })
    except Exception as e:
        return json.dumps({"error": str(e)})