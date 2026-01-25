#!/usr/bin/env python3
"""
simple_agent - HTML文档生成与S3上传Agent

专业的HTML文档生成与S3存储专家，能够根据用户提供的内容和格式要求，
自动生成高质量的HTML文档，上传至AWS S3存储桶，并返回可访问的预签名URL。

功能特性：
- 自然语言理解：解析用户的文档内容和格式要求
- HTML5文档生成：使用AI模型生成符合标准的HTML文档
- S3文件上传：将生成的HTML文件上传至指定S3存储桶
- 预签名URL生成：创建带有过期时间的临时访问链接
- 流式响应：提供实时进度反馈
- 错误处理：完善的异常捕获和友好的错误提示

技术栈：
- Python 3.13+
- Strands SDK (Agent框架)
- AWS Bedrock (Claude Sonnet 4.5)
- boto3 SDK (S3集成)
- BedrockAgentCoreApp (部署框架)

作者：agent build workflow
版本：1.0.0
创建日期：2026-01-24
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
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# ==================== Agent 配置 ====================
AGENT_CONFIG_PATH = "generated_agents_prompts/simple_agent/simple_agent"

def create_simple_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
) -> Any:
    """
    创建 simple_agent 实例
    
    Args:
        env: 运行环境 (development/production/testing)
        version: Agent版本
        model_id: 模型ID
        enable_logging: 是否启用日志
        
    Returns:
        创建的Agent实例
    """
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id,
        "enable_logging": enable_logging
    }
    return create_agent_from_prompt_template(
        agent_name=AGENT_CONFIG_PATH,
        **agent_params
    )

# 使用 agent_factory 创建 agent
simple_agent = create_simple_agent()

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
            - session_id: 会话ID（可选）
            - media: 媒体文件列表（可选）
            - expiration: URL过期时间（可选，默认3600秒）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）
            
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
        
    Returns:
        str: 最终响应文本（非流式模式）
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}, session_id: {session_id}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return
    
    print(f"🔄 Processing prompt: {prompt}")
    
    try:
        # 使用流式响应
        stream = simple_agent.stream_async(prompt)
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
    
    parser = argparse.ArgumentParser(
        description='simple_agent - HTML文档生成与S3上传Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 本地测试
  python simple_agent.py -i "生成一个产品介绍页面"
  
  # 交互式对话
  python simple_agent.py -it
  
  # 指定环境和版本
  python simple_agent.py -i "创建报告页面" -e development -v latest
  
  # 启动服务器（AgentCore部署）
  python simple_agent.py
        """
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入内容'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['development', 'production', 'testing'],
        help='指定Agent运行环境'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本'
    )
    parser.add_argument(
        '-it', '--interactive',
        action='store_true',
        default=False,
        help='启动交互式多轮对话模式'
    )
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📋 Agent: simple_agent")
        print("📝 描述: HTML文档生成与S3上传Agent")
        print("🔧 配置: awesome-nexus-ai-file-storage")
        app.run()
    elif args.input:
        # 本地测试模式
        agent = create_simple_agent(env=args.env, version=args.version)
        print(f"✅ Agent创建成功: {agent.name}")
        print(f"📝 输入: {args.input}")
        print(f"📋 响应: ")
        try:
            result = agent(args.input)
            print(result)
        except Exception as e:
            print(f"❌ 错误: {e}")
    elif args.interactive:
        # 交互式对话模式
        agent = create_simple_agent(env=args.env, version=args.version)
        print(f"✅ Agent创建成功: {agent.name}")
        print("💬 进入交互式对话模式（输入 'quit' 或 'exit' 退出）\n")
        
        while True:
            try:
                user_input = input("You: ")
                user_input = user_input.encode('utf-8', errors='ignore').decode('utf-8').strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                if not user_input:
                    continue
                
                agent(user_input)
                print()
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📋 Agent: simple_agent")
        print("📝 描述: HTML文档生成与S3上传Agent")
        print("🔧 配置: awesome-nexus-ai-file-storage")
        print("💡 提示: 使用 -i 参数进行本地测试，使用 -it 参数启动交互式对话")
        app.run()
