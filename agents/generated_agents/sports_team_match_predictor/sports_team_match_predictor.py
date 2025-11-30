#!/usr/bin/env python3
"""
体育比赛预测分析Agent

专业的体育比赛预测分析专家，能够收集球队信息、分析比赛数据并预测比赛结果。
支持足球和篮球等主流体育项目，提供数据驱动的比赛预测和详细分析报告。

功能特性：
- 球队信息收集：收集球队基本信息、近期战绩、球员状态等完整数据
- 比赛数据分析：分析球队近期表现、历史交锋、主客场优势等多维度数据
- 比赛结果预测：基于收集的数据预测球队未来比赛的胜负可能性
- 结构化报告生成：生成清晰、详细、有依据的分析报告

依赖项：
- strands-agents: Strands Agent框架
- nexus_utils: 本地工具包（Agent工厂和配置管理）
- generated_tools/sports_team_match_predictor/sports_data_tools.py: 体育数据工具集
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
logger = logging.getLogger("sports_team_match_predictor")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
AGENT_CONFIG_PATH = "generated_agents_prompts/sports_team_match_predictor/sports_team_match_predictor"


def create_sports_predictor_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
) -> Any:
    """
    创建体育比赛预测分析Agent
    
    Args:
        env: 运行环境 (production/development/testing)
        version: Agent版本
        model_id: 模型ID (default使用配置文件中的模型)
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


# 创建默认Agent实例
sports_predictor = create_sports_predictor_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（球队名称和分析需求）
            - sport_type: 体育项目类型（可选）
            - analysis_depth: 分析深度（可选）
            
    Returns:
        str: 响应文本（预测分析报告）
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        error_msg = "Error: Missing 'prompt' in request. Please provide a team name for analysis."
        logger.error(error_msg)
        return error_msg
    
    logger.info(f"🔄 Processing team analysis request: {prompt}")
    
    try:
        # 调用Agent进行分析
        result = sports_predictor(prompt)
        
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
        
        logger.info(f"✅ Analysis completed successfully")
        logger.debug(f"Response preview: {response_text[:200]}...")
        
        return response_text
        
    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return error_msg


# 为 AgentCore 提供别名入口点
invoke = handler
main = handler


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='体育比赛预测分析Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 分析单个球队
  python sports_team_match_predictor.py -i "Manchester United"
  
  # 指定体育项目
  python sports_team_match_predictor.py -i "Lakers" --sport basketball
  
  # 指定分析深度
  python sports_team_match_predictor.py -i "Barcelona" --depth advanced
  
  # 指定环境和版本
  python sports_team_match_predictor.py -i "Real Madrid" -e development -v 1.0
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='球队名称（必填）'
    )
    parser.add_argument(
        '--sport',
        type=str,
        choices=['auto', 'football', 'basketball'],
        default='auto',
        help='体育项目类型（auto/football/basketball）'
    )
    parser.add_argument(
        '--depth',
        type=str,
        choices=['basic', 'standard', 'advanced'],
        default='standard',
        help='分析深度（basic/standard/advanced）'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        choices=['production', 'development', 'testing'],
        default='production',
        help='运行环境'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default='latest',
        help='Agent版本'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试日志'
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
        logger.info("🏃 运行本地测试模式")
        
        # 根据参数创建Agent
        predictor = create_sports_predictor_agent(
            env=args.env,
            version=args.version,
            enable_logging=True
        )
        
        # 构建分析请求
        request = args.input
        if args.sport != 'auto':
            request += f" (体育项目: {args.sport})"
        if args.depth != 'standard':
            request += f" (分析深度: {args.depth})"
        
        logger.info(f"📝 分析请求: {request}")
        
        try:
            # 执行分析
            result = predictor(request)
            
            # 输出结果
            print("\n" + "="*80)
            print("📊 体育比赛预测分析报告")
            print("="*80)
            print(result)
            print("="*80 + "\n")
            
            logger.info("✅ 分析完成")
            
        except Exception as e:
            logger.error(f"❌ 分析失败: {str(e)}", exc_info=True)
            print(f"\n❌ 错误: {str(e)}\n")
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
