#!/usr/bin/env python3
"""
公司信息搜索工具

提供多搜索引擎集成的公司信息搜索功能，支持深度检索和内容提取
"""

import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import quote_plus

from strands import tool


@tool
def company_search(company_name: str, search_engines: List[str] = None, 
                  max_results: int = 5, deep_search: bool = True) -> str:
    """
    使用多种搜索引擎查询公司信息
    
    Args:
        company_name: 要搜索的公司名称
        search_engines: 要使用的搜索引擎列表，默认为["google", "bing", "baidu", "duckduckgo"]
        max_results: 每个搜索引擎返回的最大结果数，默认为5
        deep_search: 是否进行深度搜索，获取更多公司相关信息，默认为True
    
    Returns:
        JSON格式的搜索结果，包含各搜索引擎的结果和元数据
    """
    try:
        if not company_name:
            return json.dumps({
                "status": "error",
                "message": "公司名称不能为空",
                "results": None
            }, ensure_ascii=False)
        
        # 设置默认搜索引擎
        if not search_engines:
            search_engines = ["google", "bing", "baidu", "duckduckgo"]
        
        # 构建搜索查询
        search_queries = [
            f"{company_name} company profile",
            f"{company_name} official website",
            f"{company_name} revenue",
            f"{company_name} business information",
            f"{company_name} company overview"
        ]
        
        # 如果公司名称包含中文，添加中文查询
        if any('\u4e00' <= char <= '\u9fff' for char in company_name):
            search_queries.extend([
                f"{company_name} 公司简介",
                f"{company_name} 官网",
                f"{company_name} 营业额",
                f"{company_name} 企业信息"
            ])
        
        # 收集搜索结果
        all_results = {
            "status": "success",
            "message": f"成功搜索公司信息: {company_name}",
            "company_name": company_name,
            "search_metadata": {
                "search_engines": search_engines,
                "max_results": max_results,
                "deep_search": deep_search,
                "search_queries": search_queries[:max_results],
                "timestamp": time.time()
            },
            "results": {}
        }
        
        # 为每个搜索引擎构建搜索URL
        for engine in search_engines:
            engine_results = []
            
            for query in search_queries[:max_results]:
                search_url = _build_search_url(engine, query)
                
                # 记录查询信息
                query_info = {
                    "query": query,
                    "search_url": search_url,
                    "engine": engine,
                    "timestamp": time.time(),
                    "status": "pending_http_request"  # 标记需要实际HTTP请求
                }
                
                engine_results.append(query_info)
            
            all_results["results"][engine] = {
                "engine_name": engine,
                "search_queries": engine_results,
                "deep_content": [] if deep_search else None
            }
        
        # 添加深度搜索说明
        if deep_search:
            all_results["deep_search_info"] = {
                "status": "pending",
                "note": "深度搜索需要使用http_request工具获取搜索结果中的链接内容",
                "recommended_steps": [
                    "1. 使用http_request工具获取搜索URL的内容",
                    "2. 从搜索结果中提取有价值的链接",
                    "3. 再次使用http_request工具获取这些链接的内容",
                    "4. 从内容中提取公司信息"
                ]
            }
        
        return json.dumps(all_results, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"搜索公司信息时发生错误: {str(e)}",
            "results": None
        }, ensure_ascii=False)


@tool
def company_info_extractor(content: str, company_name: str) -> str:
    """
    从网页内容中提取公司信息
    
    Args:
        content: 网页内容
        company_name: 公司名称，用于上下文匹配
    
    Returns:
        JSON格式的提取结果，包含公司信息和元数据
    """
    try:
        if not content:
            return json.dumps({
                "status": "error",
                "message": "内容不能为空",
                "extracted_info": None
            }, ensure_ascii=False)
        
        # 初始化提取结果
        extracted_info = {
            "company_name": company_name,
            "revenue": _extract_revenue(content, company_name),
            "company_profile": _extract_company_profile(content, company_name),
            "founding_year": _extract_founding_year(content),
            "headquarters": _extract_headquarters(content),
            "industry": _extract_industry(content),
            "employee_count": _extract_employee_count(content),
            "website": _extract_website(content, company_name),
            "social_media": _extract_social_media(content),
            "key_executives": _extract_key_executives(content),
            "products_services": _extract_products_services(content, company_name)
        }
        
        # 添加提取质量评估
        extraction_quality = _assess_extraction_quality(extracted_info)
        
        result = {
            "status": "success",
            "message": "成功从内容中提取公司信息",
            "company_name": company_name,
            "extraction_metadata": {
                "content_length": len(content),
                "extraction_timestamp": time.time(),
                "extraction_quality": extraction_quality
            },
            "extracted_info": extracted_info
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"提取公司信息时发生错误: {str(e)}",
            "extracted_info": None
        }, ensure_ascii=False)


@tool
def multi_engine_company_search(company_name: str, search_type: str = "comprehensive", 
                              max_results: int = 3) -> str:
    """
    使用多搜索引擎策略进行公司信息查询
    
    Args:
        company_name: 要搜索的公司名称
        search_type: 搜索类型，可选值为"basic"(基本信息)、"financial"(财务信息)、"comprehensive"(综合信息)
        max_results: 每个搜索引擎返回的最大结果数，默认为3
    
    Returns:
        JSON格式的多引擎搜索结果
    """
    try:
        if not company_name:
            return json.dumps({
                "status": "error",
                "message": "公司名称不能为空",
                "results": None
            }, ensure_ascii=False)
        
        # 根据搜索类型确定查询和搜索引擎
        if search_type == "basic":
            search_engines = ["google", "bing"]
            search_queries = [
                f"{company_name} company profile",
                f"{company_name} official website"
            ]
            if any('\u4e00' <= char <= '\u9fff' for char in company_name):
                search_queries.extend([
                    f"{company_name} 公司简介",
                    f"{company_name} 官网"
                ])
        elif search_type == "financial":
            search_engines = ["google", "bing", "baidu"]
            search_queries = [
                f"{company_name} annual revenue",
                f"{company_name} financial report",
                f"{company_name} earnings"
            ]
            if any('\u4e00' <= char <= '\u9fff' for char in company_name):
                search_queries.extend([
                    f"{company_name} 年营收",
                    f"{company_name} 财务报告",
                    f"{company_name} 财务状况"
                ])
        else:  # comprehensive
            search_engines = ["google", "bing", "baidu", "duckduckgo"]
            search_queries = [
                f"{company_name} company profile",
                f"{company_name} revenue",
                f"{company_name} business information",
                f"{company_name} industry",
                f"{company_name} headquarters"
            ]
            if any('\u4e00' <= char <= '\u9fff' for char in company_name):
                search_queries.extend([
                    f"{company_name} 公司简介",
                    f"{company_name} 营业额",
                    f"{company_name} 企业信息",
                    f"{company_name} 行业",
                    f"{company_name} 总部"
                ])
        
        # 收集搜索结果
        all_results = {
            "status": "success",
            "message": f"成功执行多引擎搜索: {company_name}",
            "company_name": company_name,
            "search_metadata": {
                "search_type": search_type,
                "search_engines": search_engines,
                "max_results": max_results,
                "search_queries": search_queries[:max_results],
                "timestamp": time.time()
            },
            "results": {}
        }
        
        # 为每个搜索引擎构建搜索URL
        for engine in search_engines:
            engine_results = []
            
            for query in search_queries[:max_results]:
                search_url = _build_search_url(engine, query)
                
                # 记录查询信息
                query_info = {
                    "query": query,
                    "search_url": search_url,
                    "engine": engine,
                    "timestamp": time.time(),
                    "status": "pending_http_request"  # 标记需要实际HTTP请求
                }
                
                engine_results.append(query_info)
            
            all_results["results"][engine] = {
                "engine_name": engine,
                "search_queries": engine_results
            }
        
        # 添加搜索指南
        all_results["search_guide"] = {
            "next_steps": [
                "1. 使用http_request工具获取搜索URL的内容",
                "2. 从搜索结果中提取有价值的链接",
                "3. 再次使用http_request工具获取这些链接的内容",
                "4. 使用company_info_extractor工具从内容中提取公司信息"
            ],
            "search_strategy": f"针对{search_type}类型的搜索，优先关注" + 
                             ("公司基本信息和官网" if search_type == "basic" else
                              "财务数据和财报信息" if search_type == "financial" else
                              "全面的公司信息，包括基本信息、财务数据、行业地位等")
        }
        
        return json.dumps(all_results, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"多引擎搜索时发生错误: {str(e)}",
            "results": None
        }, ensure_ascii=False)


def _build_search_url(engine: str, query: str) -> str:
    """构建搜索引擎URL"""
    encoded_query = quote_plus(query)
    
    if engine.lower() == "google":
        return f"https://www.google.com/search?q={encoded_query}"
    elif engine.lower() == "bing":
        return f"https://www.bing.com/search?q={encoded_query}"
    elif engine.lower() == "baidu":
        return f"https://www.baidu.com/s?wd={encoded_query}"
    elif engine.lower() == "duckduckgo":
        return f"https://duckduckgo.com/?q={encoded_query}"
    else:
        return f"https://www.google.com/search?q={encoded_query}"


def _extract_revenue(content: str, company_name: str) -> Optional[str]:
    """从内容中提取公司营收信息"""
    # 英文模式
    revenue_patterns = [
        rf"{company_name}.*?revenue.*?[\$£€]?\s*\d+(?:\.\d+)?\s*(?:billion|million|trillion|B|M|T)",
        r"revenue.*?[\$£€]?\s*\d+(?:\.\d+)?\s*(?:billion|million|trillion|B|M|T)",
        r"annual revenue.*?[\$£€]?\s*\d+(?:\.\d+)?\s*(?:billion|million|trillion|B|M|T)",
        r"[\$£€]?\s*\d+(?:\.\d+)?\s*(?:billion|million|trillion|B|M|T).*?revenue"
    ]
    
    # 中文模式
    if any('\u4e00' <= char <= '\u9fff' for char in company_name):
        revenue_patterns.extend([
            rf"{company_name}.*?营业额.*?(?:人民币|美元|欧元|港币)?\s*\d+(?:\.\d+)?\s*(?:亿|万|千万|百万)",
            r"营业额.*?(?:人民币|美元|欧元|港币)?\s*\d+(?:\.\d+)?\s*(?:亿|万|千万|百万)",
            r"年收入.*?(?:人民币|美元|欧元|港币)?\s*\d+(?:\.\d+)?\s*(?:亿|万|千万|百万)",
            r"(?:人民币|美元|欧元|港币)?\s*\d+(?:\.\d+)?\s*(?:亿|万|千万|百万).*?营业额"
        ])
    
    for pattern in revenue_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            # 提取匹配的上下文
            start = max(0, matches.start() - 50)
            end = min(len(content), matches.end() + 50)
            context = content[start:end]
            return context.strip()
    
    return None


def _extract_company_profile(content: str, company_name: str) -> Optional[str]:
    """从内容中提取公司简介"""
    # 尝试找到包含公司简介的段落
    profile_patterns = [
        rf"{company_name}\s+is\s+a.*?(?:\.|\n)",
        r"About\s+(?:the\s+)?[Cc]ompany.*?(?:\.|\n)",
        r"[Cc]ompany\s+[Pp]rofile.*?(?:\.|\n)",
        r"[Cc]ompany\s+[Oo]verview.*?(?:\.|\n)"
    ]
    
    # 中文模式
    if any('\u4e00' <= char <= '\u9fff' for char in company_name):
        profile_patterns.extend([
            rf"{company_name}\s+是\s+.*?(?:。|\n)",
            r"公司简介.*?(?:。|\n)",
            r"关于公司.*?(?:。|\n)",
            r"企业概况.*?(?:。|\n)"
        ])
    
    for pattern in profile_patterns:
        matches = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if matches:
            # 提取匹配的上下文，最多300个字符
            profile = matches.group(0)
            if len(profile) > 300:
                profile = profile[:300] + "..."
            return profile.strip()
    
    return None


def _extract_founding_year(content: str) -> Optional[str]:
    """从内容中提取公司成立年份"""
    founding_patterns = [
        r"[Ff]ounded\s+in\s+(\d{4})",
        r"[Ee]stablished\s+in\s+(\d{4})",
        r"[Ss]ince\s+(\d{4})",
        r"成立于\s*(\d{4})",
        r"创立于\s*(\d{4})"
    ]
    
    for pattern in founding_patterns:
        matches = re.search(pattern, content)
        if matches:
            return matches.group(1)
    
    return None


def _extract_headquarters(content: str) -> Optional[str]:
    """从内容中提取公司总部位置"""
    hq_patterns = [
        r"[Hh]eadquarters?(?:\s+is|\s+are|\s+in|\s+located\s+in|\:)?\s+([A-Za-z\s\,]+(?:,\s*[A-Za-z]+)?)",
        r"[Hh]eadquarters?(?:\s+is|\s+are|\s+in|\s+located\s+in|\:)?\s+([^\.]+)",
        r"总部(?:位于|在)?\s*([^，。,\.]+)"
    ]
    
    for pattern in hq_patterns:
        matches = re.search(pattern, content)
        if matches:
            hq = matches.group(1).strip()
            if len(hq) < 100:  # 避免错误匹配过长的文本
                return hq
    
    return None


def _extract_industry(content: str) -> Optional[str]:
    """从内容中提取公司所属行业"""
    industry_patterns = [
        r"(?:in|is\s+a|is\s+an)\s+([A-Za-z\s]+)\s+(?:industry|company|corporation|business)",
        r"(?:行业|领域)(?:为|是)?\s*([^，。,\.]+)"
    ]
    
    for pattern in industry_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            industry = matches.group(1).strip()
            if 3 < len(industry) < 50:  # 避免错误匹配过短或过长的文本
                return industry
    
    return None


def _extract_employee_count(content: str) -> Optional[str]:
    """从内容中提取公司员工数量"""
    employee_patterns = [
        r"(?:approximately|about|around|over|more\s+than)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:thousand|million|billion)?\s+employees",
        r"(?:approximately|about|around|over|more\s+than)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:thousand|million|billion)?\s+staff",
        r"(?:员工|职工|雇员)(?:人数|规模|总数)(?:为|是|约)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:万|千|百)?\s*(?:人|名)"
    ]
    
    for pattern in employee_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            return matches.group(0).strip()
    
    return None


def _extract_website(content: str, company_name: str) -> Optional[str]:
    """从内容中提取公司官网"""
    # 尝试找到官网URL
    website_patterns = [
        r"(?:official\s+website|website|site)\s*(?:\:|is)?\s*(https?://[^\s\"\'<>]+)",
        rf"{company_name}(?:'s)?\s+(?:official\s+website|website|site)\s*(?:\:|is)?\s*(https?://[^\s\"\'<>]+)",
        r"(?:官网|官方网站|网址)\s*(?:为|是|:)?\s*(https?://[^\s\"\'<>]+)"
    ]
    
    for pattern in website_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            return matches.group(1).strip()
    
    # 尝试从内容中提取域名
    domain_patterns = [
        rf"(?:www\.)?{re.escape(company_name.lower().replace(' ', ''))}\.(?:com|org|net|io|co)",
        rf"(?:www\.)?{re.escape(company_name.lower().replace(' ', '-'))}\.(?:com|org|net|io|co)",
        r"www\.[a-zA-Z0-9-]+\.(?:com|org|net|io|co)"
    ]
    
    for pattern in domain_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            domain = matches.group(0)
            if not domain.startswith("http"):
                domain = "https://" + domain
            return domain
    
    return None


def _extract_social_media(content: str) -> Dict[str, str]:
    """从内容中提取公司社交媒体链接"""
    social_media = {}
    
    # 社交媒体模式
    patterns = {
        "twitter": r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)",
        "facebook": r"facebook\.com/([a-zA-Z0-9\.]+)",
        "linkedin": r"linkedin\.com/company/([a-zA-Z0-9\-]+)",
        "instagram": r"instagram\.com/([a-zA-Z0-9_\.]+)",
        "youtube": r"youtube\.com/(?:channel|user)/([a-zA-Z0-9_\-]+)"
    }
    
    for platform, pattern in patterns.items():
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            handle = matches.group(1)
            social_media[platform] = f"https://{platform}.com/{handle}"
    
    return social_media


def _extract_key_executives(content: str) -> List[Dict[str, str]]:
    """从内容中提取公司高管信息"""
    executives = []
    
    # 高管模式
    exec_patterns = [
        r"(?:CEO|Chief Executive Officer|President)(?:\s+is|\:)?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:CFO|Chief Financial Officer)(?:\s+is|\:)?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:CTO|Chief Technology Officer)(?:\s+is|\:)?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:COO|Chief Operating Officer)(?:\s+is|\:)?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:首席执行官|CEO)(?:\s+是|\:)?\s+([^\s，。,\.]+)",
        r"(?:首席财务官|CFO)(?:\s+是|\:)?\s+([^\s，。,\.]+)",
        r"(?:首席技术官|CTO)(?:\s+是|\:)?\s+([^\s，。,\.]+)",
        r"(?:首席运营官|COO)(?:\s+是|\:)?\s+([^\s，。,\.]+)"
    ]
    
    for pattern in exec_patterns:
        matches = re.search(pattern, content)
        if matches:
            title = re.search(r"(CEO|Chief Executive Officer|President|CFO|Chief Financial Officer|CTO|Chief Technology Officer|COO|Chief Operating Officer|首席执行官|首席财务官|首席技术官|首席运营官)", pattern)
            if title:
                executives.append({
                    "name": matches.group(1).strip(),
                    "title": title.group(1)
                })
    
    return executives


def _extract_products_services(content: str, company_name: str) -> List[str]:
    """从内容中提取公司产品或服务信息"""
    products_services = []
    
    # 产品服务模式
    product_patterns = [
        rf"{company_name}(?:'s)?\s+products\s+include\s+([^\.]+)",
        rf"{company_name}(?:'s)?\s+services\s+include\s+([^\.]+)",
        r"(?:products|services)(?:\s+include|\:)?\s+([^\.]+)",
        rf"{company_name}的(?:产品|服务)(?:包括|有)?\s+([^。]+)"
    ]
    
    for pattern in product_patterns:
        matches = re.search(pattern, content, re.IGNORECASE)
        if matches:
            product_text = matches.group(1).strip()
            # 处理列表形式的产品
            if "," in product_text:
                products = [p.strip() for p in product_text.split(",")]
                products_services.extend(products)
            else:
                products_services.append(product_text)
    
    return products_services[:5]  # 限制返回数量


def _assess_extraction_quality(extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """评估提取信息的质量"""
    quality = {
        "overall_score": 0,
        "fields_found": 0,
        "total_fields": len(extracted_info),
        "quality_assessment": "低"
    }
    
    # 计算有多少字段成功提取
    for key, value in extracted_info.items():
        if value and value != {} and value != []:
            quality["fields_found"] += 1
    
    # 计算总体得分
    quality["overall_score"] = int((quality["fields_found"] / quality["total_fields"]) * 100)
    
    # 评估质量
    if quality["overall_score"] >= 70:
        quality["quality_assessment"] = "高"
    elif quality["overall_score"] >= 40:
        quality["quality_assessment"] = "中"
    else:
        quality["quality_assessment"] = "低"
    
    return quality