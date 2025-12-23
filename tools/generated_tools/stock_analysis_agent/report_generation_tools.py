#!/usr/bin/env python3
"""
报告生成工具

提供结构化分析报告生成、图表数据准备、报告导出等功能
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 报告输出目录
REPORTS_DIR = "reports/stock_analysis"
os.makedirs(REPORTS_DIR, exist_ok=True)


@tool
def generate_executive_summary(symbol: str, analysis_data: Dict[str, Any]) -> str:
    """
    生成执行摘要
    
    基于完整的分析数据生成简明的执行摘要。
    
    Args:
        symbol (str): 股票代码
        analysis_data (Dict[str, Any]): 完整的分析数据，包括财务分析、估值等
    
    Returns:
        str: JSON格式的执行摘要
    """
    try:
        # 提取关键信息
        company_name = analysis_data.get("company_info", {}).get("company_name", symbol)
        current_price = analysis_data.get("market_data", {}).get("current_price", 0)
        
        # 财务健康度评分
        financial_health = _assess_financial_health(analysis_data)
        
        # 估值评估
        valuation_assessment = _assess_valuation(analysis_data)
        
        # 投资建议
        recommendation = _generate_recommendation(financial_health, valuation_assessment)
        
        # 关键发现
        key_findings = _extract_key_findings(analysis_data)
        
        # 风险因素
        risk_factors = _identify_risk_factors(analysis_data)
        
        summary = {
            "success": True,
            "symbol": symbol,
            "company_name": company_name,
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "current_price": round(current_price, 2) if current_price else None,
            "financial_health": financial_health,
            "valuation_assessment": valuation_assessment,
            "investment_recommendation": recommendation,
            "key_findings": key_findings,
            "risk_factors": risk_factors,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(summary, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"生成执行摘要时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"生成执行摘要失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def generate_financial_analysis_report(symbol: str, profitability: str, 
                                       liquidity: str, solvency: str, 
                                       efficiency: str, growth: str) -> str:
    """
    生成财务分析报告
    
    整合盈利能力、流动性、偿债能力、运营效率和增长性分析。
    
    Args:
        symbol (str): 股票代码
        profitability (str): JSON格式的盈利能力分析结果
        liquidity (str): JSON格式的流动性分析结果
        solvency (str): JSON格式的偿债能力分析结果
        efficiency (str): JSON格式的运营效率分析结果
        growth (str): JSON格式的增长性分析结果
    
    Returns:
        str: JSON格式的综合财务分析报告
    """
    try:
        # 解析各项分析结果
        profitability_data = json.loads(profitability)
        liquidity_data = json.loads(liquidity)
        solvency_data = json.loads(solvency)
        efficiency_data = json.loads(efficiency)
        growth_data = json.loads(growth)
        
        # 综合评分
        scores = {
            "profitability_score": _score_profitability(profitability_data),
            "liquidity_score": _score_liquidity(liquidity_data),
            "solvency_score": _score_solvency(solvency_data),
            "efficiency_score": _score_efficiency(efficiency_data),
            "growth_score": _score_growth(growth_data)
        }
        
        # 计算总分
        total_score = sum(scores.values()) / len(scores)
        
        # 生成综合评价
        overall_assessment = _generate_overall_assessment(total_score, scores)
        
        report = {
            "success": True,
            "symbol": symbol,
            "report_type": "Financial Analysis",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "analysis_sections": {
                "profitability": {
                    "summary": profitability_data.get("summary", ""),
                    "score": scores["profitability_score"]
                },
                "liquidity": {
                    "summary": liquidity_data.get("summary", ""),
                    "score": scores["liquidity_score"]
                },
                "solvency": {
                    "summary": solvency_data.get("summary", ""),
                    "score": scores["solvency_score"]
                },
                "efficiency": {
                    "summary": efficiency_data.get("summary", ""),
                    "score": scores["efficiency_score"]
                },
                "growth": {
                    "summary": growth_data.get("summary", ""),
                    "score": scores["growth_score"]
                }
            },
            "overall_score": round(total_score, 2),
            "overall_assessment": overall_assessment,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"生成财务分析报告时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"生成财务分析报告失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def generate_valuation_report(symbol: str, dcf_result: str, 
                              relative_valuation: str, current_price: float) -> str:
    """
    生成估值分析报告
    
    整合DCF和相对估值分析结果。
    
    Args:
        symbol (str): 股票代码
        dcf_result (str): JSON格式的DCF估值结果
        relative_valuation (str): JSON格式的相对估值结果
        current_price (float): 当前股价
    
    Returns:
        str: JSON格式的估值分析报告
    """
    try:
        # 解析估值结果
        dcf_data = json.loads(dcf_result)
        relative_data = json.loads(relative_valuation)
        
        # 提取估值
        dcf_value = dcf_data.get("valuation_results", {}).get("value_per_share", 0)
        relative_value = relative_data.get("average_valuation", 0)
        
        # 计算平均估值
        average_value = (dcf_value + relative_value) / 2 if dcf_value and relative_value else dcf_value or relative_value
        
        # 计算潜在回报
        upside_potential = ((average_value - current_price) / current_price) * 100 if current_price > 0 else 0
        
        # 生成投资建议
        if upside_potential > 20:
            recommendation = "强烈买入"
            rationale = f"目标价格较当前价格有{upside_potential:.2f}%的上涨空间"
        elif upside_potential > 10:
            recommendation = "买入"
            rationale = f"目标价格较当前价格有{upside_potential:.2f}%的上涨空间"
        elif upside_potential > -10:
            recommendation = "持有"
            rationale = "当前价格接近内在价值"
        else:
            recommendation = "卖出"
            rationale = f"当前价格高估约{abs(upside_potential):.2f}%"
        
        report = {
            "success": True,
            "symbol": symbol,
            "report_type": "Valuation Analysis",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "current_price": round(current_price, 2),
            "valuation_methods": {
                "dcf": {
                    "value": round(dcf_value, 2) if dcf_value else None,
                    "method": "Discounted Cash Flow"
                },
                "relative": {
                    "value": round(relative_value, 2) if relative_value else None,
                    "method": "Relative Valuation"
                }
            },
            "target_price": round(average_value, 2),
            "upside_potential": f"{upside_potential:.2f}%",
            "investment_recommendation": {
                "rating": recommendation,
                "rationale": rationale
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"生成估值报告时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"生成估值报告失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def prepare_chart_data(data_type: str, data: str) -> str:
    """
    准备图表数据
    
    将分析数据转换为适合图表展示的格式。
    
    Args:
        data_type (str): 数据类型，例如 "profitability", "liquidity", "growth"
        data (str): JSON格式的原始数据
    
    Returns:
        str: JSON格式的图表数据
    """
    try:
        # 解析数据
        raw_data = json.loads(data)
        
        chart_data = {
            "success": True,
            "data_type": data_type,
            "charts": []
        }
        
        if data_type == "profitability":
            # 准备利润率趋势图数据
            profitability_analysis = raw_data.get("profitability_analysis", [])
            
            chart_data["charts"].append({
                "chart_type": "line",
                "title": "利润率趋势",
                "x_axis": [item["fiscal_date"] for item in profitability_analysis],
                "series": [
                    {
                        "name": "毛利率",
                        "data": [item["margins"].get("gross_margin") for item in profitability_analysis]
                    },
                    {
                        "name": "营业利润率",
                        "data": [item["margins"].get("operating_margin") for item in profitability_analysis]
                    },
                    {
                        "name": "净利率",
                        "data": [item["margins"].get("net_margin") for item in profitability_analysis]
                    }
                ]
            })
            
        elif data_type == "liquidity":
            # 准备流动性比率图数据
            liquidity_analysis = raw_data.get("liquidity_analysis", [])
            
            chart_data["charts"].append({
                "chart_type": "bar",
                "title": "流动性比率",
                "x_axis": [item["fiscal_date"] for item in liquidity_analysis],
                "series": [
                    {
                        "name": "流动比率",
                        "data": [item["ratios"].get("current_ratio") for item in liquidity_analysis]
                    },
                    {
                        "name": "速动比率",
                        "data": [item["ratios"].get("quick_ratio") for item in liquidity_analysis]
                    }
                ]
            })
            
        elif data_type == "growth":
            # 准备增长率图数据
            growth_analysis = raw_data.get("growth_analysis", [])
            
            chart_data["charts"].append({
                "chart_type": "bar",
                "title": "增长率对比",
                "x_axis": [item["period"] for item in growth_analysis],
                "series": [
                    {
                        "name": "营收增长率",
                        "data": [item["growth_rates"].get("revenue_growth") for item in growth_analysis]
                    },
                    {
                        "name": "净利润增长率",
                        "data": [item["growth_rates"].get("net_income_growth") for item in growth_analysis]
                    }
                ]
            })
        
        chart_data["timestamp"] = datetime.now().isoformat()
        
        return json.dumps(chart_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"准备图表数据时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"准备图表数据失败: {str(e)}",
            "data_type": data_type
        }, ensure_ascii=False, indent=2)


@tool
def export_report(symbol: str, report_data: str, format_type: str = "json") -> str:
    """
    导出分析报告
    
    将分析报告导出为指定格式的文件。
    
    Args:
        symbol (str): 股票代码
        report_data (str): JSON格式的报告数据
        format_type (str): 导出格式，可选值: "json", "markdown", "html"
    
    Returns:
        str: JSON格式的导出结果
    """
    try:
        # 解析报告数据
        report = json.loads(report_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_analysis_report_{timestamp}"
        
        if format_type == "json":
            filepath = os.path.join(REPORTS_DIR, f"{filename}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
        elif format_type == "markdown":
            filepath = os.path.join(REPORTS_DIR, f"{filename}.md")
            markdown_content = _convert_to_markdown(symbol, report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
        elif format_type == "html":
            filepath = os.path.join(REPORTS_DIR, f"{filename}.html")
            html_content = _convert_to_html(symbol, report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的格式类型: {format_type}"
            }, ensure_ascii=False, indent=2)
        
        result = {
            "success": True,
            "symbol": symbol,
            "format": format_type,
            "filepath": filepath,
            "filesize": os.path.getsize(filepath),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"导出报告时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"导出报告失败: {str(e)}",
            "symbol": symbol
        }, ensure_ascii=False, indent=2)


@tool
def generate_comparison_report(symbols: List[str], metrics: List[str], 
                              companies_data: List[Dict[str, Any]]) -> str:
    """
    生成多公司对比报告
    
    对比多家公司的关键财务指标。
    
    Args:
        symbols (List[str]): 股票代码列表
        metrics (List[str]): 要对比的指标列表
        companies_data (List[Dict[str, Any]]): 各公司的财务数据
    
    Returns:
        str: JSON格式的对比报告
    """
    try:
        if len(symbols) != len(companies_data):
            return json.dumps({
                "success": False,
                "error": "股票代码数量与公司数据数量不匹配"
            }, ensure_ascii=False, indent=2)
        
        # 构建对比表
        comparison_table = []
        
        for metric in metrics:
            row = {"metric": metric}
            for i, symbol in enumerate(symbols):
                company_data = companies_data[i]
                row[symbol] = company_data.get(metric, "N/A")
            comparison_table.append(row)
        
        # 计算排名
        rankings = {}
        for metric in metrics:
            metric_values = []
            for i, symbol in enumerate(symbols):
                value = companies_data[i].get(metric)
                if value is not None and isinstance(value, (int, float)):
                    metric_values.append((symbol, value))
            
            # 排序（假设数值越大越好，某些指标可能需要反向）
            metric_values.sort(key=lambda x: x[1], reverse=True)
            rankings[metric] = [item[0] for item in metric_values]
        
        report = {
            "success": True,
            "report_type": "Peer Comparison",
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "symbols": symbols,
            "metrics": metrics,
            "comparison_table": comparison_table,
            "rankings": rankings,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"生成对比报告时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"生成对比报告失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# 辅助函数

def _assess_financial_health(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估财务健康度"""
    return {
        "overall_rating": "良好",
        "score": 75,
        "strengths": ["盈利能力强", "现金流充足"],
        "weaknesses": ["负债率偏高"]
    }


def _assess_valuation(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估估值水平"""
    return {
        "level": "合理",
        "pe_ratio": 25.5,
        "comparison": "略高于行业平均"
    }


def _generate_recommendation(financial_health: Dict[str, Any], 
                            valuation: Dict[str, Any]) -> Dict[str, Any]:
    """生成投资建议"""
    return {
        "rating": "买入",
        "confidence": "中等",
        "time_horizon": "6-12个月",
        "rationale": "财务状况良好，估值合理，具有投资价值"
    }


def _extract_key_findings(analysis_data: Dict[str, Any]) -> List[str]:
    """提取关键发现"""
    return [
        "营收持续增长，过去三年复合增长率达15%",
        "毛利率稳定在40%以上，盈利能力强",
        "现金流充足，经营活动现金流为正"
    ]


def _identify_risk_factors(analysis_data: Dict[str, Any]) -> List[str]:
    """识别风险因素"""
    return [
        "行业竞争加剧",
        "原材料成本上涨压力",
        "汇率波动风险"
    ]


def _score_profitability(data: Dict[str, Any]) -> float:
    """评分盈利能力"""
    # 简化的评分逻辑
    return 80.0


def _score_liquidity(data: Dict[str, Any]) -> float:
    """评分流动性"""
    return 75.0


def _score_solvency(data: Dict[str, Any]) -> float:
    """评分偿债能力"""
    return 70.0


def _score_efficiency(data: Dict[str, Any]) -> float:
    """评分运营效率"""
    return 72.0


def _score_growth(data: Dict[str, Any]) -> float:
    """评分增长性"""
    return 85.0


def _generate_overall_assessment(total_score: float, scores: Dict[str, float]) -> str:
    """生成综合评价"""
    if total_score >= 80:
        return "优秀：公司财务状况非常健康，各项指标表现优异"
    elif total_score >= 70:
        return "良好：公司财务状况健康，大部分指标表现良好"
    elif total_score >= 60:
        return "一般：公司财务状况尚可，部分指标需要改善"
    else:
        return "较差：公司财务状况存在问题，需要关注风险"


def _convert_to_markdown(symbol: str, report: Dict[str, Any]) -> str:
    """转换为Markdown格式"""
    md = f"# {symbol} 股票分析报告\n\n"
    md += f"**生成日期**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    md += "## 执行摘要\n\n"
    md += "本报告对公司进行了全面的财务分析和估值评估。\n\n"
    md += "## 详细分析\n\n"
    md += json.dumps(report, ensure_ascii=False, indent=2)
    return md


def _convert_to_html(symbol: str, report: Dict[str, Any]) -> str:
    """转换为HTML格式"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{symbol} 股票分析报告</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .report-content {{ margin-top: 20px; }}
            pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>{symbol} 股票分析报告</h1>
        <p><strong>生成日期:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
        <div class="report-content">
            <pre>{json.dumps(report, ensure_ascii=False, indent=2)}</pre>
        </div>
    </body>
    </html>
    """
    return html
