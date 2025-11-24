#!/usr/bin/env python3
"""
天气查询Agent

专业的天气查询专家，能够根据用户提供的城市名称查询并返回实时天气信息。
支持中英文城市名称、多种温度单位和数据格式化输出。

功能特性:
- 支持中英文城市名称输入
- 实时天气数据查询
- 多种输出格式（文本、HTML、JSON）
- 智能缓存机制
- 完善的错误处理

使用示例:
    python weather_query_agent.py -i "北京的天气怎么样？"
    python weather_query_agent.py -i "What's the weather in Shanghai?"
"""

import os
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


def create_weather_query_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
):
    """
    创建天气查询Agent实例
    
    Args:
        env: 运行环境 (development/production/testing)
        version: Agent版本
        model_id: 使用的模型ID
        
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
        agent_name="generated_agents_prompts/weather_query_agent/weather_query_agent",
        **agent_params
    )


# 创建默认Agent实例
weather_query_agent = create_weather_query_agent()


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='天气查询Agent - 根据城市名称查询实时天气信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查询北京天气
  python weather_query_agent.py -i "北京的天气怎么样？"
  
  # 查询上海天气（英文）
  python weather_query_agent.py -i "What's the weather in Shanghai?"
  
  # 使用开发环境
  python weather_query_agent.py -i "广州天气" -e development
  
  # 查看详细天气信息
  python weather_query_agent.py -i "查询深圳的详细天气信息"
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="北京的天气怎么样？",
        help='查询输入（城市名称或自然语言描述）'
    )
    
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=['development', 'production', 'testing'],
        help='运行环境 (默认: production)'
    )
    
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='Agent版本 (默认: latest)'
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        default="default",
        help='模型ID (默认: default)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # 创建Agent实例
    try:
        agent = create_weather_query_agent(
            env=args.env,
            version=args.version,
            model_id=args.model
        )
        
        print(f"✅ Weather Query Agent 创建成功: {agent.name}")
        print(f"🌍 运行环境: {args.env}")
        print(f"📦 版本: {args.version}")
        print(f"🔧 模型: {args.model}")
        print(f"\n{'='*60}\n")
        
        # 执行查询
        print(f"🎯 查询输入: {args.input}")
        print(f"\n{'='*60}\n")
        
        result = agent(args.input)
        
        print(f"📋 Agent 响应:\n")
        print(result)
        print(f"\n{'='*60}\n")
        
        print("✅ 查询完成")
        
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
