#!/usr/bin/env python3
"""
Multi-Cloud Pricing Comparison Agent

专业的多云报价对比智能体，能够根据自然语言描述的云服务需求，通过AWS Pricing API和Azure Retail Prices API
获取真实价格数据，进行智能配置推荐和价格对比分析，生成包含三个Sheet的Excel报告。

功能:
1. 解析用户的自然语言云服务需求描述
2. 通过AWS Pricing API获取真实AWS价格数据（支持EC2、EBS、S3、RDS、ElastiCache、OpenSearch、ELB、网络流量）
3. 通过Azure Retail Prices API获取真实Azure价格数据（支持VM、Disk、Blob、SQL、Redis、Search、Gateway、带宽）
4. 建立AWS和Azure服务的映射关系，自动匹配对应区域
5. 根据vCPU和内存需求推荐最合适的实例类型，应用生产环境最佳实践
6. 对比AWS和Azure的价格差异，计算成本节省百分比
7. 生成包含三个Sheet的Excel报告（AWS报价表、Azure报价表、对比总结表）
8. 支持流式响应、多轮对话、交互式模式

工具:
AWS价格查询工具（9个）：
- get_aws_ec2_pricing: 查询EC2实例价格
- get_aws_ebs_pricing: 查询EBS存储价格
- get_aws_s3_pricing: 查询S3对象存储价格
- get_aws_rds_pricing: 查询RDS数据库价格
- get_aws_elasticache_pricing: 查询ElastiCache缓存价格
- get_aws_opensearch_pricing: 查询OpenSearch搜索服务价格
- get_aws_elb_pricing: 查询ELB负载均衡器价格
- get_aws_network_pricing: 查询网络流量价格
- recommend_aws_instances: 根据vCPU和内存推荐AWS实例

Azure价格查询工具（9个）：
- get_azure_vm_pricing: 查询Virtual Machines价格
- get_azure_disk_pricing: 查询Managed Disks价格
- get_azure_blob_pricing: 查询Blob Storage价格
- get_azure_sql_pricing: 查询Azure SQL Database价格
- get_azure_redis_pricing: 查询Azure Cache for Redis价格
- get_azure_search_pricing: 查询Azure Cognitive Search价格
- get_azure_gateway_pricing: 查询Application Gateway/Load Balancer价格
- get_azure_bandwidth_pricing: 查询带宽价格
- recommend_azure_instances: 根据vCPU和内存推荐Azure实例

对比分析工具（6个）：
- map_aws_to_azure_services: 建立AWS和Azure服务映射
- map_regions: 将地理位置映射到AWS和Azure区域
- compare_pricing_across_clouds: 对比AWS和Azure价格差异
- calculate_annual_cost: 计算年度总成本
- format_pricing_data: 格式化价格数据为易读格式
- generate_excel_report: 生成包含三个Sheet的Excel报告
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

# 初始化配置加载器
config = ConfigLoader()

# 配置遥测和环境变量
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

# 优先使用环境变量，其次使用配置文件，最后使用默认值
otel_endpoint = config.get_with_env_override(
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
agent_config_path = "generated_agents_prompts/multi_cloud_pricing_comparison_agent/multi_cloud_pricing_comparison_agent_prompt"

# 创建 agent 的通用参数生成方法
def create_multi_cloud_pricing_agent(env: str = "production", version: str = "latest", model_id: str = "default"):
    """创建多云报价对比Agent
    
    Args:
        env: 环境类型（development/production/testing）
        version: 版本号（默认latest）
        model_id: 模型ID（默认default，使用claude-sonnet-4-5）
    
    Returns:
        创建的Agent实例
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

# 使用 agent_factory 创建 agent
multi_cloud_pricing_agent = create_multi_cloud_pricing_agent()


class MultiCloudPricingAgentCLI:
    """Multi-Cloud Pricing Comparison Agent 命令行接口类"""
    
    def __init__(self, agent):
        """初始化Multi-Cloud Pricing Agent CLI

        Args:
            agent: 已初始化的Multi-Cloud Pricing Agent
        """
        self.agent = agent
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器

        Returns:
            argparse.ArgumentParser: 参数解析器对象
        """
        parser = argparse.ArgumentParser(
            description='Multi-Cloud Pricing Comparison Agent - 根据自然语言需求提供AWS和Azure服务配置和价格对比报价'
        )
        parser.add_argument(
            '-r', '--requirement', 
            type=str,
            help='自然语言描述的云服务需求'
        )
        parser.add_argument(
            '-f', '--file', 
            type=str,
            help='包含需求描述的文件路径'
        )
        parser.add_argument(
            '--aws-region', 
            type=str,
            default='us-east-1',
            help='AWS区域代码，默认为us-east-1'
        )
        parser.add_argument(
            '--azure-region', 
            type=str,
            default='eastus',
            help='Azure区域代码，默认为eastus'
        )
        parser.add_argument(
            '-it', '--interactive', 
            action='store_true',
            help='启动交互式多轮对话模式'
        )
        parser.add_argument(
            '-o', '--output',
            type=str,
            help='指定Excel报告输出路径'
        )
        return parser
    
    def run(self) -> None:
        """运行Multi-Cloud Pricing Agent CLI"""
        args = self.parser.parse_args()
        
        # 获取需求描述
        requirement = self._get_requirement(args)
        if not requirement:
            print("❌ 错误: 请提供需求描述 (使用 -r 或 --file 参数)")
            return
        
        # 添加区域信息
        if args.aws_region or args.azure_region:
            requirement += f"\nAWS区域: {args.aws_region}, Azure区域: {args.azure_region}"
        
        # 添加输出路径信息
        if args.output:
            requirement += f"\n输出路径: {args.output}"
        
        print(f"🔍 正在分析需求并生成多云服务报价对比...\n")
        
        try:
            if args.interactive:
                self._run_interactive_mode(requirement)
            else:
                response = self.agent(requirement)
                # 流式响应已在agent内部处理，这里不需要再次打印
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
            return input("请描述您的云服务需求: ")
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


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

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
        stream = multi_cloud_pricing_agent.stream_async(prompt)
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
        print(f"✅ Multi-Cloud Pricing Comparison Agent 创建成功: {multi_cloud_pricing_agent.name}")
        
        # 运行命令行界面
        cli = MultiCloudPricingAgentCLI(multi_cloud_pricing_agent)
        cli.run()
