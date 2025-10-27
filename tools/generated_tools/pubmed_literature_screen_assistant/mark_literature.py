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
def mark_literature(pmc_ids: list, research_id: str, reasoning: dict = None, auto_download: bool = False) -> str:
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
        analysis_dir = base_dir / "analysis_results"
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
            
            # 尝试从analysis_results中获取impact_factor
            impact_factor = 0
            analysis_file = analysis_dir / f"{pmc_id}.json"
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                        impact_factor_raw = analysis.get("impact_factor", 0)
                        # 转换为数值类型（如果是字符串）
                        if isinstance(impact_factor_raw, str):
                            try:
                                impact_factor = float(impact_factor_raw)
                            except (ValueError, TypeError):
                                impact_factor = 0
                        else:
                            impact_factor = float(impact_factor_raw) if impact_factor_raw else 0
                except Exception:
                    pass
            
            # 提取年份
            pub_date = metadata.get("publication_date", "")
            year = pub_date.split()[0] if pub_date else "unknown"
            
            # 检查全文是否缓存
            is_cached = (paper_dir / f"{pmc_id}.txt").exists()
            
            # 构建文献条目
            lit_entry = {
                "pmcid": pmc_id,
                "title": metadata.get("title", ""),
                "impact_factor": impact_factor,
                "reasoning": reasoning.get(pmc_id, ""),
                "is_fulltext_cached": is_cached
            }
            
            by_year[year].append(lit_entry)
            
            if lit_entry["impact_factor"]:
                impact_factors.append(float(lit_entry["impact_factor"]))
        
        # 合并新的文献到现有manifest中，避免重复
        existing_pmcids = set()
        if "marked_literature" in manifest and "by_year" in manifest["marked_literature"]:
            for year_data in manifest["marked_literature"]["by_year"].values():
                for lit in year_data.get("literature", []):
                    existing_pmcids.add(lit.get("pmcid"))
        
        # 添加新文献（过滤掉已存在的）
        new_year_data = defaultdict(list)
        for year, lits in by_year.items():
            for lit in lits:
                if lit["pmcid"] not in existing_pmcids:
                    new_year_data[year].append(lit)
                    existing_pmcids.add(lit["pmcid"])
        
        # 合并到现有manifest中
        if "marked_literature" not in manifest:
            manifest["marked_literature"] = {"by_year": {}}
        if "by_year" not in manifest["marked_literature"]:
            manifest["marked_literature"]["by_year"] = {}
        
        for year in sorted(new_year_data.keys(), reverse=True):
            year_lits = new_year_data[year]
            year_ifs = [lit["impact_factor"] for lit in year_lits if lit["impact_factor"]]
            
            if year in manifest["marked_literature"]["by_year"]:
                # 合并到现有年份
                manifest["marked_literature"]["by_year"][year]["literature"].extend(year_lits)
                manifest["marked_literature"]["by_year"][year]["total_count"] = len(manifest["marked_literature"]["by_year"][year]["literature"])
                all_year_ifs = [lit["impact_factor"] for lit in manifest["marked_literature"]["by_year"][year]["literature"] if lit["impact_factor"]]
                manifest["marked_literature"]["by_year"][year]["average_impact_factor"] = sum(all_year_ifs) / len(all_year_ifs) if all_year_ifs else 0
            else:
                # 新建年份
                manifest["marked_literature"]["by_year"][year] = {
                    "total_count": len(year_lits),
                    "average_impact_factor": sum(year_ifs) / len(year_ifs) if year_ifs else 0,
                    "literature": year_lits
                }
        
        # 重新计算所有年份的统计信息
        all_year_data = manifest["marked_literature"]["by_year"]
        total_count = sum(len(data["literature"]) for data in all_year_data.values())
        all_impact_factors = []
        for data in all_year_data.values():
            all_impact_factors.extend([lit["impact_factor"] for lit in data["literature"] if lit["impact_factor"]])
        
        # 更新统计信息
        manifest["statistics"] = {
            "total_count": total_count,
            "by_year": {year: data["total_count"] for year, data in all_year_data.items()},
            "average_impact_factor": sum(all_impact_factors) / len(all_impact_factors) if all_impact_factors else 0
        }
        
        # 保存manifest
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "marked_count": manifest["statistics"]["total_count"],
            "statistics": manifest["statistics"]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
