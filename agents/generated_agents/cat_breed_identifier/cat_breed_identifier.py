#!/usr/bin/env python3
"""
猫咪品种识别Agent

专业的猫咪品种识别与习性分析专家，能够根据用户描述的猫咪外观特征识别品种，
并提供该品种的生活习性、性格特点、饲养建议等详细信息。

功能特点：
- 自然语言理解：解析用户口语化的特征描述
- 品种识别：基于特征进行品种匹配，支持30+主流品种
- 置信度评估：评估识别结果的可靠性
- 交互式追问：当信息不足时主动询问关键特征
- 习性信息：提供性格、饲养、健康、饮食等详细信息

技术栈：
- Python 3.13+
- Strands SDK (Agent框架)
- AWS Bedrock (Claude Sonnet 4.5)
- BedrockAgentCoreApp (部署运行时)

作者: Nexus-AI Agent Build Workflow
版本: 1.0
日期: 2025-12-07
"""

import os
import json
import logging
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ==================== 环境配置 ====================
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cat_breed_identifier")

# ==================== Agent 初始化 ====================
# Agent 参数配置
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "enable_logging": True
}

# 使用 agent_factory 创建 Agent
try:
    cat_breed_identifier = create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/cat_breed_identifier/cat_breed_identifier",
        **agent_params
    )
    logger.info(f"✅ Agent 创建成功: {cat_breed_identifier.name}")
except Exception as e:
    logger.error(f"❌ Agent 创建失败: {str(e)}")
    raise RuntimeError(f"Agent 初始化失败: {str(e)}")

# 验证 Agent 是否正确初始化
if not cat_breed_identifier or not hasattr(cat_breed_identifier, 'name'):
    raise RuntimeError("Agent 初始化失败：Agent 对象无效")

# ==================== BedrockAgentCoreApp 配置 ====================
# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any]):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必需）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            - media: 媒体文件列表（可选，预留扩展）
    
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    
    Returns:
        str: 错误信息（如果发生错误）
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取用户输入（支持多种字段名）
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    # 输入验证
    if not prompt:
        error_msg = "Error: Missing 'prompt' in request. Please provide a valid cat description."
        logger.error(error_msg)
        yield error_msg
        return
    
    # 记录请求信息
    user_id = payload.get("user_id", "anonymous")
    session_id = payload.get("session_id", "default")
    logger.info(f"🔄 Processing request - User: {user_id}, Session: {session_id}")
    logger.info(f"📝 Prompt: {prompt}")
    
    try:
        # 使用流式响应
        logger.info("🚀 Starting stream_async...")
        stream = cat_breed_identifier.stream_async(prompt)
        
        # 逐步产生响应片段
        async for event in stream:
            # 记录流式事件（仅在调试模式下）
            if logger.level == logging.DEBUG:
                logger.debug(f"📤 Streaming event: {event}")
            
            # 产生流式响应片段
            yield event
        
        logger.info("✅ Stream completed successfully")
        
    except Exception as e:
        error_msg = f"Error: Agent execution failed - {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        yield error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='猫咪品种识别Agent - 根据特征描述识别品种并提供习性信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 本地测试模式
  python cat_breed_identifier.py -i "白色长毛猫，蓝色眼睛，扁平脸"
  
  # 启动 HTTP 服务器（AgentCore 部署模式）
  python cat_breed_identifier.py
  
  # Docker 容器中运行
  DOCKER_CONTAINER=1 python cat_breed_identifier.py
        """
    )
    parser.add_argument(
        '-i', '--input', 
        type=str, 
        default=None,
        help='测试输入：猫咪特征描述'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试日志'
    )
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📡 监听端点: POST /invocations")
        logger.info("💡 发送请求格式: {\"prompt\": \"猫咪特征描述\"}")
        app.run()
        
    elif args.input:
        # 本地测试模式
        logger.info(f"✅ Agent 创建成功: {cat_breed_identifier.name}")
        logger.info(f"📝 测试输入: {args.input}")
        
        try:
            # 同步调用（本地测试）
            result = cat_breed_identifier(args.input)
            
            # 处理响应
            if hasattr(result, 'content') and result.content:
                response = result.content
            elif isinstance(result, str):
                response = result
            elif hasattr(result, 'text'):
                response = result.text
            else:
                response = str(result)
            
            logger.info(f"📋 Agent 响应:\n{response}")
            
        except Exception as e:
            logger.error(f"❌ 测试失败: {str(e)}", exc_info=True)
            
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📡 监听端点: POST /invocations")
        logger.info("💡 提示: 使用 -i 参数进行本地测试")
        logger.info("💡 示例: python cat_breed_identifier.py -i '白色长毛猫'")
        app.run()
