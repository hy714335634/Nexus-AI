#!/usr/bin/env python3
"""
内容生成Agent模板

专业的内容生成专家，能够根据需求生成各种类型的内容。
支持文章写作、报告生成、创意内容、营销文案等功能。
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
agent_config_path = "template_prompts/content_generator_agent"

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

# 使用 agent_factory 创建 agent
content_generator = create_content_generator_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息

    Returns:
        str: 响应文本
    """
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        return "Error: Missing 'prompt' in request"

    print(f"🔄 Processing prompt: {prompt}")

    try:
        result = content_generator(prompt)

        # 提取响应内容 - 适配 Strands Agent 返回格式
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                response_text = content[0].get('text', str(result))
            else:
                response_text = str(result)
        elif hasattr(result, 'content') and result.content:
            response_text = result.content
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)

        print(f"✅ Response: {response_text[:200]}...")
        return response_text

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='内容生成Agent测试')
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入内容')
    parser.add_argument('-t', '--type', type=str, default="article", help='内容类型')
    parser.add_argument('-e', '--env', type=str, default="production", help='指定Agent运行环境')
    parser.add_argument('-v', '--version', type=str, default="latest", help='指定Agent版本')
    args = parser.parse_args()

    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    elif args.input:
        # 本地测试模式
        content_generator = create_content_generator_agent(env=args.env, version=args.version)
        print(f"✅ Content Generator Agent 创建成功: {content_generator.name}")
        test_input = args.input
        if args.type:
            test_input += f"\n内容类型: {args.type}"
        print(f"📝 输入: {test_input}")
        try:
            result = content_generator(test_input)
            print(f"📋 响应: {result}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
