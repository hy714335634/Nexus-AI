#!/usr/bin/env python3
"""
思维导图生成Agent

专业的思维导图生成助手，能够根据用户提供的话题或文本内容，
智能分析内容结构和逻辑关系，自动生成清晰、层次分明的思维导图。
支持Markdown、Mermaid、JSON三种输出格式，提供流式响应。

Author: Nexus-AI Agent Build Workflow
Date: 2026-01-22
Version: 1.0.0
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# ==================== 环境配置 ====================
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置OTLP遥测端点
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# ==================== Agent配置 ====================
# Agent提示词配置路径
AGENT_PROMPT_PATH = "generated_agents_prompts/mindmap_generator/mindmap_generator_prompt"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()


def create_mindmap_generator_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
):
    """
    创建思维导图生成Agent实例
    
    Args:
        env: 运行环境（development/testing/production）
        version: Agent版本（默认latest）
        model_id: 模型ID（默认default，使用Claude Sonnet 4.5）
    
    Returns:
        Agent实例
    """
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id,
        "enable_logging": True
    }
    
    print(f"🔧 创建思维导图生成Agent...")
    print(f"   环境: {env}")
    print(f"   版本: {version}")
    print(f"   模型: {model_id}")
    
    agent = create_agent_from_prompt_template(
        agent_name=AGENT_PROMPT_PATH,
        **agent_params
    )
    
    print(f"✅ Agent创建成功: {agent.name}")
    return agent


# 使用生产环境配置创建Agent
mindmap_generator = create_mindmap_generator_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必需）
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）
    
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    
    Returns:
        str: 错误信息（仅在异常时返回）
    """
    session_id = context.session_id
    print(f"📥 收到请求 - Session ID: {session_id}")
    print(f"📦 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    # 验证输入
    if not prompt:
        error_msg = "Error: 缺少 'prompt' 参数。请提供您想要生成思维导图的话题或文本内容。"
        print(f"❌ {error_msg}")
        yield error_msg
        return
    
    # 检查输入长度
    if len(prompt) > 10000:
        error_msg = "Error: 输入内容过长（超过10000字）。建议您将内容分为几个部分，或者提炼出核心内容。"
        print(f"❌ {error_msg}")
        yield error_msg
        return
    
    print(f"🔄 开始处理思维导图生成...")
    print(f"📝 用户输入长度: {len(prompt)} 字符")
    
    try:
        # 使用流式响应
        stream = mindmap_generator.stream_async(prompt)
        
        # 流式输出生成的内容
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 流式输出: {event[:100]}..." if len(event) > 100 else f"📤 流式输出: {event}")
            yield event
        
        print("✅ 思维导图生成完成")
    
    except Exception as e:
        error_msg = f"Error: 生成思维导图时发生错误 - {str(e)}"
        print(f"❌ {error_msg}")
        yield error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='思维导图生成Agent - 将话题或文本转化为结构化思维导图',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 本地测试（单次）
  python mindmap_generator.py -i "人工智能"
  
  # 本地测试（交互式）
  python mindmap_generator.py -it
  
  # 指定环境和版本
  python mindmap_generator.py -i "项目管理" -e development -v latest
  
  # 启动HTTP服务器（AgentCore部署模式）
  python mindmap_generator.py
        """
    )
    
    parser.add_argument('-i', '--input', type=str, default=None,
                        help='测试输入（话题或文本内容）')
    parser.add_argument('-e', '--env', type=str, default="production",
                        choices=['development', 'testing', 'production'],
                        help='指定Agent运行环境（默认: production）')
    parser.add_argument('-v', '--version', type=str, default="latest",
                        help='指定Agent版本（默认: latest）')
    parser.add_argument('-it', '--interactive', action='store_true',
                        help='启动交互式多轮对话模式')
    
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # ==================== AgentCore 部署模式 ====================
        print("=" * 60)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 60)
        print(f"📡 监听端口: 8080")
        print(f"🔗 端点: /invocations")
        print(f"🤖 Agent: {mindmap_generator.name}")
        print("=" * 60)
        app.run()
    
    elif args.interactive:
        # ==================== 交互式对话模式 ====================
        agent = create_mindmap_generator_agent(env=args.env, version=args.version)
        
        print("=" * 60)
        print("💬 思维导图生成Agent - 交互式对话模式")
        print("=" * 60)
        print(f"🤖 Agent: {agent.name}")
        print(f"🌍 环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print("=" * 60)
        print("💡 提示:")
        print("  - 输入话题或文本内容，我将为您生成思维导图")
        print("  - 支持Markdown、Mermaid、JSON三种输出格式")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("=" * 60)
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                
                if not user_input:
                    continue
                
                if len(user_input) > 10000:
                    print("⚠️  输入内容过长（超过10000字），建议缩短内容。\n")
                    continue
                
                print(f"\n🔄 正在生成思维导图...\n")
                result = agent(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")
    
    elif args.input:
        # ==================== 本地测试模式 ====================
        agent = create_mindmap_generator_agent(env=args.env, version=args.version)
        
        print("=" * 60)
        print("🧪 思维导图生成Agent - 本地测试")
        print("=" * 60)
        print(f"🤖 Agent: {agent.name}")
        print(f"🌍 环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print("=" * 60)
        print(f"📝 输入: {args.input}")
        print("=" * 60)
        print()
        
        try:
            if len(args.input) > 10000:
                print("⚠️  输入内容过长（超过10000字），建议缩短内容。")
            else:
                print("🔄 正在生成思维导图...\n")
                result = agent(args.input)
                print("\n" + "=" * 60)
                print("✅ 生成完成")
                print("=" * 60)
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    else:
        # ==================== 默认启动服务器 ====================
        print("=" * 60)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 60)
        print(f"📡 监听端口: 8080")
        print(f"🔗 端点: /invocations")
        print(f"🤖 Agent: {mindmap_generator.name}")
        print("=" * 60)
        print("💡 提示: 使用 -i 参数进行本地测试")
        print("   示例: python mindmap_generator.py -i '人工智能'")
        print("=" * 60)
        app.run()
