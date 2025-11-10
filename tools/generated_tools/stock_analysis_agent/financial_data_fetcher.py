#!/usr/bin/env python3
"""
财报数据抓取工具

提供从多个数据源抓取股票财报数据的功能，支持自动格式转换、验证和缓存管理
"""

import json
import os
import time
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认缓存目录
DEFAULT_CACHE_DIR = ".cache/stock_analysis_agent"
os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)


@tool
def fetch_financial_statements(symbol: str, statement_type: str = "income", period: str = "annual") -> str:
    """
    获取公司财务报表数据
    
    支持从多个API源获取财务报表数据，包括损益表、资产负债表和现金流量表。
    优先使用缓存数据，如果缓存不存在或已过期则从API获取。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL" 或 "600000.SS"
        statement_type (str): 报表类型，可选值: "income"(损益表), "balance"(资产负债表), "cash"(现金流量表)
        period (str): 期间类型，可选值: "annual"(年度), "quarterly"(季度)
    
    Returns:
        str: JSON格式的财务报表数据
    """
    try:
        # 检查缓存
        cache_key = f"financial_statements_{symbol}_{statement_type}_{period}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached
        
        # 从API获取数据 - 使用Alpha Vantage API
        import requests
        
        # 映射statement_type到API参数
        function_map = {
            "income": "INCOME_STATEMENT",
            "balance": "BALANCE_SHEET",
            "cash": "CASH_FLOW"
        }
        
        function = function_map.get(statement_type, "INCOME_STATEMENT")
        
        # 尝试从环境变量获取API密钥
        api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
        
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": function,
            "symbol": symbol,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 检查API响应
        if "Error Message" in data:
            return json.dumps({
                "success": False,
                "error": data["Error Message"],
                "symbol": symbol
            }, ensure_ascii=False, indent=2)
        
        # 提取报表数据
        reports_key = "annualReports" if period == "annual" else "quarterlyReports"
        reports = data.get(reports_key, [])
        
        result = {
            "success": True,
            "symbol": symbol,
            "statement_type": statement_type,
            "period": period,
            "currency": "USD",
            "reports": reports,
            "data_source": "Alpha Vantage",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=24)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取财务报表时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取财务报表失败: {str(e)}",
            "symbol": symbol,
            "statement_type": statement_type
        }, ensure_ascii=False, indent=2)


@tool
def fetch_company_overview(symbol: str) -> str:
    """
    获取公司概览信息
    
    获取公司的基本信息，包括行业、市值、PE比率、股息率等关键指标。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL" 或 "TSLA"
    
    Returns:
        str: JSON格式的公司概览数据
    """
    try:
        # 检查缓存
        cache_key = f"company_overview_{symbol}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached
        
        # 从API获取数据
        import requests
        
        api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
        
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 检查API响应
        if not data or "Symbol" not in data:
            return json.dumps({
                "success": False,
                "error": "无法获取公司信息或股票代码无效",
                "symbol": symbol
            }, ensure_ascii=False, indent=2)
        
        result = {
            "success": True,
            "symbol": symbol,
            "company_name": data.get("Name", ""),
            "description": data.get("Description", ""),
            "sector": data.get("Sector", ""),
            "industry": data.get("Industry", ""),
            "market_cap": data.get("MarketCapitalization", ""),
            "pe_ratio": data.get("PERatio", ""),
            "peg_ratio": data.get("PEGRatio", ""),
            "book_value": data.get("BookValue", ""),
            "dividend_per_share": data.get("DividendPerShare", ""),
            "dividend_yield": data.get("DividendYield", ""),
            "eps": data.get("EPS", ""),
            "revenue_per_share": data.get("RevenuePerShareTTM", ""),
            "profit_margin": data.get("ProfitMargin", ""),
            "operating_margin": data.get("OperatingMarginTTM", ""),
            "return_on_assets": data.get("ReturnOnAssetsTTM", ""),
            "return_on_equity": data.get("ReturnOnEquityTTM", ""),
            "revenue": data.get("RevenueTTM", ""),
            "gross_profit": data.get("GrossProfitTTM", ""),
            "ebitda": data.get("EBITDA", ""),
            "beta": data.get("Beta", ""),
            "52_week_high": data.get("52WeekHigh", ""),
            "52_week_low": data.get("52WeekLow", ""),
            "50_day_moving_avg": data.get("50DayMovingAverage", ""),
            "200_day_moving_avg": data.get("200DayMovingAverage", ""),
            "shares_outstanding": data.get("SharesOutstanding", ""),
            "data_source": "Alpha Vantage",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=24)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取公司概览时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取公司概览失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def fetch_earnings_data(symbol: str) -> str:
    """
    获取公司盈利数据
    
    获取公司的历史盈利数据，包括每股收益(EPS)和盈利预期。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL"
    
    Returns:
        str: JSON格式的盈利数据
    """
    try:
        # 检查缓存
        cache_key = f"earnings_{symbol}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached
        
        # 从API获取数据
        import requests
        
        api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
        
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "EARNINGS",
            "symbol": symbol,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 检查API响应
        if "Error Message" in data:
            return json.dumps({
                "success": False,
                "error": data["Error Message"],
                "symbol": symbol
            }, ensure_ascii=False, indent=2)
        
        result = {
            "success": True,
            "symbol": symbol,
            "annual_earnings": data.get("annualEarnings", []),
            "quarterly_earnings": data.get("quarterlyEarnings", []),
            "data_source": "Alpha Vantage",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=24)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取盈利数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取盈利数据失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def fetch_analyst_estimates(symbol: str) -> str:
    """
    获取华尔街分析师预测数据
    
    获取券商分析师对公司未来盈利的预测数据。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL"
    
    Returns:
        str: JSON格式的分析师预测数据
    """
    try:
        # 检查缓存
        cache_key = f"analyst_estimates_{symbol}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached
        
        # 从Yahoo Finance获取数据
        import requests
        
        # Yahoo Finance API
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {
            "modules": "earningsTrend,financialData,recommendationTrend"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 提取相关数据
        quote_summary = data.get("quoteSummary", {})
        result_data = quote_summary.get("result", [])
        
        if not result_data:
            return json.dumps({
                "success": False,
                "error": "无法获取分析师预测数据",
                "symbol": symbol
            }, ensure_ascii=False, indent=2)
        
        result_info = result_data[0]
        
        result = {
            "success": True,
            "symbol": symbol,
            "earnings_trend": result_info.get("earningsTrend", {}),
            "financial_data": result_info.get("financialData", {}),
            "recommendation_trend": result_info.get("recommendationTrend", {}),
            "data_source": "Yahoo Finance",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=24)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取分析师预测时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取分析师预测失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def fetch_market_data(symbol: str, interval: str = "1d", range_period: str = "1y") -> str:
    """
    获取股票市场数据
    
    获取股票的历史价格数据，包括开盘价、收盘价、最高价、最低价和交易量。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL"
        interval (str): 数据间隔，可选值: "1d"(日), "1wk"(周), "1mo"(月)
        range_period (str): 时间范围，可选值: "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
    
    Returns:
        str: JSON格式的市场数据
    """
    try:
        # 检查缓存
        cache_key = f"market_data_{symbol}_{interval}_{range_period}"
        cached = _get_from_cache(cache_key, expiration_hours=1)  # 市场数据缓存1小时
        if cached:
            return cached
        
        # 从Yahoo Finance获取数据
        import requests
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": interval,
            "range": range_period
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 提取价格数据
        chart = data.get("chart", {})
        result_data = chart.get("result", [])
        
        if not result_data:
            return json.dumps({
                "success": False,
                "error": "无法获取市场数据",
                "symbol": symbol
            }, ensure_ascii=False, indent=2)
        
        chart_data = result_data[0]
        timestamps = chart_data.get("timestamp", [])
        indicators = chart_data.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]
        
        # 格式化数据
        price_data = []
        for i, ts in enumerate(timestamps):
            price_data.append({
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                "timestamp": ts,
                "open": quote.get("open", [])[i] if i < len(quote.get("open", [])) else None,
                "high": quote.get("high", [])[i] if i < len(quote.get("high", [])) else None,
                "low": quote.get("low", [])[i] if i < len(quote.get("low", [])) else None,
                "close": quote.get("close", [])[i] if i < len(quote.get("close", [])) else None,
                "volume": quote.get("volume", [])[i] if i < len(quote.get("volume", [])) else None
            })
        
        result = {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "range": range_period,
            "currency": chart_data.get("meta", {}).get("currency", "USD"),
            "exchange": chart_data.get("meta", {}).get("exchangeName", ""),
            "data_count": len(price_data),
            "price_data": price_data,
            "data_source": "Yahoo Finance",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=1)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取市场数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取市场数据失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def validate_financial_data(data: str) -> str:
    """
    验证财务数据的完整性和有效性
    
    检查财务数据是否包含必需的字段，数值是否在合理范围内。
    
    Args:
        data (str): JSON格式的财务数据
    
    Returns:
        str: JSON格式的验证结果
    """
    try:
        # 解析数据
        financial_data = json.loads(data)
        
        validation_result = {
            "success": True,
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "completeness_score": 0.0
        }
        
        # 检查必需字段
        required_fields = ["symbol", "success"]
        missing_fields = []
        
        for field in required_fields:
            if field not in financial_data:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result["errors"].append(f"缺少必需字段: {', '.join(missing_fields)}")
            validation_result["is_valid"] = False
        
        # 检查数据类型
        if "reports" in financial_data:
            reports = financial_data.get("reports", [])
            if not isinstance(reports, list):
                validation_result["errors"].append("reports字段应为数组类型")
                validation_result["is_valid"] = False
            elif len(reports) == 0:
                validation_result["warnings"].append("reports数组为空")
        
        # 计算完整性得分
        expected_fields = ["symbol", "success", "reports", "currency", "timestamp"]
        present_fields = sum(1 for field in expected_fields if field in financial_data)
        validation_result["completeness_score"] = round(present_fields / len(expected_fields), 2)
        
        # 检查数值合理性
        if "reports" in financial_data and isinstance(financial_data["reports"], list):
            for i, report in enumerate(financial_data["reports"]):
                # 检查负债率是否异常
                total_assets = float(report.get("totalAssets", 0) or 0)
                total_liabilities = float(report.get("totalLiabilities", 0) or 0)
                
                if total_assets > 0:
                    debt_ratio = total_liabilities / total_assets
                    if debt_ratio > 0.9:
                        validation_result["warnings"].append(
                            f"报告 {i+1}: 负债率过高 ({debt_ratio:.2%})"
                        )
        
        return json.dumps(validation_result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "is_valid": False,
            "error": f"数据格式错误: {str(e)}"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"验证财务数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "is_valid": False,
            "error": f"验证失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def fetch_key_metrics(symbol: str) -> str:
    """
    获取公司关键财务指标
    
    提取和计算公司的关键财务指标，包括盈利能力、偿债能力、运营效率等指标。
    
    Args:
        symbol (str): 股票代码，例如 "AAPL"
    
    Returns:
        str: JSON格式的关键财务指标
    """
    try:
        # 获取公司概览数据
        overview_json = fetch_company_overview(symbol)
        overview = json.loads(overview_json)
        
        if not overview.get("success"):
            return overview_json
        
        # 提取关键指标
        result = {
            "success": True,
            "symbol": symbol,
            "valuation_metrics": {
                "pe_ratio": _safe_float(overview.get("pe_ratio")),
                "peg_ratio": _safe_float(overview.get("peg_ratio")),
                "price_to_book": _safe_float(overview.get("book_value")),
                "dividend_yield": _safe_float(overview.get("dividend_yield"))
            },
            "profitability_metrics": {
                "profit_margin": _safe_float(overview.get("profit_margin")),
                "operating_margin": _safe_float(overview.get("operating_margin")),
                "return_on_assets": _safe_float(overview.get("return_on_assets")),
                "return_on_equity": _safe_float(overview.get("return_on_equity")),
                "eps": _safe_float(overview.get("eps"))
            },
            "growth_metrics": {
                "revenue_ttm": _safe_float(overview.get("revenue")),
                "gross_profit_ttm": _safe_float(overview.get("gross_profit")),
                "ebitda": _safe_float(overview.get("ebitda"))
            },
            "risk_metrics": {
                "beta": _safe_float(overview.get("beta")),
                "52_week_high": _safe_float(overview.get("52_week_high")),
                "52_week_low": _safe_float(overview.get("52_week_low"))
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取关键指标时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取关键指标失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def fetch_macro_economic_data(indicator: str = "GDP") -> str:
    """
    获取宏观经济指标数据
    
    获取GDP、利率、通胀率等宏观经济指标。
    
    Args:
        indicator (str): 经济指标类型，可选值: "GDP", "INFLATION", "INTEREST_RATE", "UNEMPLOYMENT"
    
    Returns:
        str: JSON格式的宏观经济数据
    """
    try:
        # 检查缓存
        cache_key = f"macro_data_{indicator}"
        cached = _get_from_cache(cache_key, expiration_hours=168)  # 缓存7天
        if cached:
            return cached
        
        # 从FRED API获取数据
        import requests
        
        api_key = os.environ.get("FRED_API_KEY", "")
        
        # 映射指标到FRED系列ID
        series_map = {
            "GDP": "GDP",
            "INFLATION": "CPIAUCSL",
            "INTEREST_RATE": "DFF",
            "UNEMPLOYMENT": "UNRATE"
        }
        
        series_id = series_map.get(indicator, "GDP")
        
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 20
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        observations = data.get("observations", [])
        
        result = {
            "success": True,
            "indicator": indicator,
            "series_id": series_id,
            "data": observations,
            "data_source": "FRED",
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存结果
        _save_to_cache(cache_key, json.dumps(result), expiration_hours=168)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取宏观经济数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取宏观经济数据失败: {str(e)}",
            "indicator": indicator,
            "note": "需要设置FRED_API_KEY环境变量"
        }, ensure_ascii=False, indent=2)


@tool
def search_industry_trends(industry: str, max_results: int = 10) -> str:
    """
    搜索行业趋势信息
    
    使用网络搜索获取行业发展趋势和相关信息。需要配合http_request或SerpAPI工具使用。
    
    Args:
        industry (str): 行业名称，例如 "Technology", "Healthcare"
        max_results (int): 最大返回结果数，默认10
    
    Returns:
        str: JSON格式的行业趋势信息
    """
    API_KEY = os.environ.get("SERPAPI_API_KEY", "")
    if not API_KEY:
        return json.dumps({
            "success": False,
            "error": "SERPAPI_API_KEY is not set",
            "industry": industry
        }, ensure_ascii=False, indent=2)
    
    try:
        # 检查缓存
        cache_key = f"industry_trends_{industry}"
        cached = _get_from_cache(cache_key, expiration_hours=168)  # 缓存7天
        if cached:
            return cached
        
        # 构建搜索查询
        query = f"{industry} industry trends analysis outlook"

        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": API_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("organic_results", [])
        if not results:
            return json.dumps({
                "success": False,
                "error": "No results found",
                "industry": industry
            }, ensure_ascii=False, indent=2)
        
        return json.dumps({"success": True, "results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"搜索行业趋势时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"搜索行业趋势失败: {str(e)}",
            "industry": industry
        }, ensure_ascii=False, indent=2)


@tool
def fetch_comparable_companies(symbol: str, sector: str = None) -> str:
    """
    获取可比公司列表
    
    基于行业分类和业务相似度识别可比公司。
    
    Args:
        symbol (str): 目标股票代码
        sector (str): 行业类别，如果不提供则自动获取
    
    Returns:
        str: JSON格式的可比公司列表
    """
    try:
        # 检查缓存
        cache_key = f"comparable_companies_{symbol}"
        cached = _get_from_cache(cache_key, expiration_hours=168)  # 缓存7天
        if cached:
            return cached
        
        # 如果没有提供sector，先获取公司概览
        if not sector:
            overview_json = fetch_company_overview(symbol)
            overview = json.loads(overview_json)
            if overview.get("success"):
                sector = overview.get("sector", "")
        
        # 使用行业ETF或指数成分股作为可比公司
        # 这里提供一个简化的实现
        result = {
            "success": True,
            "symbol": symbol,
            "sector": sector,
            "comparable_companies": [],
            "selection_criteria": [
                "同一行业分类",
                "市值相近（±50%）",
                "业务模式相似"
            ],
            "note": "需要进一步实现行业分类和可比公司筛选逻辑",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取可比公司时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"获取可比公司失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


# 缓存辅助函数

def _get_from_cache(cache_key: str, expiration_hours: int = 24) -> Optional[str]:
    """从缓存获取数据"""
    try:
        cache_file = os.path.join(DEFAULT_CACHE_DIR, f"{_sanitize_key(cache_key)}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_item = json.load(f)
        
        # 检查是否过期
        if time.time() > cache_item.get("expires_at", 0):
            return None
        
        logger.info(f"使用缓存数据: {cache_key}")
        return cache_item.get("data", "")
        
    except Exception as e:
        logger.warning(f"读取缓存失败: {str(e)}")
        return None


def _save_to_cache(cache_key: str, data: str, expiration_hours: int = 24) -> None:
    """保存数据到缓存"""
    try:
        cache_file = os.path.join(DEFAULT_CACHE_DIR, f"{_sanitize_key(cache_key)}.json")
        
        cache_item = {
            "key": cache_key,
            "data": data,
            "created_at": time.time(),
            "expires_at": time.time() + (expiration_hours * 3600),
            "expiration_hours": expiration_hours
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_item, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已缓存: {cache_key}")
        
    except Exception as e:
        logger.warning(f"保存缓存失败: {str(e)}")


def _sanitize_key(key: str) -> str:
    """将缓存键转换为安全的文件名"""
    return hashlib.md5(key.encode('utf-8')).hexdigest()


def _safe_float(value: Any) -> Optional[float]:
    """安全地转换为浮点数"""
    try:
        if value is None or value == "None" or value == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None
