#!/usr/bin/env python3
"""
AWS Pricing Agent

专业的AWS产品报价智能体，能够根据自然语言描述的资源需求，分析并推荐合理的AWS服务和配置，
提供实时报价并生成专业的报价方案。支持EC2、EBS、S3、网络流量、ELB、RDS、ElastiCache、
Opensearch等多种AWS产品的价格查询。

功能:
1. 解析用户的自然语言需求描述
2. 推荐符合需求的AWS服务配置，优先推荐最新一代实例
3. 通过AWS价格API获取实时价格信息，支持所有AWS区域（包括中国区域）
4. 生成专业、清晰的报价方案，包含配置详情、价格明细和推荐理由
5. 处理用户的澄清问题和补充信息

工具:
- use_aws: 调用AWS服务API
- get_aws_pricing: 获取AWS服务的价格信息
- get_ec2_instance_pricing: 获取EC2实例价格
- get_ebs_pricing: 获取EBS存储价格
- get_s3_pricing: 获取S3存储价格
- get_network_pricing: 获取网络流量价格
- get_elb_pricing: 获取负载均衡器价格
- get_rds_pricing: 获取RDS数据库价格
- get_elasticache_pricing: 获取ElastiCache价格
- get_opensearch_pricing: 获取OpenSearch服务价格
- get_available_instance_types: 获取可用的实例类型
- recommend_instance_types: 根据需求推荐实例类型
"""

import os
import json
import argparse
from typing import Dict, Any, Optional, List
from nexus_utils.agent_factory import create_agent_from_prompt_template
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()

# 配置遥测
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
# 优先使用环境变量，其次使用配置文件，最后使用默认值
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()

# Agent 配置路径
agent_config_path = "generated_agents_prompts/aws_pricing_agent/aws_pricing_agent"

# 创建 agent 的通用参数生成方法
def create_aws_pricing_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
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

# 使用 agent_factory 创建 agent
aws_pricing_agent = create_aws_pricing_agent()

class AWSPricingAgentCLI:
    """AWS Pricing Agent 命令行接口类"""
    
    def __init__(self, agent):
        """初始化AWS Pricing Agent CLI

        Args:
            agent: 已初始化的AWS Pricing Agent
        """
        self.agent = agent
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器

        Returns:
            argparse.ArgumentParser: 参数解析器对象
        """
        parser = argparse.ArgumentParser(
            description='AWS Pricing Agent - 根据自然语言需求提供AWS服务配置和价格报价'
        )
        parser.add_argument(
            '-r', '--requirement', 
            type=str,
            help='自然语言描述的资源需求'
        )
        parser.add_argument(
            '-f', '--file', 
            type=str,
            help='包含需求描述的文件路径'
        )
        parser.add_argument(
            '--region', 
            type=str,
            default='us-east-1',
            help='AWS区域代码，默认为us-east-1'
        )
        parser.add_argument(
            '-it', '--interactive', 
            action='store_true',
            help='启动交互式多轮对话模式'
        )
        return parser
    
    def run(self) -> None:
        """运行AWS Pricing Agent CLI"""
        args = self.parser.parse_args()
        
        # 获取需求描述
        requirement = self._get_requirement(args)
        if not requirement:
            print("❌ 错误: 请提供需求描述 (使用 -r 或 --file 参数)")
            return
        
        # 添加区域信息
        if args.region:
            requirement += f"\n区域: {args.region}"
        
        print(f"🔍 正在分析需求并生成AWS服务报价...\n")
        
        try:
            if args.interactive:
                self._run_interactive_mode(requirement)
            else:
                response = self.agent(requirement)
                # print(f"📋 AWS服务报价方案:\n{response}")
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")
    
    def _get_requirement(self, args) -> Optional[str]:
        """从命令行参数或文件中获取需求描述

        Args:
            args: 解析后的命令行参数

        Returns:
            Optional[str]: 需求描述文本，如果未提供则返回None
        """
        if args.requirement:
            return args.requirement
        elif args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"❌ 读取文件失败: {str(e)}")
                return None
        elif args.interactive:
            return input("请描述您的AWS资源需求: ")
        else:
            return None
    
    def _run_interactive_mode(self, initial_requirement: str) -> None:
        """运行交互模式，支持多轮对话

        Args:
            initial_requirement (str): 初始需求描述
        """
        print("💬 进入交互式对话模式（输入 'quit' 或 'exit' 退出）\n")
        
        # 首次响应
        if initial_requirement:
            self.agent(initial_requirement)
            print()
        
        # 继续对话
        while True:
            try:
                user_input = input("You: ")
                user_input = user_input.encode('utf-8', errors='ignore').decode('utf-8').strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 退出交互式对话")
                    break
                if not user_input:
                    continue
                
                self.agent(user_input)
                print()
            except KeyboardInterrupt:
                print("\n👋 退出交互式对话")
                break
            except Exception as e:
                print(f"❌ 错误: {e}\n")
    
    def _build_conversation_prompt(self, history: List[Dict[str, str]]) -> str:
        """构建包含对话历史的完整提示

        Args:
            history (List[Dict[str, str]]): 对话历史记录

        Returns:
            str: 包含对话历史的完整提示
        """
        prompt = ""
        for message in history:
            if message["role"] == "user":
                prompt += f"用户: {message['content']}\n\n"
            else:
                prompt += f"AWS Pricing Agent: {message['content']}\n\n"
        
        return prompt


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - user_id: 用户ID（可选）
            - media: 媒体文件列表（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID（从 runtimeSessionId header 获取）

    Yields:
        str: 流式响应的文本片段（自动处理流式传输）
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}, session_id: {session_id}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return

    print(f"🔄 Processing prompt: {prompt}")

    try:
        # 使用流式响应
        stream = aws_pricing_agent.stream_async(prompt)
        async for event in stream:
            # 每个 event 包含流式响应的片段
            print(f"📤 Streaming event: {event}")
            yield event

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        yield f"Error: {str(e)}"


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    else:
        # 本地 CLI 模式
        print(f"✅ AWS Pricing Agent 创建成功: {aws_pricing_agent.name}")
        
        # 运行命令行界面
        cli = AWSPricingAgentCLI(aws_pricing_agent)
        cli.run()