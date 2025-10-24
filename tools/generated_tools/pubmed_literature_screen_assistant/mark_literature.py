#!/usr/bin/env python3
"""维护文献标记清单"""

import json
from pathlib import Path
from collections import defaultdict
from strands import tool

try:
    from .download_fulltext import download_fulltext
except ImportError:
    from download_fulltext import download_fulltext


@tool
def mark_literature(pmc_ids: list, research_id: str, reasoning: dict = None, auto_download: bool = True) -> str:
    """
    标记文献并维护manifest.json文件，按发表年度分组和相关度排序
    标记时自动下载全文
    
    Args:
        pmc_ids: PMC ID列表
        research_id: 研究项目ID
        reasoning: 标记理由字典，格式 {pmcid: reasoning_text}
        auto_download: 是否自动下载全文，默认True
        
    Returns:
        JSON字符串，包含标记状态和统计信息
    """
    try:
        base_dir = Path(f".cache/pmc_literature/{research_id}")
        meta_dir = base_dir / "meta_data"
        paper_dir = base_dir / "paper"
        manifest_file = base_dir / "manifest.json"
        
        if not meta_dir.exists():
            return json.dumps({"status": "error", "message": "元数据目录不存在"})
        
        reasoning = reasoning or {}
        
        # 自动下载全文
        if auto_download:
            download_fulltext(pmc_ids, research_id)
        
        # 加载现有manifest
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        else:
            manifest = {"marked_literature": {"by_year": {}}, "statistics": {}}
        
        # 按年度分组
        by_year = defaultdict(list)
        impact_factors = []
        
        for pmc_id in pmc_ids:
            meta_file = meta_dir / f"{pmc_id}.json"
            if not meta_file.exists():
                continue
                
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 提取年份
            pub_date = metadata.get("publication_date", "")
            year = pub_date.split()[0] if pub_date else "unknown"
            
            # 检查全文是否缓存
            is_cached = (paper_dir / f"{pmc_id}.txt").exists()
            
            # 构建文献条目
            lit_entry = {
                "pmcid": pmc_id,
                "title": metadata.get("title", ""),
                "impact_factor": metadata.get("impact_factor", 0),
                "reasoning": reasoning.get(pmc_id, ""),
                "is_fulltext_cached": is_cached
            }
            
            by_year[year].append(lit_entry)
            
            if lit_entry["impact_factor"]:
                impact_factors.append(float(lit_entry["impact_factor"]))
        
        # 更新manifest结构
        manifest["marked_literature"]["by_year"] = {}
        
        for year in sorted(by_year.keys(), reverse=True):
            year_lits = by_year[year]
            year_ifs = [lit["impact_factor"] for lit in year_lits if lit["impact_factor"]]
            
            manifest["marked_literature"]["by_year"][year] = {
                "total_count": len(year_lits),
                "average_impact_factor": sum(year_ifs) / len(year_ifs) if year_ifs else 0,
                "literature": year_lits
            }
        
        # 更新统计信息
        total_count = sum(len(lits) for lits in by_year.values())
        manifest["statistics"] = {
            "total_count": total_count,
            "by_year": {year: len(lits) for year, lits in by_year.items()},
            "average_impact_factor": sum(impact_factors) / len(impact_factors) if impact_factors else 0
        }
        
        # 保存manifest
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "marked_count": total_count,
            "statistics": manifest["statistics"]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
