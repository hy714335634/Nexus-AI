#!/usr/bin/env python3
"""
药物反馈收集Agent

专业的药物反馈收集与分析专家，能够接收药物名称输入，从互联网多个来源收集、分析和总结
关于该药物的用户反馈信息，生成全面的分析报告。

功能特性：
- 药物名称输入处理和验证
- 多源网络信息检索（搜索引擎、医疗论坛、社交媒体）
- 反馈信息提取和结构化
- 情感分析和主题分类
- 数据去重和质量过滤
- 反馈信息聚合和统计分析
- 生成可读性强的总结报告

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock (Claude Sonnet 4.5)
- DuckDuckGo搜索引擎
- BeautifulSoup4 (HTML解析)

作者：Nexus-AI Agent Code Developer
创建时间：2025-11-29
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
logger = logging.getLogger("drug_feedback_collector")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
AGENT_CONFIG_PATH = "generated_agents_prompts/drug_feedback_collector/drug_feedback_collector"

# Agent 参数配置
DEFAULT_AGENT_PARAMS = {
    "env": "production",
    "version": "latest",
    "model_id": "default",
    "enable_logging": True
}


def create_drug_feedback_collector_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
) -> Any:
    """
    创建药物反馈收集Agent实例
    
    Args:
        env: 运行环境（production/development/testing）
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
    
    try:
        agent = create_agent_from_prompt_template(
            agent_name=AGENT_CONFIG_PATH,
            **agent_params
        )
        logger.info(f"✅ Drug Feedback Collector Agent 创建成功: {agent.name}")
        return agent
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


# 创建默认Agent实例
drug_feedback_collector = create_drug_feedback_collector_agent(**DEFAULT_AGENT_PARAMS)


def process_drug_feedback_request(drug_name: str, **kwargs) -> Dict[str, Any]:
    """
    处理药物反馈收集请求
    
    Args:
        drug_name: 药物名称
        **kwargs: 其他可选参数（如search_depth、language_preference等）
    
    Returns:
        Dict: 包含分析结果和状态信息的字典
    """
    try:
        # 验证输入
        if not drug_name or not drug_name.strip():
            return {
                "success": False,
                "error": "药物名称不能为空",
                "error_code": "INVALID_INPUT"
            }
        
        # 构建请求提示
        prompt = f"请收集和分析关于药物「{drug_name}」的网络反馈信息。"
        
        # 添加可选参数
        if kwargs.get("search_depth"):
            prompt += f"\n搜索深度：{kwargs['search_depth']}"
        if kwargs.get("language_preference"):
            prompt += f"\n语言偏好：{kwargs['language_preference']}"
        
        logger.info(f"🔄 开始处理药物反馈收集请求: {drug_name}")
        
        # 调用Agent
        result = drug_feedback_collector(prompt)
        
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
        
        logger.info(f"✅ 药物反馈收集完成: {drug_name}")
        
        return {
            "success": True,
            "drug_name": drug_name,
            "response": response_text,
            "request_params": kwargs
        }
        
    except Exception as e:
        logger.error(f"❌ 处理请求失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_code": "PROCESSING_ERROR"
        }


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必需）
            - drug_name: 药物名称（可选，从prompt中提取）
            - search_depth: 搜索深度（可选）
            - language_preference: 语言偏好（可选）
    
    Returns:
        str: 响应文本
    """
    logger.info(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取prompt
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        return "Error: Missing 'prompt' in request"
    
    logger.info(f"🔄 Processing prompt: {prompt}")
    
    try:
        # 调用Agent处理请求
        result = drug_feedback_collector(prompt)
        
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
        return response_text
        
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        return f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='药物反馈收集Agent - 收集和分析药物的网络反馈信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 基本使用
  python drug_feedback_collector.py -i "请收集阿司匹林的反馈信息"
  
  # 指定药物名称
  python drug_feedback_collector.py -d "布洛芬"
  
  # 指定搜索深度
  python drug_feedback_collector.py -d "阿司匹林" --depth comprehensive
  
  # 指定语言偏好
  python drug_feedback_collector.py -d "aspirin" --language en
  
  # 启动AgentCore服务器
  python drug_feedback_collector.py
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入内容（完整的prompt）'
    )
    parser.add_argument(
        '-d', '--drug',
        type=str,
        default=None,
        help='药物名称'
    )
    parser.add_argument(
        '--depth',
        type=str,
        choices=['basic', 'standard', 'comprehensive'],
        default='standard',
        help='搜索深度（basic: 基础, standard: 标准, comprehensive: 全面）'
    )
    parser.add_argument(
        '--language',
        type=str,
        choices=['zh', 'en', 'both'],
        default='both',
        help='语言偏好（zh: 中文, en: 英文, both: 中英文）'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        help='运行环境（production/development/testing）'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='Agent版本'
    )
    
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    elif args.input or args.drug:
        # 本地测试模式
        try:
            # 创建Agent实例（如果需要不同配置）
            if args.env != "production" or args.version != "latest":
                test_agent = create_drug_feedback_collector_agent(
                    env=args.env,
                    version=args.version
                )
            else:
                test_agent = drug_feedback_collector
            
            # 构建测试请求
            if args.input:
                test_prompt = args.input
            elif args.drug:
                test_prompt = f"请收集和分析关于药物「{args.drug}」的网络反馈信息。"
                if args.depth != "standard":
                    test_prompt += f"\n搜索深度：{args.depth}"
                if args.language != "both":
                    test_prompt += f"\n语言偏好：{args.language}"
            else:
                test_prompt = "请收集阿司匹林的反馈信息"
            
            logger.info(f"📝 测试输入: {test_prompt}")
            
            # 执行测试
            result = test_agent(test_prompt)
            
            # 输出结果
            logger.info(f"📋 响应结果:")
            print("\n" + "="*80)
            print(result)
            print("="*80 + "\n")
            
        except Exception as e:
            logger.error(f"❌ 测试执行失败: {str(e)}")
            raise
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
