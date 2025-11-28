"""
股票信息收集工具集

本模块提供股票信息收集所需的专用工具，包括：
1. stock_query_tool - 股票查询和基本信息获取
2. market_data_tool - 实时行情数据获取
3. financial_data_tool - 财务数据和关键指标获取
4. news_collection_tool - 股票相关新闻收集
5. cache_manager_tool - 数据缓存管理

依赖包：
- strands (framework)
- yfinance (Yahoo Finance API)
- requests (HTTP requests)
- duckduckgo-search (news search)
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from strands import tool

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


# ============================================================================
# 缓存管理工具
# ============================================================================

@tool
def cache_manager_tool(
    operation: str,
    key: str,
    value: Optional[str] = None,
    ttl_minutes: Optional[int] = None,
    cache_dir: str = ".cache/stock_information_collector"
) -> str:
    """
    缓存管理工具 - 支持数据的存储、读取、删除和清理
    
    Args:
        operation: 操作类型 (set/get/delete/clear/stats)
        key: 缓存键
        value: 缓存值（JSON字符串，仅set操作需要）
        ttl_minutes: 缓存有效期（分钟），None表示永久有效
        cache_dir: 缓存目录路径
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确保缓存目录存在
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # 生成缓存文件名（使用MD5哈希避免特殊字符）
        key_hash = hashlib.md5(key.encode()).hexdigest()
        cache_file = cache_path / f"{key_hash}.json"
        meta_file = cache_path / f"{key_hash}.meta"
        
        if operation == "set":
            if value is None:
                return json.dumps({
                    "success": False,
                    "error": "value is required for set operation"
                }, ensure_ascii=False)
            
            # 保存缓存数据
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(value)
            
            # 保存元数据
            meta = {
                "key": key,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat() if ttl_minutes else None
            }
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False)
            
            return json.dumps({
                "success": True,
                "operation": "set",
                "key": key,
                "ttl_minutes": ttl_minutes,
                "expires_at": meta["expires_at"]
            }, ensure_ascii=False)
        
        elif operation == "get":
            if not cache_file.exists() or not meta_file.exists():
                return json.dumps({
                    "success": False,
                    "error": "cache not found",
                    "key": key
                }, ensure_ascii=False)
            
            # 读取元数据检查过期
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            if meta["expires_at"]:
                expires_at = datetime.fromisoformat(meta["expires_at"])
                if datetime.now() > expires_at:
                    # 缓存已过期，删除文件
                    cache_file.unlink()
                    meta_file.unlink()
                    return json.dumps({
                        "success": False,
                        "error": "cache expired",
                        "key": key,
                        "expired_at": meta["expires_at"]
                    }, ensure_ascii=False)
            
            # 读取缓存数据
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_value = f.read()
            
            return json.dumps({
                "success": True,
                "operation": "get",
                "key": key,
                "value": cached_value,
                "created_at": meta["created_at"],
                "expires_at": meta["expires_at"]
            }, ensure_ascii=False)
        
        elif operation == "delete":
            deleted = False
            if cache_file.exists():
                cache_file.unlink()
                deleted = True
            if meta_file.exists():
                meta_file.unlink()
                deleted = True
            
            return json.dumps({
                "success": True,
                "operation": "delete",
                "key": key,
                "deleted": deleted
            }, ensure_ascii=False)
        
        elif operation == "clear":
            # 清理所有缓存
            deleted_count = 0
            for file in cache_path.glob("*"):
                file.unlink()
                deleted_count += 1
            
            return json.dumps({
                "success": True,
                "operation": "clear",
                "deleted_count": deleted_count // 2  # 每个缓存有两个文件
            }, ensure_ascii=False)
        
        elif operation == "stats":
            # 统计缓存信息
            total_count = 0
            expired_count = 0
            valid_count = 0
            total_size = 0
            
            for meta_file_path in cache_path.glob("*.meta"):
                total_count += 1
                
                with open(meta_file_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                cache_file_path = meta_file_path.with_suffix('.json')
                if cache_file_path.exists():
                    total_size += cache_file_path.stat().st_size
                
                if meta["expires_at"]:
                    expires_at = datetime.fromisoformat(meta["expires_at"])
                    if datetime.now() > expires_at:
                        expired_count += 1
                    else:
                        valid_count += 1
                else:
                    valid_count += 1
            
            return json.dumps({
                "success": True,
                "operation": "stats",
                "total_count": total_count,
                "valid_count": valid_count,
                "expired_count": expired_count,
                "total_size_bytes": total_size,
                "cache_dir": str(cache_path)
            }, ensure_ascii=False)
        
        else:
            return json.dumps({
                "success": False,
                "error": f"unknown operation: {operation}",
                "supported_operations": ["set", "get", "delete", "clear", "stats"]
            }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "operation": operation
        }, ensure_ascii=False)


# ============================================================================
# 股票查询工具
# ============================================================================

@tool
def stock_query_tool(
    query: str,
    market: Optional[str] = None,
    query_type: str = "auto"
) -> str:
    """
    股票查询工具 - 识别股票并获取基本信息
    
    支持通过股票代码或名称查询，支持A股、港股、美股市场
    
    Args:
        query: 股票代码或名称（如：AAPL、苹果、000001、平安银行）
        market: 市场类型 (A股/港股/美股/auto)，auto表示自动识别
        query_type: 查询类型 (symbol/name/auto)，auto表示自动识别
        
    Returns:
        str: JSON格式的股票基本信息
    """
    try:
        if yf is None:
            return json.dumps({
                "success": False,
                "error": "yfinance package not installed. Please install: pip install yfinance"
            }, ensure_ascii=False)
        
        # 检查缓存
        cache_key = f"stock_basic_info:{query}:{market}"
        cache_result = cache_manager_tool("get", cache_key)
        cache_data = json.loads(cache_result)
        
        if cache_data["success"]:
            cached_info = json.loads(cache_data["value"])
            cached_info["from_cache"] = True
            return json.dumps(cached_info, ensure_ascii=False)
        
        # 规范化股票代码
        symbol = _normalize_stock_symbol(query, market)
        
        # 使用yfinance获取股票信息
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if not info or 'symbol' not in info:
            return json.dumps({
                "success": False,
                "error": "stock not found",
                "query": query,
                "symbol": symbol
            }, ensure_ascii=False)
        
        # 提取基本信息
        basic_info = {
            "success": True,
            "symbol": info.get('symbol', symbol),
            "name": info.get('longName', info.get('shortName', 'N/A')),
            "full_name": info.get('longName', 'N/A'),
            "market": _identify_market(symbol),
            "exchange": info.get('exchange', 'N/A'),
            "currency": info.get('currency', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "sector": info.get('sector', 'N/A'),
            "market_cap": info.get('marketCap', 0),
            "market_cap_formatted": _format_large_number(info.get('marketCap', 0)),
            "description": info.get('longBusinessSummary', 'N/A'),
            "website": info.get('website', 'N/A'),
            "employees": info.get('fullTimeEmployees', 'N/A'),
            "country": info.get('country', 'N/A'),
            "city": info.get('city', 'N/A'),
            "query_time": datetime.now().isoformat(),
            "from_cache": False
        }
        
        # 缓存基本信息（24小时）
        cache_manager_tool(
            "set",
            cache_key,
            json.dumps(basic_info, ensure_ascii=False),
            ttl_minutes=1440  # 24小时
        )
        
        return json.dumps(basic_info, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query,
            "market": market
        }, ensure_ascii=False)


# ============================================================================
# 行情数据工具
# ============================================================================

@tool
def market_data_tool(
    symbol: str,
    market: Optional[str] = None
) -> str:
    """
    行情数据工具 - 获取股票实时行情数据
    
    Args:
        symbol: 股票代码
        market: 市场类型 (A股/港股/美股/auto)
        
    Returns:
        str: JSON格式的行情数据
    """
    try:
        if yf is None:
            return json.dumps({
                "success": False,
                "error": "yfinance package not installed"
            }, ensure_ascii=False)
        
        # 检查缓存（15分钟）
        cache_key = f"market_data:{symbol}"
        cache_result = cache_manager_tool("get", cache_key)
        cache_data = json.loads(cache_result)
        
        if cache_data["success"]:
            cached_data = json.loads(cache_data["value"])
            cached_data["from_cache"] = True
            return json.dumps(cached_data, ensure_ascii=False)
        
        # 规范化股票代码
        normalized_symbol = _normalize_stock_symbol(symbol, market)
        
        # 获取股票对象
        stock = yf.Ticker(normalized_symbol)
        info = stock.info
        
        if not info:
            return json.dumps({
                "success": False,
                "error": "failed to fetch market data",
                "symbol": symbol
            }, ensure_ascii=False)
        
        # 获取历史数据（最近2天）
        hist = stock.history(period="2d")
        
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        previous_close = info.get('previousClose', info.get('regularMarketPreviousClose', 0))
        
        # 计算涨跌
        if previous_close and previous_close > 0:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
        else:
            change = 0
            change_percent = 0
        
        market_data = {
            "success": True,
            "symbol": normalized_symbol,
            "current_price": current_price,
            "previous_close": previous_close,
            "open_price": info.get('open', info.get('regularMarketOpen', 0)),
            "day_high": info.get('dayHigh', info.get('regularMarketDayHigh', 0)),
            "day_low": info.get('dayLow', info.get('regularMarketDayLow', 0)),
            "volume": info.get('volume', info.get('regularMarketVolume', 0)),
            "volume_formatted": _format_large_number(info.get('volume', 0)),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "market_cap": info.get('marketCap', 0),
            "market_cap_formatted": _format_large_number(info.get('marketCap', 0)),
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 0),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow', 0),
            "average_volume": info.get('averageVolume', 0),
            "market_state": info.get('marketState', 'REGULAR'),
            "currency": info.get('currency', 'USD'),
            "timestamp": datetime.now().isoformat(),
            "from_cache": False
        }
        
        # 缓存行情数据（15分钟）
        cache_manager_tool(
            "set",
            cache_key,
            json.dumps(market_data, ensure_ascii=False),
            ttl_minutes=15
        )
        
        return json.dumps(market_data, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "symbol": symbol
        }, ensure_ascii=False)


# ============================================================================
# 财务数据工具
# ============================================================================

@tool
def financial_data_tool(
    symbol: str,
    market: Optional[str] = None
) -> str:
    """
    财务数据工具 - 获取股票财务数据和关键指标
    
    Args:
        symbol: 股票代码
        market: 市场类型 (A股/港股/美股/auto)
        
    Returns:
        str: JSON格式的财务数据
    """
    try:
        if yf is None:
            return json.dumps({
                "success": False,
                "error": "yfinance package not installed"
            }, ensure_ascii=False)
        
        # 检查缓存（7天）
        cache_key = f"financial_data:{symbol}"
        cache_result = cache_manager_tool("get", cache_key)
        cache_data = json.loads(cache_result)
        
        if cache_data["success"]:
            cached_data = json.loads(cache_data["value"])
            cached_data["from_cache"] = True
            return json.dumps(cached_data, ensure_ascii=False)
        
        # 规范化股票代码
        normalized_symbol = _normalize_stock_symbol(symbol, market)
        
        # 获取股票对象
        stock = yf.Ticker(normalized_symbol)
        info = stock.info
        
        if not info:
            return json.dumps({
                "success": False,
                "error": "failed to fetch financial data",
                "symbol": symbol
            }, ensure_ascii=False)
        
        # 提取财务数据
        financial_data = {
            "success": True,
            "symbol": normalized_symbol,
            "valuation_metrics": {
                "pe_ratio": info.get('trailingPE', info.get('forwardPE', 'N/A')),
                "pb_ratio": info.get('priceToBook', 'N/A'),
                "ps_ratio": info.get('priceToSalesTrailing12Months', 'N/A'),
                "peg_ratio": info.get('pegRatio', 'N/A'),
                "enterprise_value": info.get('enterpriseValue', 'N/A'),
                "ev_to_revenue": info.get('enterpriseToRevenue', 'N/A'),
                "ev_to_ebitda": info.get('enterpriseToEbitda', 'N/A')
            },
            "profitability_metrics": {
                "profit_margin": info.get('profitMargins', 'N/A'),
                "operating_margin": info.get('operatingMargins', 'N/A'),
                "gross_margin": info.get('grossMargins', 'N/A'),
                "roe": info.get('returnOnEquity', 'N/A'),
                "roa": info.get('returnOnAssets', 'N/A')
            },
            "financial_health": {
                "total_revenue": info.get('totalRevenue', 'N/A'),
                "revenue_formatted": _format_large_number(info.get('totalRevenue', 0)),
                "net_income": info.get('netIncomeToCommon', 'N/A'),
                "net_income_formatted": _format_large_number(info.get('netIncomeToCommon', 0)),
                "total_cash": info.get('totalCash', 'N/A'),
                "total_debt": info.get('totalDebt', 'N/A'),
                "debt_to_equity": info.get('debtToEquity', 'N/A'),
                "current_ratio": info.get('currentRatio', 'N/A'),
                "quick_ratio": info.get('quickRatio', 'N/A')
            },
            "growth_metrics": {
                "revenue_growth": info.get('revenueGrowth', 'N/A'),
                "earnings_growth": info.get('earningsGrowth', 'N/A'),
                "earnings_quarterly_growth": info.get('earningsQuarterlyGrowth', 'N/A')
            },
            "dividend_info": {
                "dividend_rate": info.get('dividendRate', 'N/A'),
                "dividend_yield": info.get('dividendYield', 'N/A'),
                "payout_ratio": info.get('payoutRatio', 'N/A'),
                "ex_dividend_date": info.get('exDividendDate', 'N/A')
            },
            "analyst_data": {
                "target_mean_price": info.get('targetMeanPrice', 'N/A'),
                "target_high_price": info.get('targetHighPrice', 'N/A'),
                "target_low_price": info.get('targetLowPrice', 'N/A'),
                "recommendation_mean": info.get('recommendationMean', 'N/A'),
                "recommendation_key": info.get('recommendationKey', 'N/A'),
                "number_of_analyst_opinions": info.get('numberOfAnalystOpinions', 'N/A')
            },
            "report_period": info.get('mostRecentQuarter', 'N/A'),
            "fiscal_year_end": info.get('lastFiscalYearEnd', 'N/A'),
            "timestamp": datetime.now().isoformat(),
            "from_cache": False
        }
        
        # 缓存财务数据（7天）
        cache_manager_tool(
            "set",
            cache_key,
            json.dumps(financial_data, ensure_ascii=False),
            ttl_minutes=10080  # 7天
        )
        
        return json.dumps(financial_data, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "symbol": symbol
        }, ensure_ascii=False)


# ============================================================================
# 新闻收集工具
# ============================================================================

@tool
def news_collection_tool(
    symbol: str,
    company_name: Optional[str] = None,
    max_results: int = 10,
    days: int = 7
) -> str:
    """
    新闻收集工具 - 收集股票相关的新闻资讯
    
    Args:
        symbol: 股票代码
        company_name: 公司名称（可选，用于增强搜索）
        max_results: 最大新闻数量
        days: 收集最近几天的新闻
        
    Returns:
        str: JSON格式的新闻列表
    """
    try:
        # 检查缓存（1小时）
        cache_key = f"news:{symbol}:{days}"
        cache_result = cache_manager_tool("get", cache_key)
        cache_data = json.loads(cache_result)
        
        if cache_data["success"]:
            cached_news = json.loads(cache_data["value"])
            cached_news["from_cache"] = True
            return json.dumps(cached_news, ensure_ascii=False)
        
        news_items = []
        
        # 方法1: 使用yfinance获取新闻
        if yf is not None:
            try:
                stock = yf.Ticker(symbol)
                yf_news = stock.news
                
                if yf_news:
                    for item in yf_news[:max_results]:
                        news_items.append({
                            "title": item.get('title', ''),
                            "publisher": item.get('publisher', 'Unknown'),
                            "link": item.get('link', ''),
                            "publish_time": datetime.fromtimestamp(item.get('providerPublishTime', 0)).isoformat() if item.get('providerPublishTime') else 'N/A',
                            "type": item.get('type', 'NEWS'),
                            "source": "Yahoo Finance"
                        })
            except Exception as e:
                print(f"Error fetching news from yfinance: {e}")
        
        # 方法2: 使用DuckDuckGo搜索新闻
        if DDGS is not None and len(news_items) < max_results:
            try:
                search_query = f"{symbol} stock news"
                if company_name:
                    search_query = f"{company_name} {symbol} stock news"
                
                ddgs = DDGS()
                ddg_results = ddgs.news(search_query, max_results=max_results)
                
                for item in ddg_results:
                    if len(news_items) >= max_results:
                        break
                    
                    news_items.append({
                        "title": item.get('title', ''),
                        "body": item.get('body', ''),
                        "url": item.get('url', ''),
                        "publish_time": item.get('date', 'N/A'),
                        "source": item.get('source', 'DuckDuckGo News')
                    })
            except Exception as e:
                print(f"Error fetching news from DuckDuckGo: {e}")
        
        # 按时间排序（最新的在前）
        news_items.sort(key=lambda x: x.get('publish_time', ''), reverse=True)
        
        news_data = {
            "success": True,
            "symbol": symbol,
            "company_name": company_name,
            "news_count": len(news_items),
            "news_items": news_items[:max_results],
            "collected_at": datetime.now().isoformat(),
            "from_cache": False
        }
        
        # 缓存新闻数据（1小时）
        cache_manager_tool(
            "set",
            cache_key,
            json.dumps(news_data, ensure_ascii=False),
            ttl_minutes=60
        )
        
        return json.dumps(news_data, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "symbol": symbol
        }, ensure_ascii=False)


# ============================================================================
# 辅助函数
# ============================================================================

def _normalize_stock_symbol(query: str, market: Optional[str] = None) -> str:
    """
    规范化股票代码
    
    Args:
        query: 原始查询（股票代码或名称）
        market: 市场类型
        
    Returns:
        str: 规范化的股票代码
    """
    query = query.strip().upper()
    
    # 如果已经是完整的Yahoo Finance代码格式，直接返回
    if '.' in query or '^' in query:
        return query
    
    # A股代码处理
    if query.isdigit() and len(query) == 6:
        # 上交所：60开头
        if query.startswith('60'):
            return f"{query}.SS"
        # 深交所：00、30开头
        elif query.startswith('00') or query.startswith('30'):
            return f"{query}.SZ"
    
    # 港股代码处理
    if query.isdigit() and len(query) <= 5:
        # 补齐到5位
        padded = query.zfill(5)
        return f"{padded}.HK"
    
    # 美股代码通常是字母
    if query.isalpha():
        return query
    
    # 默认返回原始查询
    return query


def _identify_market(symbol: str) -> str:
    """
    识别股票所属市场
    
    Args:
        symbol: 股票代码
        
    Returns:
        str: 市场类型
    """
    if '.SS' in symbol or '.SZ' in symbol:
        return 'A股'
    elif '.HK' in symbol:
        return '港股'
    else:
        return '美股'


def _format_large_number(num: Union[int, float]) -> str:
    """
    格式化大数字（如市值）
    
    Args:
        num: 数字
        
    Returns:
        str: 格式化后的字符串
    """
    if not isinstance(num, (int, float)) or num == 0:
        return 'N/A'
    
    if num >= 1_000_000_000_000:  # 万亿
        return f"{num / 1_000_000_000_000:.2f}万亿"
    elif num >= 1_000_000_000:  # 十亿
        return f"{num / 1_000_000_000:.2f}亿"
    elif num >= 1_000_000:  # 百万
        return f"{num / 1_000_000:.2f}百万"
    else:
        return f"{num:,.0f}"
