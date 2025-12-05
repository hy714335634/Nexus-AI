#!/usr/bin/env python3
"""
数据分析Agent模板

专业的数据分析专家，能够处理各种数据格式并进行统计分析。
支持数据预处理、统计分析、图表生成、报告输出等功能。
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
agent_config_path = "template_prompts/data_analyzer_agent"

# 创建 agent 的通用参数生成方法
def create_data_analyzer_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
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
data_analyzer = create_data_analyzer_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点（支持流式响应）

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            - media: 媒体文件列表（可选）

    Yields:
        str: 流式响应的文本片段（自动处理流式传输）

    Returns:
        str: 最终响应文本（非流式模式）
    """
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        return "Error: Missing 'prompt' in request"

    print(f"🔄 Processing prompt: {prompt}")

    try:
        # 使用流式响应
        stream = data_analyzer.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 Streaming event: {event}")
            yield event

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='数据分析Agent测试')
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入内容')
    parser.add_argument('-f', '--file', type=str, help='要分析的数据文件路径')
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
        data_analyzer = create_data_analyzer_agent(env=args.env, version=args.version)
        print(f"✅ Data Analyzer Agent 创建成功: {data_analyzer.name}")
        test_input = args.input
        if args.file:
            test_input += f"\n数据文件路径: {args.file}"
        print(f"📝 输入: {test_input}")
        try:
            result = data_analyzer(test_input)
            print(f"📋 响应: {result}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
