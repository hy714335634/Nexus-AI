#!/usr/bin/env python3
"""
深度研究Agent模板

专业的深度研究专家，能够进行全面的信息收集、分析和综合。
支持多源信息收集、深度分析、报告生成、知识综合等功能。
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数生成方法
def create_deep_research_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    agent_params = {
        "env": env,
        "version": version, 
        "model_id": model_id,
        "enable_logging": True
    }
    return create_agent_from_prompt_template(
        agent_name=agent_config_path, 
        **agent_params
    )

agent_config_path = "template_prompts/deep_research_agent"  

# 使用 agent_factory 创建 agent
deep_researcher = create_deep_research_agent()

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='深度研究Agent测试')
    parser.add_argument('-t', '--topic', type=str, 
                       default="请对人工智能在医疗领域的应用进行深度研究",
                       help='研究主题')
    parser.add_argument('-s', '--scope', type=str, 
                       default="技术发展、应用现状、未来趋势",
                       help='研究范围')
    parser.add_argument('-d', '--depth', type=str, 
                       choices=['basic', 'intermediate', 'advanced'],
                       default='intermediate',
                       help='研究深度')
    parser.add_argument('-e', '--env', type=str,
                       default="production",
                       help='指定Agent运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str,
                       default="latest",
                       help='指定Agent版本 (默认: latest)')
    args = parser.parse_args()

    deep_researcher = create_deep_research_agent(env=args.env, version=args.version)

    print(f"✅ Deep Research Agent 创建成功: {deep_researcher.name}")
    
    # 构建测试输入
    test_input = f"""
研究主题: {args.topic}
研究范围: {args.scope}
研究深度: {args.depth}

请进行深度研究并提供详细的分析报告。
"""
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = deep_researcher(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
