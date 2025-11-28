#!/usr/bin/env python3
"""
股票信息收集与评价Agent

专业的股票信息收集与评价系统，能够根据用户提供的股票名称或代码，
自动收集相关的股票信息（包括基本面数据、市场表现、新闻资讯等），
并基于收集到的信息给出综合评价和投资建议。

功能特性：
- 支持多市场股票查询（A股、港股、美股）
- 自动收集基本信息、实时行情、财务数据、新闻资讯
- 生成综合评价报告和投资建议
- 智能缓存管理减少API调用
- 完善的错误处理和降级策略

作者：Agent Build Workflow
版本：1.0.0
创建日期：2025-11-28
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
logger = logging.getLogger("stock_information_collector")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置参数
AGENT_CONFIG = {
    "agent_name": "generated_agents_prompts/stock_information_collector/stock_information_collector",
    "env": "production",
    "version": "latest",
    "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "enable_logging": True
}


def create_stock_collector_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
) -> Any:
    """
    创建股票信息收集Agent

    Args:
        env: 运行环境（production/development/testing）
        version: Agent版本
        model_id: 使用的模型ID

    Returns:
        创建的Agent实例
    """
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id,
        "enable_logging": True
    }

    logger.info(f"正在创建股票信息收集Agent，环境: {env}, 版本: {version}, 模型: {model_id}")

    try:
        agent = create_agent_from_prompt_template(
            agent_name=AGENT_CONFIG["agent_name"],
            **agent_params
        )
        logger.info(f"✅ Agent创建成功: {agent.name}")
        return agent
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


# 创建默认Agent实例
stock_collector = create_stock_collector_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（股票名称或代码）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）

    Returns:
        str: 响应文本（股票信息和评价报告）
    """
    logger.info(f"📥 接收到请求: {json.dumps(payload, ensure_ascii=False)}")

    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        error_msg = "错误：缺少必需的'prompt'参数"
        logger.error(error_msg)
        return f"Error: Missing 'prompt' in request"

    logger.info(f"🔄 处理股票查询: {prompt}")

    try:
        # 调用Agent进行股票信息收集和分析
        result = stock_collector(prompt)

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

        logger.info(f"✅ 股票分析完成，响应长度: {len(response_text)} 字符")
        logger.debug(f"响应预览: {response_text[:200]}...")

        return response_text

    except Exception as e:
        error_msg = f"股票信息收集过程中发生错误: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return f"Error: {error_msg}"


# 为 AgentCore 提供别名入口点
invoke = handler
main = handler


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='股票信息收集与评价Agent - 支持A股、港股、美股查询',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python stock_information_collector.py -i "AAPL"                    # 查询苹果公司
  python stock_information_collector.py -i "000001"                  # 查询A股平安银行
  python stock_information_collector.py -i "00700"                   # 查询港股腾讯
  python stock_information_collector.py -i "苹果"                    # 使用公司名称查询
  python stock_information_collector.py -e development -i "MSFT"     # 使用开发环境查询微软

支持的市场:
  - A股：上交所（600xxx）、深交所（000xxx、002xxx、300xxx）
  - 港股：港交所（5位数字代码，如00700）
  - 美股：纳斯达克、纽交所（字母代码，如AAPL、TSLA）

注意事项:
  - 首次查询需要下载数据，可能需要较长时间
  - 数据会被缓存以加快后续查询速度
  - 行情数据可能存在15分钟延迟
  - 系统提供的信息仅供参考，不构成投资建议
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='股票名称或代码（如：AAPL、000001、腾讯）'
    )

    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['production', 'development', 'testing'],
        help='运行环境（默认：production）'
    )

    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='Agent版本（默认：latest）'
    )

    parser.add_argument(
        '-m', '--model',
        type=str,
        default="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        help='使用的模型ID'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式（显示详细日志）'
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
        logger.info("=" * 80)
        logger.info("股票信息收集与评价Agent - 本地测试模式")
        logger.info("=" * 80)

        # 创建Agent实例
        agent = create_stock_collector_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )

        logger.info(f"📝 查询股票: {args.input}")
        logger.info(f"🌍 运行环境: {args.env}")
        logger.info(f"📊 使用模型: {args.model}")
        logger.info("-" * 80)

        try:
            # 执行查询
            result = agent(args.input)

            # 显示结果
            print("\n" + "=" * 80)
            print("📋 股票分析结果:")
            print("=" * 80)
            print(result)
            print("=" * 80 + "\n")

            logger.info("✅ 查询完成")

        except Exception as e:
            logger.error(f"❌ 查询失败: {str(e)}", exc_info=True)
            print(f"\n❌ 错误: {str(e)}\n")
            exit(1)
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("💡 提示: 使用 -i 参数进行本地测试，使用 --help 查看详细帮助")
        app.run()
