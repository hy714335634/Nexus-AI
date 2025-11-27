#!/usr/bin/env python3
"""
内容生成Agent模板

专业的内容生成专家，能够根据需求生成各种类型的内容。
支持文章写作、报告生成、创意内容、营销文案等功能。
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
def create_content_generator_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
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

agent_config_path = "template_prompts/content_generator_agent"

# 使用 agent_factory 创建 agent
content_generator = create_content_generator_agent()


# ==================== AgentCore 入口点（必须包含）====================
from typing import Dict, Any

def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    AgentCore 标准入口点
    """
    prompt = event.get("prompt") or event.get("message") or event.get("input", "")
    if not prompt:
        return {"success": False, "error": "Missing 'prompt' in request"}
    try:
        result = content_generator(prompt)
        response_text = result.content if hasattr(result, 'content') else str(result)
        return {"success": True, "response": response_text}
    except Exception as e:
        return {"success": False, "error": str(e)}

invoke = handler
main = handler


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='内容生成Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请根据主题生成一篇高质量的文章",
                       help='测试输入内容')
    parser.add_argument('-t', '--type', type=str, 
                       default="article",
                       help='内容类型 (article, report, marketing, creative)')
    parser.add_argument('-e', '--env', type=str,
                       default="production",
                       help='指定Agent运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str,
                       default="latest",
                       help='指定Agent版本 (默认: latest)')
    args = parser.parse_args()

    content_generator = create_content_generator_agent(env=args.env, version=args.version)

    print(f"✅ Content Generator Agent 创建成功: {content_generator.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.type:
        test_input += f"\n内容类型: {args.type}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = content_generator(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
