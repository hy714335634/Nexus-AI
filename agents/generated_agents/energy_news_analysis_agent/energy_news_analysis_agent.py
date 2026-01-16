#!/usr/bin/env python3
"""
能源行业新闻采集与分析Agent

专业的能源行业新闻采集与分析专家，能够从多个权威数据源自动采集能源行业政策、新闻和技术文档，
进行智能分类、摘要总结，并生成HTML报告上传至S3。

功能特性：
- 多数据源并发采集：北极星能源网、国家能源局、国家发改委、省级能源局
- 动态数据源发现：通过搜索引擎自动发现省级能源局官网
- 智能内容分类：政策类、案例类、新能源行业类、能源科技类
- 深度摘要生成：单篇200-300字摘要，全局500-800字总结
- HTML报告生成：基于Jinja2模板的结构化报告
- S3归档上传：按年/月/日目录结构组织
- 流式进度反馈：实时反馈处理进度

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock Claude Sonnet 4.5
- Playwright (网页爬取)
- boto3 (S3上传)
- Jinja2 (报告生成)
"""

import os
import json
from typing import Dict, Any
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# 初始化配置加载器
loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = loader.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
agent_config_path = "generated_agents_prompts/energy_news_analysis_agent/energy_news_analysis_agent"

# 创建 agent 的通用参数生成方法
def create_energy_news_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """
    创建能源新闻分析Agent实例
    
    Args:
        env: 运行环境 (development/production/testing)
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
    return create_agent_from_prompt_template(
        agent_name=agent_config_path,
        **agent_params
    )

# 创建默认 Agent 实例
energy_news_agent = create_energy_news_agent()


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）
    
    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。
    
    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息（必须）
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）
    
    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print(f"🔑 Session ID: {session_id}")
    
    # 提取用户输入
    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")
    
    if not prompt:
        yield "Error: Missing 'prompt' in request. Please provide a prompt with keywords for energy news collection."
        return
    
    print(f"🔄 Processing prompt: {prompt}")
    
    try:
        # 使用流式响应
        stream = energy_news_agent.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 Streaming event: {event}")
            yield event
    
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        yield f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='能源行业新闻采集与分析Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 启动 AgentCore HTTP 服务器（默认）
  python energy_news_analysis_agent.py
  
  # 本地测试模式
  python energy_news_analysis_agent.py -i "请采集关于光伏政策的能源行业新闻"
  
  # 交互式对话模式
  python energy_news_analysis_agent.py -it
  
  # 指定环境和版本
  python energy_news_analysis_agent.py -i "储能技术" -e development -v latest
        """
    )
    parser.add_argument('-i', '--input', type=str, default=None, 
                       help='测试输入内容（关键词或需求描述）')
    parser.add_argument('-e', '--env', type=str, default="production",
                       choices=['development', 'production', 'testing'],
                       help='指定Agent运行环境（默认：production）')
    parser.add_argument('-v', '--version', type=str, default="latest",
                       help='指定Agent版本（默认：latest）')
    parser.add_argument('-it', '--interactive', action='store_true',
                       help='启动交互式多轮对话模式')
    args = parser.parse_args()
    
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"
    
    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("=" * 60)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 60)
        print(f"📡 监听端口: 8080")
        print(f"🔗 端点: POST /invocations")
        print(f"🤖 Agent: {agent_config_path}")
        print("=" * 60)
        app.run()
    
    elif args.interactive:
        # 交互式对话模式
        energy_news_agent = create_energy_news_agent(env=args.env, version=args.version)
        print("=" * 60)
        print("💬 能源行业新闻采集与分析Agent - 交互式模式")
        print("=" * 60)
        print(f"✅ Agent 创建成功: {energy_news_agent.name}")
        print(f"🌍 运行环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print("=" * 60)
        print("💡 提示: 输入 'quit' 或 'exit' 退出")
        print("=" * 60)
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                
                if not user_input:
                    continue
                
                print()
                result = energy_news_agent(user_input)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")
                import traceback
                traceback.print_exc()
    
    elif args.input:
        # 本地测试模式
        energy_news_agent = create_energy_news_agent(env=args.env, version=args.version)
        print("=" * 60)
        print("🧪 能源行业新闻采集与分析Agent - 测试模式")
        print("=" * 60)
        print(f"✅ Agent 创建成功: {energy_news_agent.name}")
        print(f"🌍 运行环境: {args.env}")
        print(f"📌 版本: {args.version}")
        print("=" * 60)
        print(f"📝 测试输入: {args.input}")
        print("=" * 60)
        print()
        
        try:
            result = energy_news_agent(args.input)
            print()
            print("=" * 60)
            print("✅ 测试完成")
            print("=" * 60)
        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ 测试失败: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
    
    else:
        # 默认启动服务器
        print("=" * 60)
        print("🚀 启动 AgentCore HTTP 服务器")
        print("=" * 60)
        print(f"📡 监听端口: 8080")
        print(f"🔗 端点: POST /invocations")
        print(f"🤖 Agent: {agent_config_path}")
        print("=" * 60)
        print("💡 提示: 使用 -i 参数进行本地测试")
        print("💡 提示: 使用 -it 参数启动交互式模式")
        print("=" * 60)
        app.run()
