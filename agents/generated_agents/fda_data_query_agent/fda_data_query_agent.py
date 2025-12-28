#!/usr/bin/env python3
"""
FDA数据查询智能体

专业的FDA数据查询和专业问答专家，能够通过自然语言交互理解用户查询意图，
调用openFDA官方API获取药物、医疗设备、食品等FDA公开数据，
提供准确、详细、可验证的专业问答服务。

功能特性：
- 自然语言查询解析：识别查询类型、提取关键实体、映射API参数
- 多类型FDA数据查询：支持药物、医疗设备、食品、不良事件等多个端点
- 数据提取和格式化：提取关键信息、生成结构化展示
- 专业问答和推理：多步推理、比较分析、趋势评估
- 数据来源追溯：生成完整的数据来源信息
- 缓存管理：智能缓存提升响应速度
- 错误处理和降级：完善的异常处理策略
- 数据不足处理：智能提示和替代建议

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock (Claude Sonnet 4.5)
- openFDA API
- 本地文件系统缓存

作者：Agent Build Workflow
版本：1.0
日期：2025-12-28
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

# 配置 OpenTelemetry 端点
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# ==================== 创建 BedrockAgentCoreApp 实例 ====================
app = BedrockAgentCoreApp()

# Agent 配置路径
AGENT_CONFIG_PATH = "generated_agents_prompts/fda_data_query_agent/fda_data_query_agent_prompt"

# ==================== Agent 工厂方法 ====================
def create_fda_query_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
):
    """
    创建FDA数据查询智能体实例
    
    Args:
        env: 运行环境 (development/production/testing)
        version: Agent版本
        model_id: 模型ID
        
    Returns:
        Agent实例
    """
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id,
        "enable_logging": True
    }
    
    return create_agent_from_prompt_template(
        agent_name=AGENT_CONFIG_PATH,
        **agent_params
    )

# 创建全局 Agent 实例（用于 AgentCore 部署）
fda_query_agent = create_fda_query_agent()

# ==================== AgentCore 入口点（支持流式响应）====================
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

    示例:
        payload = {
            "prompt": "查询阿司匹林的不良反应",
            "user_id": "user123"
        }
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print(f"📋 Session ID: {session_id}")

    # 提取用户查询
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        error_msg = "Error: Missing 'prompt' in request. Please provide a query."
        print(f"❌ {error_msg}")
        yield error_msg
        return

    print(f"🔄 Processing query: {prompt}")

    try:
        # 使用流式响应
        stream = fda_query_agent.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 Streaming event: {event}")
            yield event

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        yield error_msg

# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='FDA数据查询智能体 - 支持本地测试和AgentCore部署',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 本地测试模式
  python fda_data_query_agent.py -i "查询阿司匹林的不良反应"
  
  # 交互式对话模式
  python fda_data_query_agent.py -it
  
  # 指定环境和版本
  python fda_data_query_agent.py -i "查询胰岛素泵召回信息" -e development -v 1.0
  
  # AgentCore 部署模式（Docker环境）
  DOCKER_CONTAINER=1 python fda_data_query_agent.py
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试查询输入（本地测试模式）'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=["development", "production", "testing"],
        help='Agent运行环境（默认: production）'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='Agent版本（默认: latest）'
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
        print("=" * 80)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 80)
        print(f"📡 端口: 8080")
        print(f"📍 端点: /invocations")
        print(f"🤖 Agent: FDA数据查询智能体")
        print("=" * 80)
        app.run()
        
    elif args.input:
        # 本地测试模式
        print("=" * 80)
        print("🧪 本地测试模式")
        print("=" * 80)
        
        # 创建指定环境的 Agent 实例
        test_agent = create_fda_query_agent(env=args.env, version=args.version)
        
        print(f"✅ Agent创建成功: {test_agent.name}")
        print(f"📝 查询: {args.input}")
        print("=" * 80)
        print("📋 响应:")
        print("-" * 80)
        
        try:
            result = test_agent(args.input)
            print(result)
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
        
        print("=" * 80)
        
    elif args.interactive:
        # 交互式对话模式
        print("=" * 80)
        print("💬 交互式对话模式")
        print("=" * 80)
        
        # 创建指定环境的 Agent 实例
        test_agent = create_fda_query_agent(env=args.env, version=args.version)
        
        print(f"✅ Agent创建成功: {test_agent.name}")
        print(f"🌍 环境: {args.env}")
        print(f"📦 版本: {args.version}")
        print("=" * 80)
        print("💡 提示:")
        print("  - 输入查询内容，按回车发送")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("  - 输入 'clear' 清空屏幕")
        print("=" * 80)
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                    
                if user_input.lower() == 'clear':
                    os.system('clear' if os.name != 'nt' else 'cls')
                    continue
                    
                if not user_input:
                    continue
                
                print("-" * 80)
                result = test_agent(user_input)
                print("-" * 80)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {str(e)}\n")
                
    else:
        # 默认启动服务器
        print("=" * 80)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 80)
        print(f"📡 端口: 8080")
        print(f"📍 端点: /invocations")
        print(f"🤖 Agent: FDA数据查询智能体")
        print("💡 提示: 使用 -i 参数进行本地测试，使用 -it 参数启动交互式对话")
        print("=" * 80)
        app.run()
