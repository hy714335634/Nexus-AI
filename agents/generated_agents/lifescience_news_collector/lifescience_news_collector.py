#!/usr/bin/env python3
"""
生命科学行业新闻自动采集Agent

专业的生命科学行业新闻自动采集与分析专家，能够从15+数据源自动采集新闻、
智能分类、生成摘要、创建HTML报告并上传到AWS S3。

功能特性：
- 多源数据采集（SerpAPI + 14个医疗资讯网站）
- AI驱动的智能分类（7大类别体系）
- 自动摘要生成（100-200字）
- HTML报告生成（基于Jinja2模板）
- AWS S3自动上传和Presign URL生成
- 深度遍历和并发采集
- 完善的错误处理和重试机制
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

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("lifescience_news_collector")

# ==================== 环境配置 ====================
loader = ConfigLoader()
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置OTEL端点
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# ==================== BedrockAgentCoreApp 实例 ====================
app = BedrockAgentCoreApp()

# ==================== Agent 配置 ====================
AGENT_CONFIG_PATH = "generated_agents_prompts/lifescience_news_collector/lifescience_news_collector"

def create_news_collector_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
):
    """
    创建生命科学新闻采集Agent实例
    
    Args:
        env: 运行环境（development/testing/production）
        version: Agent版本
        model_id: 使用的模型ID
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
    
    logger.info(f"创建Agent实例，参数: {agent_params}")
    
    agent = create_agent_from_prompt_template(
        agent_name=AGENT_CONFIG_PATH,
        **agent_params
    )
    
    logger.info(f"✅ Agent创建成功: {agent.name}")
    return agent

# 创建默认Agent实例
news_collector_agent = create_news_collector_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到Amazon Bedrock AgentCore时，AgentCore会调用此函数处理请求。
    
    Args:
        payload: AgentCore传入的请求体，包含:
            - prompt: 用户消息（必需）
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从runtimeSessionId header获取）
            
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
        
    Returns:
        str: 最终响应文本（非流式模式）
    """
    session_id = context.session_id
    logger.info(f"📥 收到请求 - Session: {session_id}")
    logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取prompt参数
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        error_msg = "Error: Missing 'prompt' in request. 请提供'prompt'参数。"
        logger.error(error_msg)
        yield error_msg
        return
    
    logger.info(f"🔄 开始处理任务: {prompt[:100]}...")
    
    try:
        # 使用流式响应
        stream = news_collector_agent.stream_async(prompt)
        
        async for event in stream:
            # 每个event包含流式响应的片段（可能是dict或str）
            event_preview = str(event)[:100] if event else ""
            logger.debug(f"📤 流式输出: {event_preview}...")
            yield event
            
    except Exception as e:
        error_msg = f"❌ 任务执行失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='生命科学新闻采集Agent - 自动采集、分类、摘要、报告生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 本地测试模式
  python lifescience_news_collector.py -i "请采集今天的生命科学行业新闻并生成报告"
  
  # 交互式对话模式
  python lifescience_news_collector.py -it
  
  # 指定环境和版本
  python lifescience_news_collector.py -i "采集新闻" -e production -v latest
  
  # Docker部署模式（自动启动HTTP服务器）
  DOCKER_CONTAINER=1 python lifescience_news_collector.py
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入内容（单次执行模式）'
    )
    
    parser.add_argument(
        '-it', '--interactive',
        action='store_true',
        help='启动交互式多轮对话模式'
    )
    
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['development', 'testing', 'production'],
        help='指定Agent运行环境（默认: production）'
    )
    
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本（默认: latest）'
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        default="default",
        help='指定使用的模型ID（默认: default）'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default="INFO",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='日志级别（默认: INFO）'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    logger.setLevel(getattr(logging, args.log_level))
    
    # 检查是否在Docker容器中运行（AgentCore部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # ==================== AgentCore 部署模式 ====================
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📍 服务端点: POST /invocations")
        logger.info("💡 请求格式: {\"prompt\": \"your_message\"}")
        app.run()
        
    elif args.interactive:
        # ==================== 交互式对话模式 ====================
        logger.info("="*60)
        logger.info("🤖 生命科学新闻采集Agent - 交互式模式")
        logger.info("="*60)
        
        # 创建Agent实例
        agent = create_news_collector_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        logger.info(f"📌 运行环境: {args.env}")
        logger.info(f"📌 Agent版本: {args.version}")
        logger.info("💬 进入交互式对话模式（输入 'quit' 或 'exit' 退出）")
        logger.info("💡 提示: 你可以输入如 '请采集今天的生命科学新闻并生成报告'")
        logger.info("-"*60)
        
        while True:
            try:
                user_input = input("\n你: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("👋 退出交互式对话")
                    break
                    
                if not user_input:
                    continue
                
                logger.info(f"🔄 处理中...")
                result = agent(user_input)
                logger.info("✅ 任务完成")
                
            except KeyboardInterrupt:
                logger.info("\n👋 退出交互式对话")
                break
            except Exception as e:
                logger.error(f"❌ 错误: {e}", exc_info=True)
                
    elif args.input:
        # ==================== 本地测试模式 ====================
        logger.info("="*60)
        logger.info("🧪 生命科学新闻采集Agent - 测试模式")
        logger.info("="*60)
        
        # 创建Agent实例
        agent = create_news_collector_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        logger.info(f"📌 运行环境: {args.env}")
        logger.info(f"📌 Agent版本: {args.version}")
        logger.info(f"📝 输入: {args.input}")
        logger.info("-"*60)
        
        try:
            logger.info("🔄 开始处理...")
            result = agent(args.input)
            logger.info("✅ 任务完成")
            logger.info("="*60)
            print(result.metrics.accumulated_usage)
            
        except Exception as e:
            logger.error(f"❌ 任务失败: {e}", exc_info=True)
            
    else:
        # ==================== 默认启动服务器 ====================
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("📍 服务端点: POST /invocations")
        logger.info("💡 请求格式: {\"prompt\": \"your_message\"}")
        logger.info("💡 提示: 使用 -i 参数进行本地测试，使用 -it 参数进入交互模式")
        logger.info("💡 示例: python lifescience_news_collector.py -i '请采集今天的生命科学新闻'")
        app.run()
