#!/usr/bin/env python3
"""
多搜索引擎工具主文件
提供统一的搜索接口，支持多个搜索引擎，自动适配网络环境
"""

from strands import tool
import json
import time
from typing import Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入子模块
from .engine_adapters import ENGINE_ADAPTERS
from .environment_detector import _detect_best_engine, batch_check_engines
from .result_formatter import _standardize_results, _format_results
from .exceptions import SearchEngineError, ValidationError


@tool
def search(
    query: str,
    engine: str = 'auto',
    num_results: int = 10,
    language: str = 'auto',
    region: str = 'auto',
    timeout: int = 15,
    format: str = 'json',
    include_metadata: bool = True
) -> str:
    """
    统一的搜索接口，支持多个搜索引擎，自动适配网络环境
    
    Args:
        query: 搜索关键词或查询语句
        engine: 指定搜索引擎（baidu/sogou/so360/google/bing/duckduckgo/auto），默认为auto自动选择
        num_results: 返回的搜索结果数量，范围1-20，默认为10
        language: 搜索结果语言偏好（zh-CN/en-US/auto），默认为auto
        region: 地区提示（china/overseas/auto），用于优化搜索引擎选择策略，默认为auto
        timeout: 搜索超时时间（秒），范围5-30，默认为15
        format: 输出格式（json/markdown/text），默认为json
        include_metadata: 是否包含元数据（搜索时间、引擎信息等），默认为true
        
    Returns:
        str: JSON字符串，包含搜索结果列表和元数据
    """
    start_time = time.time()
    
    try:
        # 参数验证
        if not query or not query.strip():
            return json.dumps({
                'status': 'error',
                'error_type': 'ValidationError',
                'message': '搜索关键词不能为空'
            }, ensure_ascii=False, indent=2)
        
        if num_results < 1 or num_results > 20:
            return json.dumps({
                'status': 'error',
                'error_type': 'ValidationError',
                'message': 'num_results必须在1-20之间'
            }, ensure_ascii=False, indent=2)
        
        if timeout < 5 or timeout > 30:
            return json.dumps({
                'status': 'error',
                'error_type': 'ValidationError',
                'message': 'timeout必须在5-30秒之间'
            }, ensure_ascii=False, indent=2)
        
        # 自动选择引擎
        original_engine = engine
        if engine == 'auto':
            logger.info(f"开始自动选择搜索引擎（region={region}, language={language}）")
            engine = _detect_best_engine(region, language)
            logger.info(f"自动选择的搜索引擎: {engine}")
        
        # 验证引擎是否支持
        if engine not in ENGINE_ADAPTERS:
            available_engines = ', '.join(ENGINE_ADAPTERS.keys())
            return json.dumps({
                'status': 'error',
                'error_type': 'ValidationError',
                'message': f'不支持的搜索引擎: {engine}。可用的引擎: {available_engines}'
            }, ensure_ascii=False, indent=2)
        
        # 执行搜索（带重试机制）
        search_func = ENGINE_ADAPTERS[engine]
        engines_tried = [engine]
        raw_results = None
        last_error = None
        
        for attempt in range(3):  # 最多尝试3个引擎
            try:
                logger.info(f"使用引擎 {engine} 搜索: {query}")
                raw_results = search_func(query, num_results, timeout)
                
                if raw_results:
                    logger.info(f"搜索成功，获得 {len(raw_results)} 个结果")
                    break
                else:
                    logger.warning(f"引擎 {engine} 返回空结果")
                    
            except SearchEngineError as e:
                last_error = e
                logger.warning(f"引擎 {engine} 搜索失败: {e.message}")
                
                # 如果是自动模式且还有其他引擎可尝试，切换引擎
                if original_engine == 'auto' and attempt < 2:
                    # 选择一个未尝试过的引擎
                    for fallback_engine in ENGINE_ADAPTERS.keys():
                        if fallback_engine not in engines_tried:
                            engine = fallback_engine
                            engines_tried.append(engine)
                            search_func = ENGINE_ADAPTERS[engine]
                            logger.info(f"切换到备用引擎: {engine}")
                            break
                    else:
                        # 没有更多引擎可尝试
                        break
                else:
                    # 非自动模式或已经尝试过所有引擎
                    break
        
        # 检查是否获得结果
        if not raw_results:
            error_message = last_error.message if last_error else "搜索未返回任何结果"
            return json.dumps({
                'status': 'error',
                'error_type': 'SearchError',
                'engine': engine,
                'engines_tried': engines_tried,
                'message': error_message
            }, ensure_ascii=False, indent=2)
        
        # 标准化结果
        standardized_results = _standardize_results(raw_results, engine)
        
        # 计算搜索耗时
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # 格式化输出
        return _format_results(
            results=standardized_results,
            format_type=format,
            query=query,
            engine=engine,
            include_metadata=include_metadata,
            search_time_ms=search_time_ms
        )
        
    except ValidationError as e:
        return json.dumps({
            'status': 'error',
            'error_type': 'ValidationError',
            'message': e.message
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"搜索过程中发生未预期的错误: {e}", exc_info=True)
        return json.dumps({
            'status': 'error',
            'error_type': 'UnknownError',
            'message': f'搜索失败: {str(e)}'
        }, ensure_ascii=False, indent=2)


@tool
def check_engine_health(engines: str = '', check_timeout: int = 5) -> str:
    """
    检查搜索引擎的可用性和响应时间
    
    Args:
        engines: 需要检查的搜索引擎列表，JSON数组字符串格式（如：'["baidu", "google"]'），为空时检查所有支持的引擎
        check_timeout: 每个引擎的检查超时时间（秒），默认为5
        
    Returns:
        str: JSON字符串，包含各搜索引擎健康状态
    """
    try:
        # 解析engines参数
        if engines and engines.strip():
            try:
                engines_list = json.loads(engines)
                if not isinstance(engines_list, list):
                    return json.dumps({
                        'status': 'error',
                        'message': 'engines参数必须是JSON数组字符串'
                    }, ensure_ascii=False, indent=2)
            except json.JSONDecodeError as e:
                return json.dumps({
                    'status': 'error',
                    'message': f'engines参数格式错误: {str(e)}'
                }, ensure_ascii=False, indent=2)
        else:
            engines_list = None  # 检查所有引擎
        
        # 验证超时时间
        if check_timeout < 1 or check_timeout > 30:
            return json.dumps({
                'status': 'error',
                'message': 'check_timeout必须在1-30秒之间'
            }, ensure_ascii=False, indent=2)
        
        # 执行批量检查
        logger.info(f"开始健康检查（引擎: {engines_list or '全部'}）")
        results = batch_check_engines(engines_list, check_timeout)
        
        # 统计可用引擎数量
        available_count = sum(1 for r in results if r['available'])
        total_count = len(results)
        
        return json.dumps({
            'status': 'success',
            'check_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'summary': {
                'total_engines': total_count,
                'available_engines': available_count,
                'unavailable_engines': total_count - available_count
            },
            'engines_status': results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return json.dumps({
            'status': 'error',
            'message': f'健康检查失败: {str(e)}'
        }, ensure_ascii=False, indent=2)


@tool
def filter_and_sort_results(
    results_json: str,
    filter_keywords: str = '',
    exclude_keywords: str = '',
    sort_by: str = 'relevance',
    deduplicate: bool = True
) -> str:
    """
    对搜索结果进行过滤和自定义排序
    
    Args:
        results_json: 待处理的搜索结果JSON字符串（来自search函数的返回值）
        filter_keywords: 过滤关键词列表，JSON数组字符串格式（如：'["AI", "机器学习"]'），只返回包含这些关键词的结果
        exclude_keywords: 排除关键词列表，JSON数组字符串格式，过滤掉包含这些关键词的结果
        sort_by: 排序方式（relevance/date/random），默认为relevance
        deduplicate: 是否去除重复结果（基于URL），默认为true
        
    Returns:
        str: JSON字符串，包含过滤和排序后的搜索结果
    """
    try:
        # 解析输入的搜索结果
        try:
            data = json.loads(results_json)
        except json.JSONDecodeError as e:
            return json.dumps({
                'status': 'error',
                'message': f'results_json解析失败: {str(e)}'
            }, ensure_ascii=False, indent=2)
        
        # 提取结果列表
        if 'results' not in data:
            return json.dumps({
                'status': 'error',
                'message': 'results_json中缺少results字段'
            }, ensure_ascii=False, indent=2)
        
        results = data['results']
        original_count = len(results)
        
        # 解析过滤关键词
        filter_kw = []
        if filter_keywords and filter_keywords.strip():
            try:
                filter_kw = json.loads(filter_keywords)
                if not isinstance(filter_kw, list):
                    filter_kw = []
            except json.JSONDecodeError:
                logger.warning(f"filter_keywords解析失败，忽略过滤")
        
        exclude_kw = []
        if exclude_keywords and exclude_keywords.strip():
            try:
                exclude_kw = json.loads(exclude_keywords)
                if not isinstance(exclude_kw, list):
                    exclude_kw = []
            except json.JSONDecodeError:
                logger.warning(f"exclude_keywords解析失败，忽略排除")
        
        # 应用过滤条件
        if filter_kw:
            logger.info(f"应用包含过滤: {filter_kw}")
            results = [
                r for r in results
                if any(kw.lower() in (r.get('title', '') + r.get('snippet', '')).lower() 
                      for kw in filter_kw)
            ]
        
        if exclude_kw:
            logger.info(f"应用排除过滤: {exclude_kw}")
            results = [
                r for r in results
                if not any(kw.lower() in (r.get('title', '') + r.get('snippet', '')).lower() 
                          for kw in exclude_kw)
            ]
        
        # 去重
        if deduplicate:
            logger.info("应用去重")
            seen_urls = set()
            unique_results = []
            for r in results:
                url = r.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)
            results = unique_results
        
        # 排序
        if sort_by == 'random':
            import random
            logger.info("应用随机排序")
            random.shuffle(results)
        elif sort_by == 'date':
            # 简单实现：保持原序（实际需要从snippet中提取日期）
            logger.info("应用日期排序（当前保持原序）")
            pass
        # relevance: 保持原序
        
        # 更新排名
        for idx, result in enumerate(results, 1):
            result['rank'] = idx
        
        filtered_count = len(results)
        
        return json.dumps({
            'status': 'success',
            'original_count': original_count,
            'filtered_count': filtered_count,
            'removed_count': original_count - filtered_count,
            'filters_applied': {
                'filter_keywords': filter_kw,
                'exclude_keywords': exclude_kw,
                'deduplicate': deduplicate,
                'sort_by': sort_by
            },
            'results': results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"过滤和排序失败: {e}", exc_info=True)
        return json.dumps({
            'status': 'error',
            'message': f'处理失败: {str(e)}'
        }, ensure_ascii=False, indent=2)
