#!/usr/bin/env python3
"""
体育赛事预测分析Agent

专业的体育赛事预测分析专家，能够根据用户输入的球队名称，
自动收集球队信息、历史战绩、球员状态等多维度数据，
综合分析后预测未来比赛的输赢可能性，并生成详细的预测报告。

支持功能：
- 球队名称识别与验证（支持模糊匹配）
- 多维度数据收集（球队信息、历史战绩、球员状态、未来赛程、历史交锋）
- 智能缓存管理（球队24h、战绩7d、球员12h）
- 多维度综合分析（实力对比、近期状态、主客场因素、球员影响、历史交锋）
- 输赢概率预测（基于权重评分模型）
- 结构化预测报告生成
- 支持足球和篮球两大主流体育项目

技术栈：
- Strands SDK - Agent框架
- AWS Bedrock - Claude Sonnet 4.5模型
- The Sports DB API - 体育数据主数据源
- BedrockAgentCoreApp - 支持AgentCore部署

作者：Nexus-AI Agent Code Developer
版本：1.0
日期：2025-12-02
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sports_match_prediction_agent")

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# ==================== Agent 配置 ====================
AGENT_NAME = "generated_agents_prompts/sports_match_prediction_agent/sports_match_prediction_agent"

# Agent 参数配置
AGENT_PARAMS = {
    "env": "production",
    "version": "latest",
    "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "enable_logging": True
}


def create_sports_prediction_agent(env: str = None, version: str = None, model_id: str = None):
    """
    创建体育赛事预测Agent实例
    
    Args:
        env: 运行环境（development/testing/production）
        version: Agent版本
        model_id: 模型ID
    
    Returns:
        Agent实例
    """
    params = AGENT_PARAMS.copy()
    if env:
        params["env"] = env
    if version:
        params["version"] = version
    if model_id:
        params["model_id"] = model_id
    
    logger.info(f"创建Agent，参数: {params}")
    
    try:
        agent = create_agent_from_prompt_template(
            agent_name=AGENT_NAME,
            **params
        )
        logger.info(f"✅ Agent创建成功: {agent.name}")
        return agent
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


# 创建默认Agent实例
sports_prediction_agent = create_sports_prediction_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（球队名称）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
    
    Returns:
        str: 预测报告的字符串表示（不是Dict！）
    
    示例payload:
        {
            "prompt": "帮我分析一下湖人队未来几场比赛",
            "user_id": "user123",
            "session_id": "session456"
        }
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        error_msg = "Error: Missing 'prompt' in request"
        logger.error(error_msg)
        return error_msg
    
    logger.info(f"🔄 Processing prompt: {prompt}")
    
    try:
        # 调用Agent进行分析
        result = sports_prediction_agent(prompt)
        
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
        
        logger.info(f"✅ Response generated: {len(response_text)} characters")
        logger.debug(f"Response preview: {response_text[:200]}...")
        
        return response_text
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.error(f"❌ Processing error: {error_msg}")
        return error_msg


# 为 AgentCore 提供别名入口点
invoke = handler
main = handler


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='体育赛事预测分析Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 分析单个球队
  python sports_match_prediction_agent.py -i "帮我分析一下湖人队"
  
  # 分析特定比赛
  python sports_match_prediction_agent.py -i "湖人队 vs 勇士队，谁会赢？"
  
  # 分析足球队
  python sports_match_prediction_agent.py -i "曼联未来几场比赛怎么样"
  
  # 指定环境和版本
  python sports_match_prediction_agent.py -i "分析巴萨" -e development -v latest
  
  # 启动AgentCore HTTP服务器
  python sports_match_prediction_agent.py
        """
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入内容（球队名称或分析需求）'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=["development", "testing", "production"],
        help='指定Agent运行环境'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本'
    )
    parser.add_argument(
        '-m', '--model',
        type=str,
        default=None,
        help='指定模型ID'
    )
    parser.add_argument(
        '-d', '--debug',
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
        app.run()
    elif args.input:
        # 本地测试模式
        logger.info("=" * 60)
        logger.info("体育赛事预测分析Agent - 本地测试模式")
        logger.info("=" * 60)
        
        # 创建Agent实例
        agent = create_sports_prediction_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        # 执行分析
        logger.info(f"\n📝 输入: {args.input}")
        logger.info("-" * 60)
        
        try:
            result = agent(args.input)
            
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
            
            logger.info(f"\n📋 响应:\n{response_text}")
            logger.info("-" * 60)
            logger.info("✅ 分析完成")
            
        except Exception as e:
            logger.error(f"\n❌ 错误: {str(e)}")
            if args.debug:
                import traceback
                logger.error(traceback.format_exc())
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("使用 -h 查看命令行参数帮助")
        app.run()
