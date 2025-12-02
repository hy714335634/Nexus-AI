#!/usr/bin/env python3
"""
OpenFDA数据查询Agent

专业的OpenFDA数据查询专家，能够与OpenFDA API进行交互，
获取药物、医疗设备、食品等FDA公开数据，支持自然语言查询。

功能特性：
- 自然语言查询理解和参数提取
- 智能多端点路由（drug/device/food）
- API调用执行和错误处理
- 数据解析和格式化输出
- 指数退避重试机制
- 会话上下文管理

作者: Agent Build Workflow
版本: 1.0.0
日期: 2025-12-02
"""

import os
import json
import logging
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openfda_data_agent")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent配置参数
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
    "enable_logging": True
}

# 使用agent_factory创建Agent实例
openfda_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/openfda_data_agent/openfda_data_agent",
    **agent_params
)


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            - 其他业务参数

    Returns:
        str: 响应文本（不是Dict！）

    示例:
        输入: {"prompt": "查询阿司匹林的不良反应"}
        输出: "查询类型：药物\\n查询条件：阿司匹林，不良反应\\n结果数量：10条\\n..."
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")

    # 提取prompt字段
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        error_msg = "Error: Missing 'prompt' in request. Please provide a query."
        logger.error(error_msg)
        return error_msg

    logger.info(f"🔄 Processing prompt: {prompt}")

    try:
        # 调用Agent处理查询
        result = openfda_agent(prompt)

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

        logger.info(f"✅ Response generated successfully (length: {len(response_text)} chars)")
        logger.debug(f"Response preview: {response_text[:200]}...")

        return response_text

    except Exception as e:
        error_msg = f"Error: Agent execution failed - {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='OpenFDA数据查询Agent - 获取FDA药物、设备、食品等公开数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础查询
  python openfda_data_agent.py -i "查询阿司匹林的不良反应"
  
  # 设备查询
  python openfda_data_agent.py -i "查询心脏起搏器的召回信息"
  
  # 食品查询
  python openfda_data_agent.py -i "查询沙门氏菌相关的食品召回"
  
  # 复杂查询
  python openfda_data_agent.py -i "查询2023年的药物不良事件，按严重程度排序"
  
  # 启动HTTP服务器
  python openfda_data_agent.py
        """
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='查询输入（自然语言）'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )

    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📡 监听端点: POST /invocations")
        app.run()
    elif args.input:
        # 本地测试模式
        logger.info(f"✅ Agent创建成功: {openfda_agent.name}")
        logger.info(f"📝 查询输入: {args.input}")

        try:
            result = openfda_agent(args.input)
            print("\n" + "="*80)
            print("📋 查询结果:")
            print("="*80)
            print(result)
            print("="*80 + "\n")

        except Exception as e:
            logger.error(f"❌ 查询失败: {str(e)}", exc_info=True)
            print(f"\n错误: {str(e)}\n")

    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📡 监听端点: POST /invocations")
        logger.info("💡 提示: 使用 -i 参数进行本地测试，使用 --debug 启用调试模式")
        app.run()
