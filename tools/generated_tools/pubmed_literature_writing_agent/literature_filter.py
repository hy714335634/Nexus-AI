#!/usr/bin/env python3
"""
Literature Filter Tool

提供按时间范围、期刊类型和影响因子进行文献筛选的功能
"""

import json
import re
import os
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import logging
from pathlib import Path
from datetime import datetime, timedelta
import csv

from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 本地缓存目录
CACHE_DIR = Path(".cache/pubmed_literature_agent")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 影响因子数据缓存
IMPACT_FACTOR_CACHE = {}


def _load_impact_factors() -> Dict[str, float]:
    """
    加载期刊影响因子数据
    
    Returns:
        期刊名称到影响因子的映射
    """
    # 检查缓存
    if IMPACT_FACTOR_CACHE:
        return IMPACT_FACTOR_CACHE
    
    # 缓存文件路径
    cache_file = CACHE_DIR / "journal_impact_factors.csv"
    
    # 如果缓存文件存在，从缓存加载
    if cache_file.exists():
        try:
            impact_factors = {}
            with open(cache_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过标题行
                
                for row in reader:
                    if len(row) >= 2:
                        journal_name = row[0].strip().lower()
                        try:
                            impact_factor = float(row[1])
                            impact_factors[journal_name] = impact_factor
                        except (ValueError, TypeError):
                            pass
            
            # 保存到内存缓存
            IMPACT_FACTOR_CACHE.update(impact_factors)
            return impact_factors
            
        except Exception as e:
            logger.error(f"从缓存加载影响因子失败: {str(e)}")
    
    # 如果没有缓存，使用内置的基本影响因子数据
    # 这些是示例数据，实际应用中应该使用更完整的数据源
    basic_impact_factors = {
        "nature": 49.962,
        "science": 47.728,
        "cell": 41.582,
        "new england journal of medicine": 91.245,
        "lancet": 79.321,
        "jama": 56.272,
        "nature medicine": 53.440,
        "bmj": 39.890,
        "plos one": 3.240,
        "scientific reports": 4.996,
        "proceedings of the national academy of sciences": 11.205,
        "journal of biological chemistry": 5.157,
        "nucleic acids research": 16.971,
        "bioinformatics": 6.937,
        "genome research": 11.093,
        "genome biology": 13.583,
        "plos computational biology": 4.700,
        "bmc bioinformatics": 3.024,
        "journal of molecular biology": 5.469,
        "molecular cell": 17.970,
        "journal of cell biology": 10.539,
        "journal of virology": 5.103,
        "journal of bacteriology": 3.234,
        "journal of immunology": 5.422,
        "journal of neuroscience": 6.167,
        "neuron": 17.173,
        "cancer cell": 31.743,
        "cancer research": 12.701,
        "circulation": 29.690,
        "diabetes": 9.461,
        "hepatology": 17.425,
        "gastroenterology": 22.682,
        "blood": 22.113,
        "american journal of respiratory and critical care medicine": 21.405,
        "annals of internal medicine": 25.391,
        "journal of clinical oncology": 44.544,
        "journal of clinical investigation": 14.808,
        "journal of experimental medicine": 14.305,
        "immunity": 31.745,
        "molecular psychiatry": 15.992,
        "nature genetics": 38.330,
        "nature immunology": 25.455,
        "nature neuroscience": 24.884,
        "nature biotechnology": 54.908,
        "nature cell biology": 28.213,
        "nature methods": 38.500,
        "nature protocols": 16.289,
        "nature reviews cancer": 60.716,
        "nature reviews immunology": 65.931,
        "nature reviews molecular cell biology": 94.444,
        "nature reviews neuroscience": 41.583,
        "nature reviews genetics": 46.813,
        "cell stem cell": 24.633,
        "cell metabolism": 22.415,
        "developmental cell": 10.092,
        "genes & development": 9.527,
        "molecular systems biology": 11.429,
        "genome medicine": 10.675,
        "elife": 8.140,
        "embo journal": 11.598,
        "embo molecular medicine": 10.624,
        "journal of hepatology": 25.083,
        "gut": 23.059,
        "annals of oncology": 32.976,
        "journal of the american college of cardiology": 24.094,
        "european heart journal": 29.983,
        "circulation research": 17.367,
        "journal of allergy and clinical immunology": 10.793,
        "american journal of human genetics": 11.025,
        "molecular psychiatry": 15.992,
        "biological psychiatry": 13.382,
        "molecular therapy": 11.454,
        "clinical cancer research": 13.801,
        "leukemia": 11.528,
        "journal of pathology": 8.662,
        "brain": 13.501,
        "annals of neurology": 10.422,
        "neurology": 9.910,
        "journal of medical genetics": 5.899,
        "journal of medical internet research": 7.078,
        "bmc medicine": 8.775,
        "plos medicine": 10.500,
        "plos biology": 8.029,
        "plos genetics": 5.917,
        "plos pathogens": 6.218,
        "genome medicine": 10.675,
        "genome biology": 13.583,
        "nucleic acids research": 16.971,
        "bioinformatics": 6.937
    }
    
    # 保存到内存缓存
    IMPACT_FACTOR_CACHE.update(basic_impact_factors)
    
    # 保存到文件缓存
    try:
        with open(cache_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Journal Name", "Impact Factor"])
            for journal, impact in basic_impact_factors.items():
                writer.writerow([journal, impact])
    except Exception as e:
        logger.error(f"保存影响因子到缓存失败: {str(e)}")
    
    return basic_impact_factors


def _extract_year(date_str: str) -> Optional[int]:
    """
    从日期字符串中提取年份
    
    Args:
        date_str: 日期字符串
        
    Returns:
        年份或None
    """
    try:
        # 尝试匹配年份
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            return int(year_match.group(0))
        return None
    except Exception:
        return None


def _get_journal_impact_factor(journal_name: str) -> Optional[float]:
    """
    获取期刊的影响因子
    
    Args:
        journal_name: 期刊名称
        
    Returns:
        影响因子或None
    """
    if not journal_name:
        return None
    
    # 加载影响因子数据
    impact_factors = _load_impact_factors()
    
    # 规范化期刊名称
    journal_lower = journal_name.lower()
    
    # 直接匹配
    if journal_lower in impact_factors:
        return impact_factors[journal_lower]
    
    # 部分匹配
    for name, factor in impact_factors.items():
        if name in journal_lower or journal_lower in name:
            return factor
    
    # 没有找到匹配
    return None


@tool
def filter_by_time_range(literature_results: str, start_year: int = None, end_year: int = None) -> str:
    """
    按时间范围筛选文献
    
    Args:
        literature_results (str): JSON格式的文献搜索结果
        start_year (int): 起始年份
        end_year (int): 结束年份
        
    Returns:
        str: JSON格式的筛选结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 设置默认值
        if end_year is None:
            end_year = datetime.now().year
        
        if start_year is None:
            start_year = end_year - 10  # 默认过去10年
        
        # 确保起始年份不大于结束年份
        if start_year > end_year:
            start_year, end_year = end_year, start_year
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 筛选文献
        filtered_articles = []
        
        for article in articles:
            article_year = None
            
            # 从year字段获取年份
            if "year" in article:
                try:
                    article_year = int(article["year"])
                except (ValueError, TypeError):
                    pass
            
            # 从publication_date字段获取年份
            if article_year is None and "publication_date" in article:
                article_year = _extract_year(article["publication_date"])
            
            # 如果没有找到年份，尝试从其他字段提取
            if article_year is None:
                for field in ["title", "abstract", "journal"]:
                    if field in article and article[field]:
                        extracted_year = _extract_year(article[field])
                        if extracted_year:
                            article_year = extracted_year
                            break
            
            # 如果找到了年份，进行筛选
            if article_year is not None:
                if start_year <= article_year <= end_year:
                    # 添加年份信息
                    article["extracted_year"] = article_year
                    filtered_articles.append(article)
            else:
                # 如果无法确定年份，默认包含
                article["extracted_year"] = None
                filtered_articles.append(article)
        
        # 构建结果
        filter_result = {
            "status": "success",
            "filter_type": "time_range",
            "filter_params": {
                "start_year": start_year,
                "end_year": end_year
            },
            "original_count": len(articles),
            "filtered_count": len(filtered_articles),
            "results": filtered_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                filter_result[key] = results[key]
        
        return json.dumps(filter_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按时间范围筛选失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按时间范围筛选失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def filter_by_journal_type(literature_results: str, journal_types: List[str] = None) -> str:
    """
    按期刊类型筛选文献
    
    Args:
        literature_results (str): JSON格式的文献搜索结果
        journal_types (List[str]): 期刊类型列表 (oa_comm: 开放获取商业使用, oa_noncomm: 开放获取非商业使用, phe_timebound: 公共卫生紧急情况)
        
    Returns:
        str: JSON格式的筛选结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 设置默认值
        if journal_types is None or not journal_types:
            journal_types = ["oa_comm", "oa_noncomm", "phe_timebound"]
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 筛选文献
        filtered_articles = []
        
        for article in articles:
            # 从directory字段获取期刊类型
            if "directory" in article and article["directory"] in journal_types:
                filtered_articles.append(article)
        
        # 构建结果
        filter_result = {
            "status": "success",
            "filter_type": "journal_type",
            "filter_params": {
                "journal_types": journal_types
            },
            "original_count": len(articles),
            "filtered_count": len(filtered_articles),
            "results": filtered_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                filter_result[key] = results[key]
        
        return json.dumps(filter_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按期刊类型筛选失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按期刊类型筛选失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def filter_by_impact_factor(literature_results: str, min_impact_factor: float = 0.0) -> str:
    """
    按影响因子筛选文献
    
    Args:
        literature_results (str): JSON格式的文献搜索结果
        min_impact_factor (float): 最小影响因子
        
    Returns:
        str: JSON格式的筛选结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 加载影响因子数据
        impact_factors = _load_impact_factors()
        
        # 筛选文献
        filtered_articles = []
        
        for article in articles:
            impact_factor = None
            
            # 从journal字段获取期刊名称
            if "journal" in article and article["journal"]:
                impact_factor = _get_journal_impact_factor(article["journal"])
            
            # 添加影响因子信息
            article["impact_factor"] = impact_factor
            
            # 筛选
            if impact_factor is not None and impact_factor >= min_impact_factor:
                filtered_articles.append(article)
        
        # 构建结果
        filter_result = {
            "status": "success",
            "filter_type": "impact_factor",
            "filter_params": {
                "min_impact_factor": min_impact_factor
            },
            "original_count": len(articles),
            "filtered_count": len(filtered_articles),
            "results": filtered_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                filter_result[key] = results[key]
        
        return json.dumps(filter_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按影响因子筛选失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按影响因子筛选失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def filter_by_retraction_status(literature_results: str, exclude_retracted: bool = True) -> str:
    """
    按撤稿状态筛选文献
    
    Args:
        literature_results (str): JSON格式的文献搜索结果
        exclude_retracted (bool): 是否排除已撤稿文章
        
    Returns:
        str: JSON格式的筛选结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 筛选文献
        filtered_articles = []
        retracted_articles = []
        
        for article in articles:
            # 检查是否已撤稿
            is_retracted = False
            
            # 从标题中检查撤稿关键词
            if "title" in article and article["title"]:
                if re.search(r'\b(retract(ed|ion)|withdraw(n|al))\b', article["title"], re.IGNORECASE):
                    is_retracted = True
            
            # 从摘要中检查撤稿关键词
            if not is_retracted and "abstract" in article and article["abstract"]:
                if re.search(r'\b(retract(ed|ion)|withdraw(n|al))\b', article["abstract"], re.IGNORECASE):
                    is_retracted = True
            
            # 添加撤稿状态信息
            article["is_retracted"] = is_retracted
            
            # 根据撤稿状态筛选
            if is_retracted:
                retracted_articles.append(article)
            else:
                filtered_articles.append(article)
        
        # 构建结果
        filter_result = {
            "status": "success",
            "filter_type": "retraction_status",
            "filter_params": {
                "exclude_retracted": exclude_retracted
            },
            "original_count": len(articles),
            "retracted_count": len(retracted_articles),
            "filtered_count": len(filtered_articles if exclude_retracted else articles),
            "results": filtered_articles if exclude_retracted else articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                filter_result[key] = results[key]
        
        return json.dumps(filter_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"按撤稿状态筛选失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"按撤稿状态筛选失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def combined_filter(literature_results: str, filter_params: Dict[str, Any]) -> str:
    """
    组合多个筛选条件
    
    Args:
        literature_results (str): JSON格式的文献搜索结果
        filter_params (Dict[str, Any]): 筛选参数
            - start_year (int): 起始年份
            - end_year (int): 结束年份
            - journal_types (List[str]): 期刊类型列表
            - min_impact_factor (float): 最小影响因子
            - exclude_retracted (bool): 是否排除已撤稿文章
        
    Returns:
        str: JSON格式的筛选结果
    """
    try:
        # 解析文献结果
        try:
            results = json.loads(literature_results)
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "无效的JSON格式文献结果"
            }, ensure_ascii=False)
        
        # 获取文献列表
        articles = []
        if "results" in results:
            articles = results["results"]
        
        # 提取筛选参数
        start_year = filter_params.get("start_year")
        end_year = filter_params.get("end_year")
        journal_types = filter_params.get("journal_types")
        min_impact_factor = filter_params.get("min_impact_factor", 0.0)
        exclude_retracted = filter_params.get("exclude_retracted", True)
        
        # 设置默认值
        if end_year is None:
            end_year = datetime.now().year
        
        if start_year is None:
            start_year = end_year - 10  # 默认过去10年
        
        # 确保起始年份不大于结束年份
        if start_year > end_year:
            start_year, end_year = end_year, start_year
        
        if journal_types is None or not journal_types:
            journal_types = ["oa_comm", "oa_noncomm", "phe_timebound"]
        
        # 筛选文献
        filtered_articles = []
        
        for article in articles:
            # 1. 检查年份
            article_year = None
            
            # 从year字段获取年份
            if "year" in article:
                try:
                    article_year = int(article["year"])
                except (ValueError, TypeError):
                    pass
            
            # 从publication_date字段获取年份
            if article_year is None and "publication_date" in article:
                article_year = _extract_year(article["publication_date"])
            
            # 如果没有找到年份，尝试从其他字段提取
            if article_year is None:
                for field in ["title", "abstract", "journal"]:
                    if field in article and article[field]:
                        extracted_year = _extract_year(article[field])
                        if extracted_year:
                            article_year = extracted_year
                            break
            
            # 添加年份信息
            article["extracted_year"] = article_year
            
            # 如果找到了年份，进行筛选
            if article_year is not None and (article_year < start_year or article_year > end_year):
                continue
            
            # 2. 检查期刊类型
            if "directory" in article and article["directory"] not in journal_types:
                continue
            
            # 3. 检查影响因子
            impact_factor = None
            
            # 从journal字段获取期刊名称
            if "journal" in article and article["journal"]:
                impact_factor = _get_journal_impact_factor(article["journal"])
            
            # 添加影响因子信息
            article["impact_factor"] = impact_factor
            
            # 筛选
            if impact_factor is not None and impact_factor < min_impact_factor:
                continue
            
            # 4. 检查撤稿状态
            is_retracted = False
            
            # 从标题中检查撤稿关键词
            if "title" in article and article["title"]:
                if re.search(r'\b(retract(ed|ion)|withdraw(n|al))\b', article["title"], re.IGNORECASE):
                    is_retracted = True
            
            # 从摘要中检查撤稿关键词
            if not is_retracted and "abstract" in article and article["abstract"]:
                if re.search(r'\b(retract(ed|ion)|withdraw(n|al))\b', article["abstract"], re.IGNORECASE):
                    is_retracted = True
            
            # 添加撤稿状态信息
            article["is_retracted"] = is_retracted
            
            # 根据撤稿状态筛选
            if exclude_retracted and is_retracted:
                continue
            
            # 通过所有筛选条件，添加到结果
            filtered_articles.append(article)
        
        # 构建结果
        filter_result = {
            "status": "success",
            "filter_type": "combined",
            "filter_params": filter_params,
            "original_count": len(articles),
            "filtered_count": len(filtered_articles),
            "results": filtered_articles
        }
        
        # 保留原始查询信息
        for key in ["search_query", "topic", "subtopics", "directories_searched"]:
            if key in results:
                filter_result[key] = results[key]
        
        return json.dumps(filter_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"组合筛选失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"组合筛选失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_journal_impact_factor(journal_name: str) -> str:
    """
    获取期刊的影响因子
    
    Args:
        journal_name (str): 期刊名称
        
    Returns:
        str: JSON格式的影响因子信息
    """
    try:
        # 获取影响因子
        impact_factor = _get_journal_impact_factor(journal_name)
        
        if impact_factor is not None:
            return json.dumps({
                "status": "success",
                "journal_name": journal_name,
                "impact_factor": impact_factor
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "not_found",
                "journal_name": journal_name,
                "message": "未找到该期刊的影响因子信息"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"获取影响因子失败: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"获取影响因子失败: {str(e)}"
        }, ensure_ascii=False)