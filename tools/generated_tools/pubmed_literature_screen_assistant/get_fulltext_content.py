#!/usr/bin/env python3
"""获取文献全文内容"""

import json
from pathlib import Path
from strands import tool


@tool
def get_fulltext_content(pmc_ids: list, research_id: str) -> str:
    """
    获取文献全文内容，以字符串方式返回
    
    Args:
        pmc_ids: PMC ID列表（单个或多个）
        research_id: 研究项目ID
        
    Returns:
        JSON字符串，包含全文内容
    """
    try:
        if isinstance(pmc_ids, str):
            pmc_ids = [pmc_ids]
            
        cache_dir = Path(f".cache/pmc_literature/{research_id}/paper")
        
        if not cache_dir.exists():
            return json.dumps({"status": "error", "message": "全文缓存目录不存在"})
        
        results = []
        
        for pmc_id in pmc_ids:
            pmc_id = pmc_id if pmc_id.startswith("PMC") else f"PMC{pmc_id}"
            
            # 读取TXT
            txt_file = cache_dir / f"{pmc_id}.txt"
            if txt_file.exists():
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                results.append({"pmcid": pmc_id, "content": content, "format": "txt"})
                continue
            
            results.append({"pmcid": pmc_id, "status": "not_found"})
        
        return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

