#!/usr/bin/env python3
"""
AWS Network Architecture Analyzer Agent

专业的AWS网络架构分析专家，能够自动化采集AWS资源配置信息并生成网络架构拓扑图。
支持AWS资源自动发现与映射、网络拓扑关系分析与构建、网络架构可视化生成、合规性评估与报告、
多格式输出生成以及历史数据比较分析功能。满足NIST CSF 2.0 ID.AM-03和CISA CPGs 2.P合规要求。
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional, Union, Any, Tuple
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置遥测
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='AWS Network Architecture Analyzer')
    parser.add_argument('--profile', type=str, help='AWS Profile名称，默认使用默认Profile')
    parser.add_argument('--region', type=str, required=True, help='AWS Region名称')
    parser.add_argument('--output-format', type=str, default='PNG', 
                        choices=['PNG', 'SVG', 'PDF', 'HTML', 'JSON', 'YAML'],
                        help='输出格式选项')
    parser.add_argument('--cache-option', type=str, default='使用缓存',
                        choices=['使用缓存', '强制刷新'],
                        help='缓存选项')
    parser.add_argument('--detail-level', type=str, default='标准',
                        choices=['基本', '标准', '详细'],
                        help='详细程度选项')
    parser.add_argument('--comparison-id', type=str, help='历史比较选项(比较目标ID)')
    parser.add_argument('--additional', type=str, help='附加说明和要求')
    
    return parser.parse_args()

def format_user_input(args: argparse.Namespace) -> str:
    """
    格式化用户输入为Agent可处理的格式
    
    Args:
        args: 命令行参数
        
    Returns:
        str: 格式化后的用户输入
    """
    user_input = f"请根据以下参数分析AWS网络架构：\n\n"
    
    if args.profile:
        user_input += f"- AWS Profile: {args.profile}\n"
    else:
        user_input += f"- AWS Profile: 默认\n"
    
    user_input += f"- AWS Region: {args.region}\n"
    user_input += f"- 输出格式: {args.output_format}\n"
    user_input += f"- 缓存选项: {args.cache_option}\n"
    user_input += f"- 详细程度: {args.detail_level}\n"
    
    if args.comparison_id:
        user_input += f"- 历史比较ID: {args.comparison_id}\n"
    
    if args.additional:
        user_input += f"\n附加说明：\n{args.additional}\n"
    
    return user_input

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建 agent 的通用参数
    agent_params = {
        "env": "production",
        "version": "latest", 
        "model_id": "default"
    }
    
    # 使用 agent_factory 创建 agent
    print("正在初始化AWS网络架构分析Agent...")
    aws_network_analyzer = create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/aws_network_analyzer/aws_network_analyzer_agent", 
        **agent_params
    )
    print(f"✅ AWS Network Architecture Analyzer Agent 创建成功")
    
    # 格式化用户输入
    user_input = format_user_input(args)
    print("\n🔍 开始分析AWS网络架构...")
    
    try:
        # 调用Agent处理请求
        result = aws_network_analyzer(user_input)
        print("\n📋 分析结果:")
        print(result)
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()