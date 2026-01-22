#!/usr/bin/env python3
"""
FDA数据查询Agent

专业的FDA数据查询专家，能够通过自然语言理解用户查询需求，
实时访问FDA openFDA API获取药物、医疗设备、食品等公开数据，
提供客观、详细、可追溯来源的专业回答。

功能特点：
- 自然语言查询理解和意图识别
- 实时FDA API数据访问
- 药物、医疗设备、食品、不良事件、召回数据查询
- 数据来源100%可追溯
- 智能错误处理和降级策略
- 查询结果缓存机制
- 多轮对话和上下文管理
- 流式响应支持
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# 初始化配置加载器
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置OTLP导出器
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

# Agent 配置路径
AGENT_CONFIG_PATH = "generated_agents_prompts/fda_data_query_agent/fda_data_query_agent_prompt"


def create_fda_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
):
    """
    创建FDA数据查询Agent实例
    
    Args:
        env: 运行环境 (development/production/testing)
        version: Agent版本
        model_id: 模型ID
        enable_logging: 是否启用日志
        
    Returns:
        Agent实例
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


# 创建默认Agent实例
fda_agent = create_fda_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
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
    
    # 提取prompt
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return
    
    print(f"🔄 Processing prompt: {prompt}")
    
    try:
        # 使用流式响应
        stream = fda_agent.stream_async(prompt)
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
        description='FDA数据查询Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 单次查询
  python fda_data_query_agent.py -i "查询阿司匹林的FDA批准信息"
  
  # 交互式对话
  python fda_data_query_agent.py -it
  
  # 指定环境和版本
  python fda_data_query_agent.py -i "查询胰岛素的不良事件" -e production -v latest
  
  # 启动AgentCore服务器
  python fda_data_query_agent.py
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试查询内容（单次查询模式）'
    )
    parser.add_argument(
        '-it', '--interactive',
        action='store_true',
        default=False,
        help='启动交互式多轮对话模式'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['development', 'production', 'testing'],
        help='指定Agent运行环境（默认：production）'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本（默认：latest）'
    )
    parser.add_argument(
        '-m', '--model',
        type=str,
        default="default",
        help='指定模型ID（默认：default）'
    )
    
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📡 端点: /invocations")
        print("🔧 环境: AgentCore 部署模式")
        app.run()
    
    elif args.input:
        # 本地测试模式（单次查询）
        print("=" * 80)
        print("🧪 FDA数据查询Agent - 本地测试模式")
        print("=" * 80)
        
        # 创建Agent实例
        test_agent = create_fda_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        print(f"✅ Agent创建成功: {test_agent.name}")
        print(f"🔧 环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print(f"🤖 模型: {args.model}")
        print("-" * 80)
        print(f"📝 查询: {args.input}")
        print("-" * 80)
        
        try:
            # 执行查询
            result = test_agent(args.input)
            print(f"📋 响应:\n{result}")
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
        
        print("=" * 80)
    
    elif args.interactive:
        # 交互式对话模式
        print("=" * 80)
        print("💬 FDA数据查询Agent - 交互式对话模式")
        print("=" * 80)
        
        # 创建Agent实例
        interactive_agent = create_fda_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        print(f"✅ Agent创建成功: {interactive_agent.name}")
        print(f"🔧 环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print(f"🤖 模型: {args.model}")
        print("-" * 80)
        print("💡 提示：")
        print("  - 输入查询内容进行FDA数据查询")
        print("  - 支持多轮对话和上下文理解")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("  - 使用 Ctrl+C 强制退出")
        print("=" * 80)
        print()
        
        while True:
            try:
                # 获取用户输入
                user_input = input("You: ").strip()
                
                # 检查退出命令
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                
                # 忽略空输入
                if not user_input:
                    continue
                
                # 执行查询
                print()
                result = interactive_agent(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"\n❌ 错误: {str(e)}\n")
    
    else:
        # 默认启动AgentCore服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📡 端点: /invocations")
        print("💡 提示: 使用 -i 参数进行本地测试，使用 -it 参数启动交互式对话")
        app.run()
