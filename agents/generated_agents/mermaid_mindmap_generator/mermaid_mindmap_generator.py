#!/usr/bin/env python3
"""
Mermaid思维导图生成Agent

专业的Mermaid思维导图生成专家，能够根据用户输入的文本内容或主题描述，
自动进行内容分析、结构识别和层级提取，生成符合Mermaid mindmap语法规范的思维导图代码，
支持流式输出和友好的用户交互体验。

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock (Claude Sonnet 4.5)
- BedrockAgentCoreApp (HTTP服务器 + 流式响应)

部署模式：
- 本地测试：支持-i参数直接测试，-it参数交互式对话
- AgentCore部署：Docker容器化部署到Amazon Bedrock AgentCore
"""

import os
import json
import logging
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mermaid_mindmap_generator")

# 初始化配置加载器
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置OpenTelemetry端点
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
AGENT_CONFIG_PATH = "generated_agents_prompts/mermaid_mindmap_generator/mermaid_mindmap_generator_prompt"


def create_mermaid_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建Mermaid思维导图生成Agent实例
    
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
    
    logger.info(f"创建Mermaid Agent - 环境: {env}, 版本: {version}, 模型: {model_id}")
    
    try:
        agent = create_agent_from_prompt_template(
            agent_name=AGENT_CONFIG_PATH,
            **agent_params
        )
        logger.info(f"✅ Agent创建成功: {agent.name}")
        return agent
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


def validate_input(prompt: str) -> tuple[bool, str]:
    """
    验证用户输入
    
    Args:
        prompt: 用户输入内容
        
    Returns:
        (是否有效, 错误消息)
    """
    if not prompt or not prompt.strip():
        return False, "Error: 请提供需要生成思维导图的内容"
    
    if len(prompt) > 2000:
        return False, "Error: 输入内容过长，请控制在2000字以内"
    
    return True, ""


# 创建默认Agent实例（生产环境）
mermaid_agent = create_mermaid_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必填）
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）
    
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    """
    session_id = context.session_id
    logger.info(f"📥 收到请求 - Session: {session_id}, Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    # 输入验证
    is_valid, error_msg = validate_input(prompt)
    if not is_valid:
        logger.warning(f"⚠️ 输入验证失败: {error_msg}")
        yield error_msg
        return
    
    logger.info(f"🔄 开始处理 - 输入长度: {len(prompt)}字")
    
    try:
        # 使用流式响应
        stream = mermaid_agent.stream_async(prompt)
        
        async for event in stream:
            # 每个 event 包含流式响应的片段（可能是dict或str）
            event_preview = str(event)[:50] if event else ""
            logger.debug(f"📤 流式输出片段: {event_preview}...")
            yield event
        
        logger.info("✅ 处理完成")
        
    except Exception as e:
        error_message = f"Error: 生成服务异常 - {str(e)}"
        logger.error(f"❌ 处理失败: {error_message}")
        yield error_message


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Mermaid思维导图生成Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 本地测试模式
  python mermaid_mindmap_generator.py -i "项目管理的核心要素"
  
  # 交互式对话模式
  python mermaid_mindmap_generator.py -it
  
  # 指定环境和版本
  python mermaid_mindmap_generator.py -i "敏捷开发" -e development -v latest
  
  # 启动AgentCore HTTP服务器
  python mermaid_mindmap_generator.py
        """
    )
    parser.add_argument('-i', '--input', type=str, default=None, help='测试输入内容')
    parser.add_argument('-e', '--env', type=str, default="production", 
                       choices=['development', 'production', 'testing'],
                       help='指定Agent运行环境')
    parser.add_argument('-v', '--version', type=str, default="latest", help='指定Agent版本')
    parser.add_argument('-it', '--interactive', action='store_true', help='启动交互式多轮对话模式')
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
        
    elif args.interactive:
        # 交互式对话模式
        agent = create_mermaid_agent(env=args.env, version=args.version)
        print(f"✅ Mermaid Agent 创建成功: {agent.name}")
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
                
                # 输入验证
                is_valid, error_msg = validate_input(user_input)
                if not is_valid:
                    print(f"⚠️ {error_msg}\n")
                    continue
                
                # 调用Agent
                try:
                    result = agent(user_input)
                    print(f"Agent: {result}\n")
                except Exception as e:
                    print(f"❌ 错误: {str(e)}\n")
                    
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")
                
    elif args.input:
        # 本地测试模式
        agent = create_mermaid_agent(env=args.env, version=args.version)
        print(f"✅ Mermaid Agent 创建成功: {agent.name}")
        
        # 输入验证
        is_valid, error_msg = validate_input(args.input)
        if not is_valid:
            print(f"⚠️ {error_msg}")
        else:
            print(f"📝 输入: {args.input}")
            try:
                result = agent(args.input)
                print(f"📋 响应:\n{result}")
            except Exception as e:
                print(f"❌ 错误: {str(e)}")
                
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("💡 提示: 使用 -i 参数进行本地测试，使用 -it 参数启动交互式对话")
        app.run()
