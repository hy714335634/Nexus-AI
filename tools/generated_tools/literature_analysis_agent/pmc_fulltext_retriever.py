#!/usr/bin/env python3
"""
PMC Full Text Retriever Tool

Retrieves full text content from PubMed Central articles using PMC IDs.
"""

import json
import logging
from typing import List
from strands import tool

# Import from existing pubmed tools
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "pubmed_literature_writing_agent"))
from tools.generated_tools.pubmed_literature_writing_agent.pmc_s3_connector import pmc_download_file, pmc_search_files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
def retrieve_pmc_fulltext(pmc_ids: List[str], format_type: str = "txt") -> str:
    """
    Retrieve full text content from PMC articles by PMC IDs.
    
    Args:
        pmc_ids: List of PMC IDs (e.g., ["PMC1234567", "PMC7654321"])
        format_type: File format (txt or xml), default is txt
        
    Returns:
        JSON string containing full text content for each PMC ID
    """
    try:
        results = []
        
        for pmc_id in pmc_ids:
            # Clean PMC ID
            clean_id = pmc_id.strip().upper()
            if not clean_id.startswith("PMC"):
                clean_id = f"PMC{clean_id}"
            
            # Search for the file
            search_result = pmc_search_files(
                search_term=clean_id,
                directory="oa_comm",
                format_type=format_type,
                max_results=1
            )
            
            search_data = json.loads(search_result)
            
            if search_data.get("status") == "success" and search_data.get("results"):
                file_key = search_data["results"][0]["key"]
                
                # Download the file
                download_result = pmc_download_file(
                    file_key=file_key,
                    format_type=format_type,
                    save_to_cache=True
                )
                
                download_data = json.loads(download_result)
                
                if download_data.get("status") == "success":
                    # Read full content from cache
                    cache_path = download_data.get("cache_path")
                    if cache_path:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            full_content = f.read()
                        
                        results.append({
                            "pmc_id": clean_id,
                            "status": "success",
                            "content": full_content,
                            "format": format_type,
                            "content_length": len(full_content)
                        })
                    else:
                        results.append({
                            "pmc_id": clean_id,
                            "status": "error",
                            "message": "无法获取缓存文件"
                        })
                else:
                    results.append({
                        "pmc_id": clean_id,
                        "status": "error",
                        "message": download_data.get("message", "下载失败")
                    })
            else:
                results.append({
                    "pmc_id": clean_id,
                    "status": "error",
                    "message": "未找到该PMC文献"
                })
        
        return json.dumps({
            "status": "success",
            "total_requested": len(pmc_ids),
            "total_retrieved": sum(1 for r in results if r["status"] == "success"),
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"检索PMC全文失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"检索PMC全文失败: {str(e)}"
        }, ensure_ascii=False)
