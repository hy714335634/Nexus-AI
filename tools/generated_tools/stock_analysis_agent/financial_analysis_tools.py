#!/usr/bin/env python3
"""
财务分析工具

提供财务报表分析、财务比率计算、趋势分析等功能
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def calculate_financial_ratios(financial_data: str, statement_type: str = "income") -> str:
    """
    计算财务比率
    
    基于财务报表数据计算各类财务比率，包括盈利能力、偿债能力、运营效率等指标。
    
    Args:
        financial_data (str): JSON格式的财务报表数据
        statement_type (str): 报表类型，可选值: "income", "balance", "cash"
    
    Returns:
        str: JSON格式的财务比率分析结果
    """
    try:
        # 解析财务数据
        data = json.loads(financial_data)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        reports = data.get("reports", [])
        if not reports:
            return json.dumps({
                "success": False,
                "error": "财务报表数据为空"
            }, ensure_ascii=False, indent=2)
        
        # 计算比率
        ratio_results = []
        
        for report in reports:
            fiscal_date = report.get("fiscalDateEnding", "")
            
            if statement_type == "income":
                ratios = _calculate_income_ratios(report)
            elif statement_type == "balance":
                ratios = _calculate_balance_ratios(report)
            elif statement_type == "cash":
                ratios = _calculate_cash_ratios(report)
            else:
                ratios = {}
            
            ratio_results.append({
                "fiscal_date": fiscal_date,
                "ratios": ratios
            })
        
        result = {
            "success": True,
            "symbol": data.get("symbol", ""),
            "statement_type": statement_type,
            "period": data.get("period", ""),
            "ratio_results": ratio_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"数据格式错误: {str(e)}"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"计算财务比率时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算财务比率失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def analyze_profitability(financial_data: str) -> str:
    """
    分析盈利能力
    
    分析公司的盈利能力，包括毛利率、营业利润率、净利率等指标及其趋势。
    
    Args:
        financial_data (str): JSON格式的损益表数据
    
    Returns:
        str: JSON格式的盈利能力分析结果
    """
    try:
        # 解析财务数据
        data = json.loads(financial_data)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        reports = data.get("reports", [])
        if not reports:
            return json.dumps({
                "success": False,
                "error": "损益表数据为空"
            }, ensure_ascii=False, indent=2)
        
        # 分析每期的盈利能力
        profitability_analysis = []
        
        for report in reports:
            fiscal_date = report.get("fiscalDateEnding", "")
            
            # 提取关键财务数据
            revenue = _safe_float(report.get("totalRevenue", 0))
            gross_profit = _safe_float(report.get("grossProfit", 0))
            operating_income = _safe_float(report.get("operatingIncome", 0))
            net_income = _safe_float(report.get("netIncome", 0))
            ebitda = _safe_float(report.get("ebitda", 0))
            
            # 计算盈利能力指标
            analysis = {
                "fiscal_date": fiscal_date,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "operating_income": operating_income,
                "net_income": net_income,
                "ebitda": ebitda,
                "margins": {}
            }
            
            # 计算利润率
            if revenue and revenue > 0:
                analysis["margins"]["gross_margin"] = round((gross_profit / revenue) * 100, 2) if gross_profit else None
                analysis["margins"]["operating_margin"] = round((operating_income / revenue) * 100, 2) if operating_income else None
                analysis["margins"]["net_margin"] = round((net_income / revenue) * 100, 2) if net_income else None
                analysis["margins"]["ebitda_margin"] = round((ebitda / revenue) * 100, 2) if ebitda else None
            
            profitability_analysis.append(analysis)
        
        # 计算趋势
        trends = _calculate_trends(profitability_analysis, ["gross_margin", "operating_margin", "net_margin"])
        
        result = {
            "success": True,
            "symbol": data.get("symbol", ""),
            "period": data.get("period", ""),
            "profitability_analysis": profitability_analysis,
            "trends": trends,
            "summary": _generate_profitability_summary(profitability_analysis, trends),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"分析盈利能力时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"分析盈利能力失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def analyze_liquidity(balance_sheet: str) -> str:
    """
    分析流动性
    
    分析公司的短期偿债能力，包括流动比率、速动比率等指标。
    
    Args:
        balance_sheet (str): JSON格式的资产负债表数据
    
    Returns:
        str: JSON格式的流动性分析结果
    """
    try:
        # 解析财务数据
        data = json.loads(balance_sheet)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        reports = data.get("reports", [])
        if not reports:
            return json.dumps({
                "success": False,
                "error": "资产负债表数据为空"
            }, ensure_ascii=False, indent=2)
        
        # 分析每期的流动性
        liquidity_analysis = []
        
        for report in reports:
            fiscal_date = report.get("fiscalDateEnding", "")
            
            # 提取关键财务数据
            current_assets = _safe_float(report.get("totalCurrentAssets", 0))
            current_liabilities = _safe_float(report.get("totalCurrentLiabilities", 0))
            cash = _safe_float(report.get("cashAndCashEquivalentsAtCarryingValue", 0))
            inventory = _safe_float(report.get("inventory", 0))
            
            # 计算流动性指标
            analysis = {
                "fiscal_date": fiscal_date,
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "cash": cash,
                "inventory": inventory,
                "ratios": {}
            }
            
            # 计算比率
            if current_liabilities and current_liabilities > 0:
                analysis["ratios"]["current_ratio"] = round(current_assets / current_liabilities, 2) if current_assets else None
                
                # 速动比率 = (流动资产 - 存货) / 流动负债
                quick_assets = (current_assets or 0) - (inventory or 0)
                analysis["ratios"]["quick_ratio"] = round(quick_assets / current_liabilities, 2)
                
                # 现金比率 = 现金 / 流动负债
                analysis["ratios"]["cash_ratio"] = round(cash / current_liabilities, 2) if cash else None
            
            # 评估流动性状况
            current_ratio = analysis["ratios"].get("current_ratio")
            if current_ratio:
                if current_ratio >= 2.0:
                    analysis["liquidity_status"] = "优秀"
                elif current_ratio >= 1.5:
                    analysis["liquidity_status"] = "良好"
                elif current_ratio >= 1.0:
                    analysis["liquidity_status"] = "一般"
                else:
                    analysis["liquidity_status"] = "较差"
            
            liquidity_analysis.append(analysis)
        
        # 计算趋势
        trends = _calculate_trends(liquidity_analysis, ["current_ratio", "quick_ratio", "cash_ratio"])
        
        result = {
            "success": True,
            "symbol": data.get("symbol", ""),
            "period": data.get("period", ""),
            "liquidity_analysis": liquidity_analysis,
            "trends": trends,
            "summary": _generate_liquidity_summary(liquidity_analysis, trends),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"分析流动性时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"分析流动性失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def analyze_solvency(balance_sheet: str) -> str:
    """
    分析偿债能力
    
    分析公司的长期偿债能力，包括资产负债率、权益乘数等指标。
    
    Args:
        balance_sheet (str): JSON格式的资产负债表数据
    
    Returns:
        str: JSON格式的偿债能力分析结果
    """
    try:
        # 解析财务数据
        data = json.loads(balance_sheet)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        reports = data.get("reports", [])
        if not reports:
            return json.dumps({
                "success": False,
                "error": "资产负债表数据为空"
            }, ensure_ascii=False, indent=2)
        
        # 分析每期的偿债能力
        solvency_analysis = []
        
        for report in reports:
            fiscal_date = report.get("fiscalDateEnding", "")
            
            # 提取关键财务数据
            total_assets = _safe_float(report.get("totalAssets", 0))
            total_liabilities = _safe_float(report.get("totalLiabilities", 0))
            total_equity = _safe_float(report.get("totalShareholderEquity", 0))
            long_term_debt = _safe_float(report.get("longTermDebt", 0))
            
            # 计算偿债能力指标
            analysis = {
                "fiscal_date": fiscal_date,
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "long_term_debt": long_term_debt,
                "ratios": {}
            }
            
            # 计算比率
            if total_assets and total_assets > 0:
                # 资产负债率 = 总负债 / 总资产
                analysis["ratios"]["debt_to_assets"] = round((total_liabilities / total_assets) * 100, 2) if total_liabilities else None
            
            if total_equity and total_equity > 0:
                # 产权比率 = 总负债 / 股东权益
                analysis["ratios"]["debt_to_equity"] = round((total_liabilities / total_equity) * 100, 2) if total_liabilities else None
                
                # 权益乘数 = 总资产 / 股东权益
                analysis["ratios"]["equity_multiplier"] = round(total_assets / total_equity, 2) if total_assets else None
            
            # 评估偿债能力
            debt_to_assets = analysis["ratios"].get("debt_to_assets")
            if debt_to_assets:
                if debt_to_assets <= 40:
                    analysis["solvency_status"] = "优秀"
                elif debt_to_assets <= 60:
                    analysis["solvency_status"] = "良好"
                elif debt_to_assets <= 70:
                    analysis["solvency_status"] = "一般"
                else:
                    analysis["solvency_status"] = "较差"
            
            solvency_analysis.append(analysis)
        
        # 计算趋势
        trends = _calculate_trends(solvency_analysis, ["debt_to_assets", "debt_to_equity"])
        
        result = {
            "success": True,
            "symbol": data.get("symbol", ""),
            "period": data.get("period", ""),
            "solvency_analysis": solvency_analysis,
            "trends": trends,
            "summary": _generate_solvency_summary(solvency_analysis, trends),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"分析偿债能力时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"分析偿债能力失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def analyze_efficiency(financial_data: str, balance_sheet: str) -> str:
    """
    分析运营效率
    
    分析公司的运营效率，包括资产周转率、存货周转率等指标。
    
    Args:
        financial_data (str): JSON格式的损益表数据
        balance_sheet (str): JSON格式的资产负债表数据
    
    Returns:
        str: JSON格式的运营效率分析结果
    """
    try:
        # 解析财务数据
        income_data = json.loads(financial_data)
        balance_data = json.loads(balance_sheet)
        
        if not income_data.get("success") or not balance_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        income_reports = income_data.get("reports", [])
        balance_reports = balance_data.get("reports", [])
        
        if not income_reports or not balance_reports:
            return json.dumps({
                "success": False,
                "error": "财务报表数据为空"
            }, ensure_ascii=False, indent=2)
        
        # 分析运营效率
        efficiency_analysis = []
        
        # 匹配损益表和资产负债表
        for income_report in income_reports:
            fiscal_date = income_report.get("fiscalDateEnding", "")
            
            # 查找对应的资产负债表
            balance_report = next(
                (r for r in balance_reports if r.get("fiscalDateEnding") == fiscal_date),
                None
            )
            
            if not balance_report:
                continue
            
            # 提取关键数据
            revenue = _safe_float(income_report.get("totalRevenue", 0))
            cogs = _safe_float(income_report.get("costOfRevenue", 0))
            
            total_assets = _safe_float(balance_report.get("totalAssets", 0))
            inventory = _safe_float(balance_report.get("inventory", 0))
            accounts_receivable = _safe_float(balance_report.get("currentNetReceivables", 0))
            
            # 计算效率指标
            analysis = {
                "fiscal_date": fiscal_date,
                "revenue": revenue,
                "total_assets": total_assets,
                "inventory": inventory,
                "accounts_receivable": accounts_receivable,
                "ratios": {}
            }
            
            # 总资产周转率 = 营业收入 / 总资产
            if total_assets and total_assets > 0:
                analysis["ratios"]["asset_turnover"] = round(revenue / total_assets, 2) if revenue else None
            
            # 存货周转率 = 营业成本 / 存货
            if inventory and inventory > 0:
                analysis["ratios"]["inventory_turnover"] = round(cogs / inventory, 2) if cogs else None
                # 存货周转天数 = 365 / 存货周转率
                if analysis["ratios"]["inventory_turnover"]:
                    analysis["ratios"]["inventory_days"] = round(365 / analysis["ratios"]["inventory_turnover"], 2)
            
            # 应收账款周转率 = 营业收入 / 应收账款
            if accounts_receivable and accounts_receivable > 0:
                analysis["ratios"]["receivables_turnover"] = round(revenue / accounts_receivable, 2) if revenue else None
                # 应收账款周转天数 = 365 / 应收账款周转率
                if analysis["ratios"]["receivables_turnover"]:
                    analysis["ratios"]["receivables_days"] = round(365 / analysis["ratios"]["receivables_turnover"], 2)
            
            efficiency_analysis.append(analysis)
        
        # 计算趋势
        trends = _calculate_trends(efficiency_analysis, ["asset_turnover", "inventory_turnover", "receivables_turnover"])
        
        result = {
            "success": True,
            "symbol": income_data.get("symbol", ""),
            "period": income_data.get("period", ""),
            "efficiency_analysis": efficiency_analysis,
            "trends": trends,
            "summary": _generate_efficiency_summary(efficiency_analysis, trends),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"分析运营效率时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"分析运营效率失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def analyze_growth(financial_data: str) -> str:
    """
    分析增长性
    
    分析公司的增长趋势，包括营收增长率、利润增长率等指标。
    
    Args:
        financial_data (str): JSON格式的损益表数据
    
    Returns:
        str: JSON格式的增长性分析结果
    """
    try:
        # 解析财务数据
        data = json.loads(financial_data)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "输入的财务数据无效或获取失败"
            }, ensure_ascii=False, indent=2)
        
        reports = data.get("reports", [])
        if len(reports) < 2:
            return json.dumps({
                "success": False,
                "error": "需要至少两期数据才能计算增长率"
            }, ensure_ascii=False, indent=2)
        
        # 计算增长率
        growth_analysis = []
        
        for i in range(len(reports) - 1):
            current_report = reports[i]
            previous_report = reports[i + 1]
            
            current_date = current_report.get("fiscalDateEnding", "")
            previous_date = previous_report.get("fiscalDateEnding", "")
            
            # 提取关键数据
            current_revenue = _safe_float(current_report.get("totalRevenue", 0))
            previous_revenue = _safe_float(previous_report.get("totalRevenue", 0))
            
            current_net_income = _safe_float(current_report.get("netIncome", 0))
            previous_net_income = _safe_float(previous_report.get("netIncome", 0))
            
            current_operating_income = _safe_float(current_report.get("operatingIncome", 0))
            previous_operating_income = _safe_float(previous_report.get("operatingIncome", 0))
            
            # 计算增长率
            analysis = {
                "period": f"{previous_date} to {current_date}",
                "current_date": current_date,
                "previous_date": previous_date,
                "growth_rates": {}
            }
            
            # 营收增长率
            if previous_revenue and previous_revenue != 0:
                revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
                analysis["growth_rates"]["revenue_growth"] = round(revenue_growth, 2)
            
            # 净利润增长率
            if previous_net_income and previous_net_income != 0:
                net_income_growth = ((current_net_income - previous_net_income) / previous_net_income) * 100
                analysis["growth_rates"]["net_income_growth"] = round(net_income_growth, 2)
            
            # 营业利润增长率
            if previous_operating_income and previous_operating_income != 0:
                operating_income_growth = ((current_operating_income - previous_operating_income) / previous_operating_income) * 100
                analysis["growth_rates"]["operating_income_growth"] = round(operating_income_growth, 2)
            
            growth_analysis.append(analysis)
        
        # 计算平均增长率
        avg_growth = _calculate_average_growth(growth_analysis)
        
        result = {
            "success": True,
            "symbol": data.get("symbol", ""),
            "period": data.get("period", ""),
            "growth_analysis": growth_analysis,
            "average_growth_rates": avg_growth,
            "summary": _generate_growth_summary(growth_analysis, avg_growth),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"分析增长性时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"分析增长性失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def compare_peer_performance(symbol: str, peers: List[str], metrics: List[str]) -> str:
    """
    同行业公司对比分析
    
    对比目标公司与同行业公司的关键财务指标。
    
    Args:
        symbol (str): 目标公司股票代码
        peers (List[str]): 同行业公司股票代码列表
        metrics (List[str]): 要对比的指标列表，例如 ["pe_ratio", "profit_margin", "roe"]
    
    Returns:
        str: JSON格式的对比分析结果
    """
    try:
        result = {
            "success": True,
            "target_symbol": symbol,
            "peer_symbols": peers,
            "metrics": metrics,
            "comparison": {},
            "ranking": {},
            "note": "需要先获取各公司的财务数据，然后进行对比分析",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"同行业对比分析时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"同行业对比分析失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _calculate_income_ratios(report: Dict[str, Any]) -> Dict[str, Any]:
    """计算损益表相关比率"""
    ratios = {}
    
    revenue = _safe_float(report.get("totalRevenue", 0))
    gross_profit = _safe_float(report.get("grossProfit", 0))
    operating_income = _safe_float(report.get("operatingIncome", 0))
    net_income = _safe_float(report.get("netIncome", 0))
    
    if revenue and revenue > 0:
        ratios["gross_margin"] = round((gross_profit / revenue) * 100, 2) if gross_profit else None
        ratios["operating_margin"] = round((operating_income / revenue) * 100, 2) if operating_income else None
        ratios["net_margin"] = round((net_income / revenue) * 100, 2) if net_income else None
    
    return ratios


def _calculate_balance_ratios(report: Dict[str, Any]) -> Dict[str, Any]:
    """计算资产负债表相关比率"""
    ratios = {}
    
    total_assets = _safe_float(report.get("totalAssets", 0))
    total_liabilities = _safe_float(report.get("totalLiabilities", 0))
    total_equity = _safe_float(report.get("totalShareholderEquity", 0))
    current_assets = _safe_float(report.get("totalCurrentAssets", 0))
    current_liabilities = _safe_float(report.get("totalCurrentLiabilities", 0))
    
    if total_assets and total_assets > 0:
        ratios["debt_to_assets"] = round((total_liabilities / total_assets) * 100, 2) if total_liabilities else None
    
    if total_equity and total_equity > 0:
        ratios["debt_to_equity"] = round((total_liabilities / total_equity) * 100, 2) if total_liabilities else None
    
    if current_liabilities and current_liabilities > 0:
        ratios["current_ratio"] = round(current_assets / current_liabilities, 2) if current_assets else None
    
    return ratios


def _calculate_cash_ratios(report: Dict[str, Any]) -> Dict[str, Any]:
    """计算现金流量表相关比率"""
    ratios = {}
    
    operating_cashflow = _safe_float(report.get("operatingCashflow", 0))
    capital_expenditures = _safe_float(report.get("capitalExpenditures", 0))
    
    # 自由现金流 = 经营现金流 - 资本支出
    if operating_cashflow and capital_expenditures:
        ratios["free_cash_flow"] = operating_cashflow - abs(capital_expenditures)
    
    return ratios


def _calculate_trends(analysis_list: List[Dict[str, Any]], metric_keys: List[str]) -> Dict[str, str]:
    """计算指标趋势"""
    trends = {}
    
    for key in metric_keys:
        values = []
        for item in analysis_list:
            if "ratios" in item and key in item["ratios"]:
                val = item["ratios"][key]
                if val is not None:
                    values.append(val)
            elif "margins" in item and key in item["margins"]:
                val = item["margins"][key]
                if val is not None:
                    values.append(val)
        
        if len(values) >= 2:
            if values[0] > values[-1]:
                trends[key] = "上升"
            elif values[0] < values[-1]:
                trends[key] = "下降"
            else:
                trends[key] = "稳定"
        else:
            trends[key] = "数据不足"
    
    return trends


def _calculate_average_growth(growth_analysis: List[Dict[str, Any]]) -> Dict[str, float]:
    """计算平均增长率"""
    avg_growth = {}
    
    growth_keys = ["revenue_growth", "net_income_growth", "operating_income_growth"]
    
    for key in growth_keys:
        values = []
        for item in growth_analysis:
            if key in item.get("growth_rates", {}):
                val = item["growth_rates"][key]
                if val is not None:
                    values.append(val)
        
        if values:
            avg_growth[key] = round(sum(values) / len(values), 2)
    
    return avg_growth


def _generate_profitability_summary(analysis: List[Dict[str, Any]], trends: Dict[str, str]) -> str:
    """生成盈利能力分析摘要"""
    if not analysis:
        return "无足够数据生成摘要"
    
    latest = analysis[0]
    margins = latest.get("margins", {})
    
    summary_parts = []
    
    # 最新毛利率
    gross_margin = margins.get("gross_margin")
    if gross_margin:
        summary_parts.append(f"最新毛利率为{gross_margin}%")
    
    # 最新净利率
    net_margin = margins.get("net_margin")
    if net_margin:
        summary_parts.append(f"净利率为{net_margin}%")
    
    # 趋势
    if "gross_margin" in trends:
        summary_parts.append(f"毛利率呈{trends['gross_margin']}趋势")
    
    return "，".join(summary_parts) if summary_parts else "数据不足"


def _generate_liquidity_summary(analysis: List[Dict[str, Any]], trends: Dict[str, str]) -> str:
    """生成流动性分析摘要"""
    if not analysis:
        return "无足够数据生成摘要"
    
    latest = analysis[0]
    ratios = latest.get("ratios", {})
    status = latest.get("liquidity_status", "")
    
    summary_parts = []
    
    # 流动比率
    current_ratio = ratios.get("current_ratio")
    if current_ratio:
        summary_parts.append(f"流动比率为{current_ratio}")
    
    # 流动性状况
    if status:
        summary_parts.append(f"流动性状况{status}")
    
    return "，".join(summary_parts) if summary_parts else "数据不足"


def _generate_solvency_summary(analysis: List[Dict[str, Any]], trends: Dict[str, str]) -> str:
    """生成偿债能力分析摘要"""
    if not analysis:
        return "无足够数据生成摘要"
    
    latest = analysis[0]
    ratios = latest.get("ratios", {})
    status = latest.get("solvency_status", "")
    
    summary_parts = []
    
    # 资产负债率
    debt_to_assets = ratios.get("debt_to_assets")
    if debt_to_assets:
        summary_parts.append(f"资产负债率为{debt_to_assets}%")
    
    # 偿债能力状况
    if status:
        summary_parts.append(f"偿债能力{status}")
    
    return "，".join(summary_parts) if summary_parts else "数据不足"


def _generate_efficiency_summary(analysis: List[Dict[str, Any]], trends: Dict[str, str]) -> str:
    """生成运营效率分析摘要"""
    if not analysis:
        return "无足够数据生成摘要"
    
    latest = analysis[0]
    ratios = latest.get("ratios", {})
    
    summary_parts = []
    
    # 资产周转率
    asset_turnover = ratios.get("asset_turnover")
    if asset_turnover:
        summary_parts.append(f"资产周转率为{asset_turnover}")
    
    # 存货周转天数
    inventory_days = ratios.get("inventory_days")
    if inventory_days:
        summary_parts.append(f"存货周转天数为{inventory_days}天")
    
    return "，".join(summary_parts) if summary_parts else "数据不足"


def _generate_growth_summary(analysis: List[Dict[str, Any]], avg_growth: Dict[str, float]) -> str:
    """生成增长性分析摘要"""
    if not avg_growth:
        return "无足够数据生成摘要"
    
    summary_parts = []
    
    # 平均营收增长率
    revenue_growth = avg_growth.get("revenue_growth")
    if revenue_growth:
        summary_parts.append(f"平均营收增长率为{revenue_growth}%")
    
    # 平均净利润增长率
    net_income_growth = avg_growth.get("net_income_growth")
    if net_income_growth:
        summary_parts.append(f"平均净利润增长率为{net_income_growth}%")
    
    return "，".join(summary_parts) if summary_parts else "数据不足"


def _safe_float(value: Any) -> Optional[float]:
    """安全地转换为浮点数"""
    try:
        if value is None or value == "None" or value == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None
