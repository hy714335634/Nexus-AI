#!/usr/bin/env python3
"""
智能电商价格比较Agent

专业的电商价格比较专家，能够根据用户输入的商品名称，自动搜索多个主流电商平台
（淘宝、京东、拼多多）的价格信息，进行智能对比分析，帮助用户找到最优惠的购买选择。

功能特点：
- 多平台并发查询（淘宝、京东、拼多多）
- 智能商品匹配和过滤
- 价格对比分析和统计
- 结构化Markdown格式报告
- 5分钟短期缓存优化
- 完善的错误处理机制

技术栈：
- Strands SDK Agent框架
- AWS Bedrock Claude Sonnet 4.5
- BedrockAgentCore部署框架
- Python asyncio并发处理
"""

import os
import json
import asyncio
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# ==================== 环境配置 ====================
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
AGENT_CONFIG_PATH = "generated_agents_prompts/ecommerce_price_comparison_agent/ecommerce_price_comparison_agent"

# 缓存配置
CACHE_DIR = Path(".cache/ecommerce_price_comparison_agent")
CACHE_TTL = 300  # 5分钟缓存有效期（秒）

# 确保缓存目录存在
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== Agent创建函数 ====================
def create_ecommerce_price_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
):
    """
    创建电商价格比较Agent实例
    
    Args:
        env: 运行环境（production/development/testing）
        version: Agent版本
        model_id: 模型ID（默认使用Claude Sonnet 4.5）
    
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
        agent_name=AGENT_CONFIG_PATH,
        **agent_params
    )


# 创建默认Agent实例
price_comparison_agent = create_ecommerce_price_agent()


# ==================== 缓存管理函数 ====================
def get_cache_key(query: str) -> str:
    """
    生成查询的缓存键
    
    Args:
        query: 商品查询关键词
    
    Returns:
        缓存键（MD5哈希）
    """
    return hashlib.md5(query.encode('utf-8')).hexdigest()


def check_cache(query: str) -> Optional[str]:
    """
    检查缓存是否存在且有效
    
    Args:
        query: 商品查询关键词
    
    Returns:
        缓存的结果字符串，如果缓存不存在或已过期则返回None
    """
    try:
        cache_key = get_cache_key(query)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            print(f"📦 缓存未命中: {query}")
            return None
        
        # 读取缓存文件
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期
        cache_time = cache_data.get('timestamp', 0)
        if time.time() - cache_time > CACHE_TTL:
            print(f"⏰ 缓存已过期: {query}")
            cache_file.unlink()  # 删除过期缓存
            return None
        
        print(f"✅ 缓存命中: {query} (缓存于 {int((time.time() - cache_time) / 60)} 分钟前)")
        return cache_data.get('result')
        
    except Exception as e:
        print(f"⚠️ 缓存读取失败: {str(e)}")
        return None


def update_cache(query: str, result: str) -> bool:
    """
    更新缓存
    
    Args:
        query: 商品查询关键词
        result: 查询结果
    
    Returns:
        是否成功更新缓存
    """
    try:
        cache_key = get_cache_key(query)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        cache_data = {
            'query': query,
            'result': result,
            'timestamp': time.time()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 缓存已更新: {query}")
        return True
        
    except Exception as e:
        print(f"⚠️ 缓存更新失败: {str(e)}")
        return False


# ==================== 输入验证函数 ====================
def validate_input(prompt: str) -> Tuple[bool, str]:
    """
    验证用户输入
    
    Args:
        prompt: 用户输入的商品名称
    
    Returns:
        (是否有效, 错误信息或规范化后的输入)
    """
    if not prompt or not prompt.strip():
        return False, "Error: 请输入要查询的商品名称"
    
    # 规范化输入
    normalized = prompt.strip()
    
    # 检查长度
    if len(normalized) > 100:
        return False, "Error: 商品名称过长（超过100字符），请简化输入"
    
    return True, normalized


# ==================== AgentCore 入口点 ====================
@app.entrypoint
def handler(payload: Dict[str, Any]) -> str:
    """
    AgentCore 标准入口点
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（商品名称）
            - message: 备选消息字段
            - input: 备选输入字段
    
    Returns:
        str: 价格对比报告（Markdown格式）或错误信息
    
    工作流程：
        1. 接收并验证用户输入
        2. 检查缓存是否命中
        3. 如未命中，调用Agent进行多平台查询
        4. Agent内部会：
           - 并发查询淘宝、京东、拼多多
           - 解析HTML提取商品信息
           - 智能匹配和过滤相关商品
           - 标准化价格数据
           - 进行价格对比分析
           - 生成Markdown格式报告
        5. 更新缓存
        6. 返回结果
    """
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    # 验证输入
    is_valid, result = validate_input(prompt)
    if not is_valid:
        print(f"❌ 输入验证失败: {result}")
        return result
    
    query = result
    print(f"🔍 商品查询: {query}")
    
    # 检查缓存
    cached_result = check_cache(query)
    if cached_result:
        # 在缓存结果中添加缓存标识
        cache_notice = "\n\n> 💡 **提示**: 此结果来自缓存（5分钟内有效），如需最新数据请稍后重试。\n"
        return cached_result + cache_notice
    
    # 缓存未命中，调用Agent进行查询
    try:
        print(f"🔄 开始多平台查询...")
        result = price_comparison_agent(query)
        
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
        
        print(f"✅ 查询完成，响应长度: {len(response_text)} 字符")
        
        # 更新缓存
        update_cache(query, response_text)
        
        return response_text
        
    except Exception as e:
        error_msg = f"Error: 查询过程中发生错误 - {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


# ==================== 本地测试入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='智能电商价格比较Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 本地测试查询
  python ecommerce_price_comparison_agent.py -i "iPhone 15 Pro"
  
  # 指定环境和版本
  python ecommerce_price_comparison_agent.py -i "小米14" -e development -v latest
  
  # 启动HTTP服务器（AgentCore模式）
  DOCKER_CONTAINER=1 python ecommerce_price_comparison_agent.py
        """
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='测试输入的商品名称'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['production', 'development', 'testing'],
        help='指定Agent运行环境（默认: production）'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='指定Agent版本（默认: latest）'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='清除所有缓存'
    )
    
    args = parser.parse_args()
    
    # 清除缓存
    if args.clear_cache:
        print("🗑️ 清除缓存...")
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
        print("✅ 缓存已清除")
        exit(0)
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print(f"📍 缓存目录: {CACHE_DIR.absolute()}")
        print(f"⏰ 缓存有效期: {CACHE_TTL // 60} 分钟")
        app.run()
    elif args.input:
        # 本地测试模式
        print("=" * 80)
        print("🛒 智能电商价格比较Agent - 本地测试模式")
        print("=" * 80)
        
        # 创建Agent实例
        test_agent = create_ecommerce_price_agent(env=args.env, version=args.version)
        print(f"✅ Agent 创建成功: {test_agent.name}")
        print(f"🔧 运行环境: {args.env}")
        print(f"📦 版本: {args.version}")
        print(f"📍 缓存目录: {CACHE_DIR.absolute()}")
        print(f"⏰ 缓存有效期: {CACHE_TTL // 60} 分钟")
        print("-" * 80)
        
        # 验证输入
        is_valid, result = validate_input(args.input)
        if not is_valid:
            print(f"❌ {result}")
            exit(1)
        
        query = result
        print(f"🔍 商品查询: {query}")
        print("-" * 80)
        
        # 检查缓存
        cached_result = check_cache(query)
        if cached_result:
            print("\n" + "=" * 80)
            print("📋 查询结果（来自缓存）:")
            print("=" * 80)
            print(cached_result)
            print("\n> 💡 **提示**: 此结果来自缓存，如需最新数据请使用 --clear-cache 清除缓存后重试。")
        else:
            # 执行查询
            try:
                print("🔄 开始多平台查询（可能需要15秒左右）...\n")
                result = test_agent(query)
                
                print("\n" + "=" * 80)
                print("📋 查询结果:")
                print("=" * 80)
                print(result)
                
                # 更新缓存
                update_cache(query, str(result))
                
            except Exception as e:
                print(f"\n❌ 查询失败: {str(e)}")
                exit(1)
        
        print("\n" + "=" * 80)
        print("✅ 测试完成")
        print("=" * 80)
    else:
        # 默认启动服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        print(f"📍 缓存目录: {CACHE_DIR.absolute()}")
        print(f"⏰ 缓存有效期: {CACHE_TTL // 60} 分钟")
        print("\n💡 提示: 使用 -i 参数进行本地测试，例如:")
        print("  python ecommerce_price_comparison_agent.py -i \"iPhone 15 Pro\"")
        app.run()
