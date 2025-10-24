#!/usr/bin/env python3
"""获取文献标记清单"""

import json
from pathlib import Path
from strands import tool


@tool
def get_manifest(research_id: str) -> str:
    """
    获取当前标记的manifest.json文件内容
    
    Args:
        research_id: 研究项目ID
        
    Returns:
        JSON字符串，包含manifest文件的完整内容
    """
    try:
        manifest_file = Path(f".cache/pmc_literature/{research_id}/manifest.json")
        
        if not manifest_file.exists():
            return json.dumps({
                "status": "error",
                "message": "manifest.json文件不存在，请先标记文献"
            }, ensure_ascii=False)
        
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        return json.dumps({
            "status": "success",
            "manifest": manifest
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
