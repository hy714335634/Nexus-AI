#!/usr/bin/env python3
"""下载并缓存文献全文"""

import json
import os
from pathlib import Path
import boto3
from botocore.config import Config
from botocore import UNSIGNED
from strands import tool

PMC_BUCKET = "pmc-oa-opendata"
PMC_REGION = "us-east-1"


def _get_s3_client():
    return boto3.client('s3', region_name=PMC_REGION, config=Config(signature_version=UNSIGNED))


def _find_and_download_pmc_file(s3_client, pmc_id: str, cache_dir: Path):
    """通过直接路径尝试下载PMC TXT文件"""
    possible_paths = [
        f"oa_comm/txt/all/{pmc_id}.txt",
        f"oa_noncomm/txt/all/{pmc_id}.txt"
    ]
    
    for s3_key in possible_paths:
        try:
            s3_client.head_object(Bucket=PMC_BUCKET, Key=s3_key)
            cache_file = cache_dir / f"{pmc_id}.txt"
            s3_client.download_file(PMC_BUCKET, s3_key, str(cache_file))
            return cache_file
        except:
            continue
    
    return None


@tool
def download_fulltext(pmc_ids: list, research_id: str) -> str:
    """
    下载文献TXT全文并缓存
    
    Args:
        pmc_ids: PMC ID列表（单个或多个）
        research_id: 研究项目ID
        
    Returns:
        JSON字符串，包含下载状态
    """
    try:
        if isinstance(pmc_ids, str):
            pmc_ids = [pmc_ids]
            
        cache_dir = Path(f".cache/pmc_literature/{research_id}/paper")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        s3_client = _get_s3_client()
        results = []
        
        for pmc_id in pmc_ids:
            pmc_id = pmc_id if pmc_id.startswith("PMC") else f"PMC{pmc_id}"
            
            cache_file = _find_and_download_pmc_file(s3_client, pmc_id, cache_dir)
            
            if not cache_file:
                results.append({"pmcid": pmc_id, "status": "not_found"})
                continue
            
            results.append({"pmcid": pmc_id, "status": "cached", "format": "txt"})
        
        return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


