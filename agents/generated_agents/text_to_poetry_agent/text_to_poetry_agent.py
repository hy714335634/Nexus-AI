#!/usr/bin/env python3
"""
Text to Poetry Agent - 文字转诗歌创作专家

专业的诗歌创作专家，能够将普通文字转换为富有艺术美感的诗歌作品。
支持情感分析、风格智能选择（现代诗、古体诗、自由诗）和高质量诗歌生成。

功能特点：
- 深度文本理解和情感分析
- 智能诗歌风格选择
- 高质量诗歌内容生成
- 标准化格式输出
- 完善的错误处理

部署说明：
- 本地测试：python text_to_poetry_agent.py -i "测试文字"
- AgentCore部署：设置环境变量 DOCKER_CONTAINER=1 后运行

Author: Nexus-AI Platform
Date: 2025-12-02
Version: 1.0
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
logger = logging.getLogger("text_to_poetry_agent")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置
AGENT_NAME = "generated_agents_prompts/text_to_poetry_agent/text_to_poetry_agent"
MAX_INPUT_LENGTH = 2000  # 最大输入长度限制


def create_poetry_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
) -> Any:
    """
    创建诗歌创作Agent实例
    
    Args:
        env: 运行环境（development/production/testing）
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
    
    logger.info(f"创建 Poetry Agent，环境: {env}, 版本: {version}")
    
    try:
        agent = create_agent_from_prompt_template(
            agent_name=AGENT_NAME,
            **agent_params
        )
        logger.info(f"✅ Agent创建成功: {agent.name}")
        return agent
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


def validate_input(text: str) -> Dict[str, Any]:
    """
    验证输入文本的有效性
    
    Args:
        text: 输入文本
        
    Returns:
        验证结果字典
    """
    result = {
        "valid": False,
        "message": "",
        "processed_text": "",
        "warning": None
    }
    
    # 检查空值
    if not text or not text.strip():
        result["message"] = "请提供有效的文字内容，以便我为您创作诗歌。"
        return result
    
    # 去除首尾空白
    processed_text = text.strip()
    
    # 检查长度
    if len(processed_text) > MAX_INPUT_LENGTH:
        result["warning"] = (
            f"您提供的文字内容超过{MAX_INPUT_LENGTH}字，"
            "我将提取核心部分进行创作。建议简化内容以获得更精准的诗歌。"
        )
        processed_text = processed_text[:MAX_INPUT_LENGTH]
        logger.warning(f"输入超长，已截取前{MAX_INPUT_LENGTH}字")
    
    # 验证通过
    result["valid"] = True
    result["message"] = "验证通过"
    result["processed_text"] = processed_text
    
    return result


def extract_response_text(result: Any) -> str:
    """
    从Agent响应中提取文本内容
    
    Args:
        result: Agent响应对象
        
    Returns:
        提取的文本内容
    """
    try:
        # 尝试多种方式提取内容
        if hasattr(result, 'message') and result.message:
            content = result.message.get('content', [])
            if content and isinstance(content, list) and len(content) > 0:
                return content[0].get('text', str(result))
        
        if hasattr(result, 'content') and result.content:
            return result.content
        
        if isinstance(result, str):
            return result
        
        return str(result)
    
    except Exception as e:
        logger.error(f"提取响应内容失败: {str(e)}")
        return str(result)


# 创建全局Agent实例
try:
    poetry_agent = create_poetry_agent()
except Exception as e:
    logger.error(f"初始化Agent失败: {str(e)}")
    poetry_agent = None


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必需）
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            
    Returns:
        str: 响应文本（诗歌内容或错误信息）
    """
    logger.info(f"📥 接收到请求: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取输入内容
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        error_msg = "Error: 请求中缺少 'prompt' 字段，无法处理"
        logger.error(error_msg)
        return error_msg
    
    logger.info(f"🔄 处理输入: {prompt[:100]}...")
    
    try:
        # 验证输入
        validation_result = validate_input(prompt)
        
        if not validation_result["valid"]:
            logger.warning(f"输入验证失败: {validation_result['message']}")
            return validation_result["message"]
        
        processed_text = validation_result["processed_text"]
        warning = validation_result.get("warning")
        
        # 检查Agent是否初始化成功
        if poetry_agent is None:
            error_msg = "Error: Agent未能正确初始化，请检查配置"
            logger.error(error_msg)
            return error_msg
        
        # 调用Agent生成诗歌
        logger.info("🎨 开始生成诗歌...")
        result = poetry_agent(processed_text)
        
        # 提取响应内容
        response_text = extract_response_text(result)
        
        # 如果有警告信息，添加到响应前
        if warning:
            response_text = f"⚠️ {warning}\n\n{response_text}"
        
        logger.info(f"✅ 诗歌生成成功，长度: {len(response_text)} 字符")
        logger.info(f"📤 响应预览: {response_text[:200]}...")
        
        return response_text
    
    except Exception as e:
        error_msg = f"Error: 诗歌生成失败 - {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return error_msg


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Text to Poetry Agent - 文字转诗歌创作专家',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  本地测试:
    python text_to_poetry_agent.py -i "今天天气真好，阳光明媚"
    python text_to_poetry_agent.py -i "思念远方的朋友" -e development
  
  启动服务器:
    python text_to_poetry_agent.py
    DOCKER_CONTAINER=1 python text_to_poetry_agent.py
        """
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入文字内容'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=["development", "production", "testing"],
        help='指定Agent运行环境（默认: production）'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本（默认: latest）'
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
        print("=" * 60)
        print("Text to Poetry Agent - 本地测试模式")
        print("=" * 60)
        
        # 创建测试用Agent
        test_agent = create_poetry_agent(env=args.env, version=args.version)
        
        print(f"\n📝 输入文字:\n{args.input}\n")
        print("🎨 正在生成诗歌...\n")
        
        try:
            # 验证输入
            validation_result = validate_input(args.input)
            
            if not validation_result["valid"]:
                print(f"❌ 输入验证失败: {validation_result['message']}")
            else:
                processed_text = validation_result["processed_text"]
                warning = validation_result.get("warning")
                
                if warning:
                    print(f"⚠️  {warning}\n")
                
                # 生成诗歌
                result = test_agent(processed_text)
                response_text = extract_response_text(result)
                
                print("=" * 60)
                print("📋 生成的诗歌:")
                print("=" * 60)
                print(response_text)
                print("=" * 60)
        
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
            logger.error("测试失败", exc_info=True)
    
    else:
        # 默认启动服务器
        logger.info("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        logger.info("💡 提示: 使用 -i 参数进行本地测试")
        app.run()
