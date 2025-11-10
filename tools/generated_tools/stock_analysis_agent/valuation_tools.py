#!/usr/bin/env python3
"""
估值分析工具

提供DCF、相对估值、市盈率分析等估值方法
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def calculate_dcf_valuation(free_cash_flows: List[float], discount_rate: float, 
                           terminal_growth_rate: float, shares_outstanding: float) -> str:
    """
    计算DCF（现金流折现）估值
    
    使用自由现金流折现模型计算公司的内在价值。
    
    Args:
        free_cash_flows (List[float]): 预测的未来自由现金流列表（通常5-10年）
        discount_rate (float): 折现率（WACC），以小数表示，例如0.10表示10%
        terminal_growth_rate (float): 永续增长率，以小数表示，例如0.03表示3%
        shares_outstanding (float): 流通股数
    
    Returns:
        str: JSON格式的DCF估值结果
    """
    try:
        if not free_cash_flows:
            return json.dumps({
                "success": False,
                "error": "自由现金流数据不能为空"
            }, ensure_ascii=False, indent=2)
        
        if discount_rate <= 0 or discount_rate >= 1:
            return json.dumps({
                "success": False,
                "error": "折现率应在0到1之间"
            }, ensure_ascii=False, indent=2)
        
        if terminal_growth_rate < 0 or terminal_growth_rate >= discount_rate:
            return json.dumps({
                "success": False,
                "error": "永续增长率应小于折现率且大于等于0"
            }, ensure_ascii=False, indent=2)
        
        # 计算预测期现金流的现值
        pv_cash_flows = []
        total_pv = 0
        
        for i, fcf in enumerate(free_cash_flows, start=1):
            pv = fcf / ((1 + discount_rate) ** i)
            pv_cash_flows.append({
                "year": i,
                "free_cash_flow": round(fcf, 2),
                "present_value": round(pv, 2)
            })
            total_pv += pv
        
        # 计算终值
        last_fcf = free_cash_flows[-1]
        terminal_fcf = last_fcf * (1 + terminal_growth_rate)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
        
        # 折现终值
        n_years = len(free_cash_flows)
        pv_terminal_value = terminal_value / ((1 + discount_rate) ** n_years)
        
        # 计算企业价值
        enterprise_value = total_pv + pv_terminal_value
        
        # 计算每股价值
        value_per_share = enterprise_value / shares_outstanding if shares_outstanding > 0 else 0
        
        result = {
            "success": True,
            "valuation_method": "DCF",
            "assumptions": {
                "discount_rate": f"{discount_rate * 100:.2f}%",
                "terminal_growth_rate": f"{terminal_growth_rate * 100:.2f}%",
                "shares_outstanding": shares_outstanding,
                "forecast_years": len(free_cash_flows)
            },
            "cash_flow_analysis": {
                "pv_cash_flows": pv_cash_flows,
                "total_pv_cash_flows": round(total_pv, 2)
            },
            "terminal_value_analysis": {
                "terminal_fcf": round(terminal_fcf, 2),
                "terminal_value": round(terminal_value, 2),
                "pv_terminal_value": round(pv_terminal_value, 2)
            },
            "valuation_results": {
                "enterprise_value": round(enterprise_value, 2),
                "value_per_share": round(value_per_share, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算DCF估值时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算DCF估值失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_relative_valuation(target_metrics: Dict[str, float], 
                                 peer_metrics: List[Dict[str, float]], 
                                 valuation_multiples: List[str]) -> str:
    """
    计算相对估值
    
    使用市盈率(P/E)、市净率(P/B)、市销率(P/S)等相对估值指标进行估值。
    
    Args:
        target_metrics (Dict[str, float]): 目标公司的财务指标，例如 {"eps": 5.0, "revenue": 1000000}
        peer_metrics (List[Dict[str, float]]): 可比公司的财务指标列表
        valuation_multiples (List[str]): 要使用的估值倍数，例如 ["pe", "pb", "ps"]
    
    Returns:
        str: JSON格式的相对估值结果
    """
    try:
        if not peer_metrics:
            return json.dumps({
                "success": False,
                "error": "可比公司数据不能为空"
            }, ensure_ascii=False, indent=2)
        
        # 计算可比公司的平均估值倍数
        peer_averages = {}
        
        for multiple in valuation_multiples:
            values = []
            for peer in peer_metrics:
                if multiple in peer and peer[multiple] is not None:
                    values.append(peer[multiple])
            
            if values:
                peer_averages[multiple] = sum(values) / len(values)
        
        # 应用平均倍数到目标公司
        valuations = {}
        
        for multiple, avg_multiple in peer_averages.items():
            if multiple == "pe" and "eps" in target_metrics:
                valuations["pe_valuation"] = {
                    "multiple": round(avg_multiple, 2),
                    "metric": target_metrics["eps"],
                    "valuation": round(avg_multiple * target_metrics["eps"], 2)
                }
            elif multiple == "pb" and "book_value_per_share" in target_metrics:
                valuations["pb_valuation"] = {
                    "multiple": round(avg_multiple, 2),
                    "metric": target_metrics["book_value_per_share"],
                    "valuation": round(avg_multiple * target_metrics["book_value_per_share"], 2)
                }
            elif multiple == "ps" and "revenue_per_share" in target_metrics:
                valuations["ps_valuation"] = {
                    "multiple": round(avg_multiple, 2),
                    "metric": target_metrics["revenue_per_share"],
                    "valuation": round(avg_multiple * target_metrics["revenue_per_share"], 2)
                }
        
        # 计算平均估值
        valuation_values = [v["valuation"] for v in valuations.values()]
        average_valuation = sum(valuation_values) / len(valuation_values) if valuation_values else 0
        
        result = {
            "success": True,
            "valuation_method": "Relative Valuation",
            "peer_count": len(peer_metrics),
            "peer_averages": peer_averages,
            "target_metrics": target_metrics,
            "valuations": valuations,
            "average_valuation": round(average_valuation, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算相对估值时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算相对估值失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_wacc(equity_weight: float, debt_weight: float, 
                  cost_of_equity: float, cost_of_debt: float, 
                  tax_rate: float) -> str:
    """
    计算加权平均资本成本（WACC）
    
    WACC用作DCF模型中的折现率。
    
    Args:
        equity_weight (float): 权益占比，以小数表示，例如0.7表示70%
        debt_weight (float): 债务占比，以小数表示，例如0.3表示30%
        cost_of_equity (float): 权益成本，以小数表示，例如0.12表示12%
        cost_of_debt (float): 债务成本，以小数表示，例如0.05表示5%
        tax_rate (float): 税率，以小数表示，例如0.25表示25%
    
    Returns:
        str: JSON格式的WACC计算结果
    """
    try:
        # 验证输入
        if abs(equity_weight + debt_weight - 1.0) > 0.01:
            return json.dumps({
                "success": False,
                "error": "权益占比和债务占比之和应为1（100%）"
            }, ensure_ascii=False, indent=2)
        
        # 计算WACC
        # WACC = (E/V) * Re + (D/V) * Rd * (1 - Tc)
        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
        
        result = {
            "success": True,
            "inputs": {
                "equity_weight": f"{equity_weight * 100:.2f}%",
                "debt_weight": f"{debt_weight * 100:.2f}%",
                "cost_of_equity": f"{cost_of_equity * 100:.2f}%",
                "cost_of_debt": f"{cost_of_debt * 100:.2f}%",
                "tax_rate": f"{tax_rate * 100:.2f}%"
            },
            "calculation": {
                "equity_component": round(equity_weight * cost_of_equity, 4),
                "debt_component": round(debt_weight * cost_of_debt * (1 - tax_rate), 4)
            },
            "wacc": {
                "decimal": round(wacc, 4),
                "percentage": f"{wacc * 100:.2f}%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算WACC时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算WACC失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_capm(risk_free_rate: float, beta: float, market_return: float) -> str:
    """
    使用CAPM模型计算权益成本
    
    CAPM: Re = Rf + β * (Rm - Rf)
    
    Args:
        risk_free_rate (float): 无风险利率，以小数表示，例如0.03表示3%
        beta (float): 贝塔系数，衡量股票相对于市场的波动性
        market_return (float): 市场预期回报率，以小数表示，例如0.10表示10%
    
    Returns:
        str: JSON格式的权益成本计算结果
    """
    try:
        # 计算市场风险溢价
        market_risk_premium = market_return - risk_free_rate
        
        # 计算权益成本
        cost_of_equity = risk_free_rate + (beta * market_risk_premium)
        
        result = {
            "success": True,
            "model": "CAPM",
            "inputs": {
                "risk_free_rate": f"{risk_free_rate * 100:.2f}%",
                "beta": round(beta, 2),
                "market_return": f"{market_return * 100:.2f}%"
            },
            "calculation": {
                "market_risk_premium": f"{market_risk_premium * 100:.2f}%",
                "risk_premium": round(beta * market_risk_premium, 4)
            },
            "cost_of_equity": {
                "decimal": round(cost_of_equity, 4),
                "percentage": f"{cost_of_equity * 100:.2f}%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算CAPM时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算CAPM失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_ev_to_ebitda(enterprise_value: float, ebitda: float) -> str:
    """
    计算EV/EBITDA倍数
    
    EV/EBITDA是一个重要的估值指标，常用于并购估值。
    
    Args:
        enterprise_value (float): 企业价值
        ebitda (float): EBITDA（息税折旧摊销前利润）
    
    Returns:
        str: JSON格式的EV/EBITDA计算结果
    """
    try:
        if ebitda <= 0:
            return json.dumps({
                "success": False,
                "error": "EBITDA必须大于0"
            }, ensure_ascii=False, indent=2)
        
        # 计算EV/EBITDA倍数
        ev_to_ebitda = enterprise_value / ebitda
        
        # 评估倍数水平
        if ev_to_ebitda < 8:
            valuation_level = "低估"
        elif ev_to_ebitda < 12:
            valuation_level = "合理"
        elif ev_to_ebitda < 15:
            valuation_level = "略高"
        else:
            valuation_level = "高估"
        
        result = {
            "success": True,
            "inputs": {
                "enterprise_value": round(enterprise_value, 2),
                "ebitda": round(ebitda, 2)
            },
            "ev_to_ebitda": round(ev_to_ebitda, 2),
            "valuation_level": valuation_level,
            "industry_benchmarks": {
                "low": "< 8",
                "fair": "8-12",
                "slightly_high": "12-15",
                "high": "> 15"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算EV/EBITDA时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算EV/EBITDA失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_peg_ratio(pe_ratio: float, earnings_growth_rate: float) -> str:
    """
    计算PEG比率
    
    PEG比率 = P/E / 盈利增长率，用于评估成长股的估值。
    
    Args:
        pe_ratio (float): 市盈率
        earnings_growth_rate (float): 盈利增长率，以百分比表示，例如15表示15%
    
    Returns:
        str: JSON格式的PEG比率计算结果
    """
    try:
        if earnings_growth_rate <= 0:
            return json.dumps({
                "success": False,
                "error": "盈利增长率必须大于0"
            }, ensure_ascii=False, indent=2)
        
        # 计算PEG比率
        peg_ratio = pe_ratio / earnings_growth_rate
        
        # 评估PEG水平
        if peg_ratio < 0.5:
            valuation_level = "严重低估"
        elif peg_ratio < 1.0:
            valuation_level = "低估"
        elif peg_ratio < 1.5:
            valuation_level = "合理"
        elif peg_ratio < 2.0:
            valuation_level = "略高"
        else:
            valuation_level = "高估"
        
        result = {
            "success": True,
            "inputs": {
                "pe_ratio": round(pe_ratio, 2),
                "earnings_growth_rate": f"{earnings_growth_rate}%"
            },
            "peg_ratio": round(peg_ratio, 2),
            "valuation_level": valuation_level,
            "interpretation": {
                "< 0.5": "严重低估",
                "0.5-1.0": "低估",
                "1.0-1.5": "合理",
                "1.5-2.0": "略高",
                "> 2.0": "高估"
            },
            "note": "PEG < 1 通常表示股票可能被低估，但需要结合其他因素综合判断",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算PEG比率时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算PEG比率失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_dividend_discount_model(dividends: List[float], growth_rate: float, 
                                     required_return: float) -> str:
    """
    使用股利折现模型（DDM）计算股票内在价值
    
    适用于稳定派息的公司。使用Gordon增长模型。
    
    Args:
        dividends (List[float]): 历史股利列表
        growth_rate (float): 股利增长率，以小数表示，例如0.05表示5%
        required_return (float): 要求回报率，以小数表示，例如0.10表示10%
    
    Returns:
        str: JSON格式的DDM估值结果
    """
    try:
        if not dividends:
            return json.dumps({
                "success": False,
                "error": "股利数据不能为空"
            }, ensure_ascii=False, indent=2)
        
        if growth_rate >= required_return:
            return json.dumps({
                "success": False,
                "error": "增长率必须小于要求回报率"
            }, ensure_ascii=False, indent=2)
        
        # 使用最新股利计算下期股利
        latest_dividend = dividends[0]
        next_dividend = latest_dividend * (1 + growth_rate)
        
        # Gordon增长模型: P0 = D1 / (r - g)
        intrinsic_value = next_dividend / (required_return - growth_rate)
        
        # 计算历史股利增长率
        if len(dividends) >= 2:
            historical_growth_rates = []
            for i in range(len(dividends) - 1):
                if dividends[i+1] > 0:
                    growth = ((dividends[i] - dividends[i+1]) / dividends[i+1])
                    historical_growth_rates.append(growth)
            
            avg_historical_growth = sum(historical_growth_rates) / len(historical_growth_rates) if historical_growth_rates else 0
        else:
            avg_historical_growth = 0
        
        result = {
            "success": True,
            "model": "Dividend Discount Model (Gordon Growth)",
            "inputs": {
                "latest_dividend": round(latest_dividend, 2),
                "growth_rate": f"{growth_rate * 100:.2f}%",
                "required_return": f"{required_return * 100:.2f}%"
            },
            "calculation": {
                "next_dividend": round(next_dividend, 2),
                "discount_rate": f"{(required_return - growth_rate) * 100:.2f}%"
            },
            "intrinsic_value": round(intrinsic_value, 2),
            "historical_analysis": {
                "dividend_count": len(dividends),
                "average_historical_growth": f"{avg_historical_growth * 100:.2f}%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算DDM估值时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算DDM估值失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def calculate_price_targets(current_price: float, valuations: Dict[str, float], 
                           confidence_level: str = "medium") -> str:
    """
    基于多种估值方法综合计算目标价格
    
    综合DCF、相对估值等多种方法得出的估值，计算目标价格区间。
    
    Args:
        current_price (float): 当前股价
        valuations (Dict[str, float]): 不同估值方法得出的价值，例如 {"dcf": 100, "pe": 95, "pb": 105}
        confidence_level (str): 置信水平，可选值: "low", "medium", "high"
    
    Returns:
        str: JSON格式的目标价格分析结果
    """
    try:
        if not valuations:
            return json.dumps({
                "success": False,
                "error": "估值数据不能为空"
            }, ensure_ascii=False, indent=2)
        
        # 计算平均估值
        valuation_values = list(valuations.values())
        average_valuation = sum(valuation_values) / len(valuation_values)
        
        # 计算标准差
        variance = sum((x - average_valuation) ** 2 for x in valuation_values) / len(valuation_values)
        std_dev = variance ** 0.5
        
        # 根据置信水平设置目标价格区间
        confidence_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5
        }
        
        multiplier = confidence_multipliers.get(confidence_level, 1.0)
        
        # 计算目标价格区间
        lower_target = average_valuation - (std_dev * multiplier)
        upper_target = average_valuation + (std_dev * multiplier)
        
        # 计算潜在回报
        potential_return = ((average_valuation - current_price) / current_price) * 100
        lower_return = ((lower_target - current_price) / current_price) * 100
        upper_return = ((upper_target - current_price) / current_price) * 100
        
        # 生成投资建议
        if potential_return > 20:
            recommendation = "强烈买入"
        elif potential_return > 10:
            recommendation = "买入"
        elif potential_return > -10:
            recommendation = "持有"
        elif potential_return > -20:
            recommendation = "卖出"
        else:
            recommendation = "强烈卖出"
        
        result = {
            "success": True,
            "current_price": round(current_price, 2),
            "valuations": valuations,
            "analysis": {
                "average_valuation": round(average_valuation, 2),
                "standard_deviation": round(std_dev, 2),
                "confidence_level": confidence_level
            },
            "price_targets": {
                "base_target": round(average_valuation, 2),
                "lower_target": round(lower_target, 2),
                "upper_target": round(upper_target, 2),
                "target_range": f"${round(lower_target, 2)} - ${round(upper_target, 2)}"
            },
            "potential_returns": {
                "base_return": f"{potential_return:.2f}%",
                "lower_return": f"{lower_return:.2f}%",
                "upper_return": f"{upper_return:.2f}%"
            },
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算目标价格时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"计算目标价格失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def sensitivity_analysis(base_valuation: float, variable_name: str, 
                        variable_range: List[float], impact_factor: float) -> str:
    """
    敏感性分析
    
    分析关键变量变化对估值的影响。
    
    Args:
        base_valuation (float): 基准估值
        variable_name (str): 变量名称，例如 "discount_rate", "growth_rate"
        variable_range (List[float]): 变量取值范围
        impact_factor (float): 影响系数，表示变量每变化1%对估值的影响
    
    Returns:
        str: JSON格式的敏感性分析结果
    """
    try:
        if not variable_range:
            return json.dumps({
                "success": False,
                "error": "变量范围不能为空"
            }, ensure_ascii=False, indent=2)
        
        # 计算不同变量值下的估值
        sensitivity_results = []
        
        for value in variable_range:
            # 简化的敏感性计算
            valuation_change = base_valuation * impact_factor * value
            adjusted_valuation = base_valuation + valuation_change
            
            sensitivity_results.append({
                "variable_value": round(value, 4),
                "valuation": round(adjusted_valuation, 2),
                "change_from_base": round(valuation_change, 2),
                "change_percentage": f"{(valuation_change / base_valuation) * 100:.2f}%"
            })
        
        # 找出最敏感的范围
        max_change = max(abs(r["change_from_base"]) for r in sensitivity_results)
        
        result = {
            "success": True,
            "base_valuation": round(base_valuation, 2),
            "variable_name": variable_name,
            "impact_factor": impact_factor,
            "sensitivity_results": sensitivity_results,
            "analysis": {
                "max_absolute_change": round(max_change, 2),
                "sensitivity_level": "高" if max_change / base_valuation > 0.2 else "中" if max_change / base_valuation > 0.1 else "低"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"进行敏感性分析时出错: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"敏感性分析失败: {str(e)}"
        }, ensure_ascii=False, indent=2)
