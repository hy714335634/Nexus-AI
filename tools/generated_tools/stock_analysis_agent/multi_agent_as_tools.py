#!/usr/bin/env python3
"""
股票分析多Agent工具集

将股票分析系统中的各个专业Agent封装为工具函数，支持agents as tools模式
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from strands import tool

from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stock_analysis_multi_agent_tools")

# 加载配置
loader = ConfigLoader()
# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 导入Strands SDK
from nexus_utils.agent_factory import create_agent_from_prompt_template


def _parse_agent_response(response: Any) -> str:
    """
    解析Agent响应并转换为字符串
    
    Args:
        response: Agent响应对象
        
    Returns:
        str: 解析后的字符串结果
    """
    try:
        # 多层级属性检查
        if hasattr(response, 'message'):
            message = response.message
        elif hasattr(response, 'content') and response.content:
            message = response.content
        elif isinstance(response, str):
            return response
        elif hasattr(response, 'text'):
            return response.text
        else:
            message = response
        
        # 处理message可能是字典的情况
        if isinstance(message, dict):
            # 提取content中的text内容
            if "content" in message:
                text_parts = []
                for item in message["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                    elif isinstance(item, str):
                        text_parts.append(item)
                if text_parts:
                    return "\n".join(text_parts)
            # 如果不是标准格式，转为JSON字符串
            return json.dumps(message, ensure_ascii=False)
        else:
            return str(message)
            
    except Exception as e:
        logger.error(f"响应解析失败: {str(e)}")
        return f"响应解析异常: {str(e)}"


@tool
def data_collector_agent_tool(content: str, env: str = "production", 
                               version: str = "latest", model_id: str = "default") -> str:
    """
    数据采集Agent工具
    
    用于收集股票相关的财务数据、市场数据等信息。
    
    Args:
        content: 数据采集请求内容，例如："请收集AAPL公司最近一年的财务数据"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 数据采集结果（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/data_collector_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"数据采集Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def valuation_agent_tool(content: str, env: str = "production", 
                         version: str = "latest", model_id: str = "default") -> str:
    """
    估值Agent工具
    
    用于执行DCF（现金流折现）估值分析。
    
    Args:
        content: 估值分析请求内容，例如："请对AAPL公司进行DCF估值分析"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 估值分析结果（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/valuation_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"估值Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def prediction_agent_tool(content: str, env: str = "production", 
                           version: str = "latest", model_id: str = "default") -> str:
    """
    预测Agent工具
    
    用于进行盈利预测和未来业绩预测。
    
    Args:
        content: 预测分析请求内容，例如："请预测AAPL公司未来3个季度的盈利情况"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 预测分析结果（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/prediction_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"预测Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def risk_assessment_agent_tool(content: str, env: str = "production", 
                               version: str = "latest", model_id: str = "default") -> str:
    """
    风险评估Agent工具
    
    用于评估股票投资的风险因素。
    
    Args:
        content: 风险评估请求内容，例如："请评估AAPL公司的投资风险"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 风险评估结果（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/risk_assessment_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"风险评估Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def benchmark_agent_tool(content: str, env: str = "production", 
                         version: str = "latest", model_id: str = "default") -> str:
    """
    对比分析Agent工具
    
    用于进行股票与同行业或市场基准的对比分析。
    
    Args:
        content: 对比分析请求内容，例如："请将AAPL公司与同行业公司进行对比分析"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 对比分析结果（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/benchmark_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"对比分析Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def report_generator_agent_tool(content: str, env: str = "production", 
                                version: str = "latest", model_id: str = "default") -> str:
    """
    报告生成Agent工具
    
    用于生成完整的股票分析报告。
    
    Args:
        content: 报告生成请求内容，例如："请生成AAPL公司的完整分析报告"
        env: 环境配置，默认为"production"
        version: 版本，默认为"latest"
        model_id: 模型ID，默认为"default"
        
    Returns:
        str: 分析报告（字符串格式）
    """
    try:
        agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/stock_analysis_agent/report_generator_agent",
            env=env,
            version=version,
            model_id=model_id
        )
        response = agent(content)
        return _parse_agent_response(response)
    except Exception as e:
        error_msg = f"报告生成Agent执行失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

