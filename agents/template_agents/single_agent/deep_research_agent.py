#!/usr/bin/env python3
"""
深度研究Agent模板

专业的深度研究专家，能够进行全面的信息收集、分析和综合。
支持多源信息收集、深度分析、报告生成、知识综合等功能。
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
agent_config_path = "template_prompts/deep_research_agent"

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

# 使用 agent_factory 创建 agent
deep_researcher = create_deep_research_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）

    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}, session_id: {session_id}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return

    print(f"🔄 Processing prompt: {prompt}")

    try:
        # 使用流式响应
        stream = deep_researcher.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 Streaming event: {event}")
            yield event

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        yield f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='深度研究Agent测试')
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入内容')
    parser.add_argument('-t', '--topic', type=str, default="请对人工智能在医疗领域的应用进行深度研究", help='研究主题')
    parser.add_argument('-s', '--scope', type=str, default="技术发展、应用现状、未来趋势", help='研究范围')
    parser.add_argument('-d', '--depth', type=str, choices=['basic', 'intermediate', 'advanced'], default='intermediate', help='研究深度')
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
        deep_researcher = create_deep_research_agent(env=args.env, version=args.version)
        print(f"✅ Deep Research Agent 创建成功: {deep_researcher.name}")
        print(f"📝 输入: {args.input}")
        try:
            result = deep_researcher(args.input)
            print(f"📋 响应: {result}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
