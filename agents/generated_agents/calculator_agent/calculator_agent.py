#!/usr/bin/env python3
"""
智能计算器Agent

专业的智能计算器专家，能够理解自然语言数学问题并进行准确计算。
支持基本四则运算、运算优先级、幂运算、开方、百分比计算等功能。
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
agent_config_path = "generated_agents_prompts/calculator_agent/calculator_agent"

# 定义 agent 创建的通用方法
def create_calculator_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建智能计算器Agent实例
    
    Args:
        env: 运行环境（production/development/testing）
        version: Agent版本
        model_id: 使用的模型ID
        
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
        agent_name=agent_config_path, **agent_params
    )

# 使用agent_factory创建agent
calculator_agent = create_calculator_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户的数学问题（如："12乘以12等于多少"）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）

    Returns:
        str: 格式化的计算结果或错误信息
    """
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")

    # 提取用户输入的数学问题
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        return "Error: Missing 'prompt' in request. Please provide a math problem to calculate."

    print(f"🔄 Processing math problem: {prompt}")

    try:
        # 调用智能计算器Agent处理数学问题
        result = calculator_agent(prompt)

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

        print(f"✅ Calculation result: {response_text[:200]}...")
        return response_text

    except Exception as e:
        error_message = f"Error: Failed to calculate. {str(e)}"
        print(f"❌ {error_message}")
        return error_message


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='智能计算器Agent - 支持自然语言数学问题计算',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python calculator_agent.py -i "12乘以12等于多少"
  python calculator_agent.py -i "2加3乘以4"
  python calculator_agent.py -i "9的平方根"
  python calculator_agent.py -i "20的50%"
        """
    )
    parser.add_argument('-i', '--input', type=str, default=None, 
                       help='数学问题（如：12乘以12等于多少）')
    parser.add_argument('-e', '--env', type=str, default="production", 
                       help='指定Agent运行环境（production/development/testing）')
    parser.add_argument('-v', '--version', type=str, default="latest", 
                       help='指定Agent版本')
    parser.add_argument('-m', '--model', type=str, default="default", 
                       help='指定使用的模型ID')
    args = parser.parse_args()

    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📊 智能计算器Agent已就绪，等待计算请求...")
        app.run()
    elif args.input:
        # 本地测试模式
        print("=" * 60)
        print("🧮 智能计算器Agent - 本地测试模式")
        print("=" * 60)
        
        # 创建Agent实例
        calculator_agent = create_calculator_agent(
            env=args.env, 
            version=args.version,
            model_id=args.model
        )
        print(f"✅ Agent 创建成功: {calculator_agent.name}")
        print(f"📝 数学问题: {args.input}")
        print("-" * 60)
        
        try:
            # 执行计算
            result = calculator_agent(args.input)
            print(f"📋 计算结果:")
            print(result)
        except Exception as e:
            print(f"❌ 计算失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("=" * 60)
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print("📊 智能计算器Agent已就绪，等待计算请求...")
        print("\n💡 提示: 使用 -i 参数进行本地测试")
        print("   例如: python calculator_agent.py -i \"12乘以12等于多少\"")
        app.run()
