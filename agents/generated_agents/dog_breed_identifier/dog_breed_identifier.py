#!/usr/bin/env python3
"""
犬种识别Agent

根据用户输入的小狗特征描述，识别犬种并返回详细的生活习惯信息。
支持特征提取、模糊匹配、多选项推荐和结构化JSON输出。

部署要求：
- 支持本地测试模式（-i参数）
- 支持AgentCore部署模式（HTTP服务器）
- 使用BedrockAgentCoreApp框架
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
logger = logging.getLogger("dog_breed_identifier")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
    "enable_logging": True
}

# 使用 agent_factory 创建 agent
logger.info("正在初始化犬种识别Agent...")
dog_breed_identifier = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/dog_breed_identifier/dog_breed_identifier_prompt",
    **agent_params
)
logger.info(f"✅ Agent创建成功: {dog_breed_identifier.name}")

# ==================== AgentCore 入口点（必须包含）====================
# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()


@app.entrypoint
async def handler(payload: Dict[str, Any]):
    """
    AgentCore 标准入口点（支持流式响应）

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必填）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            - media: 媒体文件列表（可选）

    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")

    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        error_msg = "Error: Missing 'prompt' in request"
        logger.error(error_msg)
        yield error_msg
        return

    logger.info(f"🔄 Processing prompt: {prompt}")

    try:
        # 使用流式响应
        stream = dog_breed_identifier.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            logger.debug(f"📤 Streaming event: {event}")
            yield event

        logger.info("✅ Response streaming completed")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"❌ Agent调用失败: {error_msg}", exc_info=True)
        yield error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='犬种识别Agent - 根据特征描述识别犬种并提供生活习惯信息'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='小狗特征描述（例如："中型犬，金色长毛，垂耳，性格温顺"）'
    )
    args = parser.parse_args()

    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    elif args.input:
        # 本地测试模式
        print(f"✅ Agent创建成功: {dog_breed_identifier.name}")
        print(f"📝 输入: {args.input}")
        print("=" * 80)

        try:
            result = dog_breed_identifier(args.input)

            # 提取响应内容
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

            print(f"📋 响应:\n{response_text}")
            print("=" * 80)

            # 尝试解析JSON格式输出
            try:
                json_result = json.loads(response_text)
                print("\n📊 结构化输出:")
                print(json.dumps(json_result, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                logger.debug("响应不是JSON格式，跳过结构化输出")

        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            logger.error(f"本地测试失败: {str(e)}", exc_info=True)
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("💡 提示: 使用 -i 参数进行本地测试")
        logger.info("   示例: python dog_breed_identifier.py -i '中型犬，金色长毛，垂耳，性格温顺'")
        app.run()
