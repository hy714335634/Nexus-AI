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
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
aws_pricing_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/aws_pricing_agent/aws_pricing_agent", 
    **agent_params
)

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
            '--interactive', 
            action='store_true',
            help='启用交互模式，允许多轮对话'
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
        print("🔄 进入交互模式 (输入'exit'或'quit'退出)\n")
        
        conversation_history = [
            {"role": "user", "content": initial_requirement}
        ]
        
        # 首次响应
        response = self.agent(initial_requirement)
        print(f"📋 AWS Pricing Agent:\n{response}\n")
        
        conversation_history.append({"role": "assistant", "content": response})
        
        # 继续对话
        while True:
            user_input = input("您的回复 (exit/quit 退出): ")
            if user_input.lower() in ['exit', 'quit']:
                print("👋 感谢使用AWS Pricing Agent!")
                break
            
            conversation_history.append({"role": "user", "content": user_input})
            
            # 构建完整对话历史
            full_prompt = self._build_conversation_prompt(conversation_history)
            
            response = self.agent(full_prompt)
            print(f"\n📋 AWS Pricing Agent:\n{response}\n")
            
            conversation_history.append({"role": "assistant", "content": response})
    
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


if __name__ == "__main__":
    print(f"✅ AWS Pricing Agent 创建成功: {aws_pricing_agent.name}")
    
    # 运行命令行界面
    cli = AWSPricingAgentCLI(aws_pricing_agent)
    cli.run()