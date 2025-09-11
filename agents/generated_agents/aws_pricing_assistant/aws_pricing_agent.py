#!/usr/bin/env python3
"""
AWS产品报价智能体

专业的AWS产品报价助手，能够分析用户提供的自然语言需求或其他云平台账单，
推荐合理的AWS配置方案并提供准确的价格信息。支持EC2、EBS、S3、网络流量、
负载均衡器、RDS、ElastiCache、Opensearch等AWS产品的实时报价。
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List, Union
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("aws_pricing_agent")

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class AWSPricingAgent:
    """
    AWS产品报价智能体，负责分析用户需求，推荐AWS配置方案，提供准确价格信息，
    生成专业销售报价方案。
    """
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化AWS产品报价智能体
        
        Args:
            env: 运行环境，可选值为 "development", "production", "testing"
            version: 提示词模板版本
            model_id: 使用的模型ID
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        self.agent = self._create_agent()
        logger.info(f"AWS产品报价智能体初始化完成，环境：{env}，版本：{version}")
    
    def _create_agent(self) -> Any:
        """
        创建并返回AWS产品报价智能体实例
        
        Returns:
            创建的智能体实例
        """
        agent_params = {
            "env": self.env,
            "version": self.version,
            "model_id": self.model_id
        }
        
        try:
            agent = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/aws_pricing_assistant/aws_pricing_agent", 
                **agent_params
            )
            return agent
        except Exception as e:
            logger.error(f"创建智能体失败: {str(e)}")
            raise RuntimeError(f"创建智能体失败: {str(e)}")
    
    def analyze_requirements(self, user_input: str) -> str:
        """
        分析用户需求，推荐AWS配置方案，提供价格信息，生成报价方案
        
        Args:
            user_input: 用户输入的需求描述或其他云平台账单
            
        Returns:
            包含AWS配置推荐和价格报价的专业方案
        """
        try:
            logger.info(f"处理用户需求: {user_input[:100]}...")
            response = self.agent(user_input)
            logger.info("成功生成AWS配置推荐和价格报价")
            return response
        except Exception as e:
            error_msg = f"处理用户需求时发生错误: {str(e)}"
            logger.error(error_msg)
            return f"很抱歉，在处理您的需求时发生了错误: {str(e)}。请稍后再试或提供更详细的信息。"
    
    def generate_proposal(self, 
                         customer_name: str, 
                         requirements: str, 
                         region: str = "us-east-1", 
                         is_production: bool = True) -> str:
        """
        生成专业的AWS销售报价方案
        
        Args:
            customer_name: 客户名称
            requirements: 客户需求描述
            region: AWS区域代码
            is_production: 是否用于生产环境
            
        Returns:
            专业的AWS销售报价方案
        """
        prompt = f"""
        请为客户 {customer_name} 生成一份专业的AWS销售报价方案。

        客户需求:
        {requirements}

        目标区域: {region}
        生产环境: {'是' if is_production else '否'}

        请提供详细的配置推荐、价格明细和总价，并确保符合AWS最佳实践。
        """
        
        try:
            logger.info(f"为客户 {customer_name} 生成销售报价方案...")
            response = self.agent(prompt)
            logger.info(f"成功为客户 {customer_name} 生成销售报价方案")
            return response
        except Exception as e:
            error_msg = f"生成销售报价方案时发生错误: {str(e)}"
            logger.error(error_msg)
            return f"很抱歉，在生成销售报价方案时发生了错误: {str(e)}。请稍后再试或提供更详细的信息。"
    
    def generate_migration_proposal(self, 
                                   customer_name: str, 
                                   current_environment: str, 
                                   target_requirements: str, 
                                   region: str = "us-east-1") -> str:
        """
        生成AWS迁移方案
        
        Args:
            customer_name: 客户名称
            current_environment: 当前环境描述
            target_requirements: 目标需求描述
            region: AWS区域代码
            
        Returns:
            AWS迁移方案
        """
        prompt = f"""
        请为客户 {customer_name} 生成一份从当前环境迁移到AWS的方案。

        当前环境:
        {current_environment}

        目标需求:
        {target_requirements}

        目标区域: {region}

        请提供详细的迁移方案，包括配置映射、优化建议、迁移步骤、价格对比和总成本。
        """
        
        try:
            logger.info(f"为客户 {customer_name} 生成迁移方案...")
            response = self.agent(prompt)
            logger.info(f"成功为客户 {customer_name} 生成迁移方案")
            return response
        except Exception as e:
            error_msg = f"生成迁移方案时发生错误: {str(e)}"
            logger.error(error_msg)
            return f"很抱歉，在生成迁移方案时发生了错误: {str(e)}。请稍后再试或提供更详细的信息。"
    
    def generate_comparative_proposal(self, 
                                     customer_name: str, 
                                     competitor_info: str, 
                                     requirements: str, 
                                     region: str = "us-east-1") -> str:
        """
        生成对比竞争对手产品的AWS销售报价方案
        
        Args:
            customer_name: 客户名称
            competitor_info: 竞争对手信息
            requirements: 客户需求描述
            region: AWS区域代码
            
        Returns:
            对比竞争对手产品的AWS销售报价方案
        """
        prompt = f"""
        请为客户 {customer_name} 生成一份AWS与竞争对手的对比报价方案。

        竞争对手信息:
        {competitor_info}

        客户需求:
        {requirements}

        目标区域: {region}

        请提供详细的配置对比、价格对比、性能对比和AWS的优势分析。
        """
        
        try:
            logger.info(f"为客户 {customer_name} 生成对比报价方案...")
            response = self.agent(prompt)
            logger.info(f"成功为客户 {customer_name} 生成对比报价方案")
            return response
        except Exception as e:
            error_msg = f"生成对比报价方案时发生错误: {str(e)}"
            logger.error(error_msg)
            return f"很抱歉，在生成对比报价方案时发生了错误: {str(e)}。请稍后再试或提供更详细的信息。"
    
    def __call__(self, user_input: str) -> str:
        """
        处理用户输入，返回AWS配置推荐和价格报价
        
        Args:
            user_input: 用户输入的需求描述或其他云平台账单
            
        Returns:
            包含AWS配置推荐和价格报价的专业方案
        """
        return self.analyze_requirements(user_input)


def create_aws_pricing_agent(env: str = "production", 
                            version: str = "latest", 
                            model_id: str = "default") -> AWSPricingAgent:
    """
    创建AWS产品报价智能体实例
    
    Args:
        env: 运行环境，可选值为 "development", "production", "testing"
        version: 提示词模板版本
        model_id: 使用的模型ID
        
    Returns:
        AWS产品报价智能体实例
    """
    return AWSPricingAgent(env=env, version=version, model_id=model_id)


# 直接使用agent_factory创建的简化版本
def create_simple_aws_pricing_agent(env: str = "production", 
                                  version: str = "latest", 
                                  model_id: str = "default") -> Any:
    """
    创建简化版AWS产品报价智能体实例，直接使用agent_factory
    
    Args:
        env: 运行环境，可选值为 "development", "production", "testing"
        version: 提示词模板版本
        model_id: 使用的模型ID
        
    Returns:
        AWS产品报价智能体实例
    """
    agent_params = {
        "env": env,
        "version": version,
        "model_id": model_id
    }
    
    return create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/aws_pricing_assistant/aws_pricing_agent", 
        **agent_params
    )


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AWS产品报价智能体测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请为我推荐一个4核8GB内存的EC2实例和100GB的gp3存储，在北京区域运行Linux系统",
                       help='测试输入内容')
    parser.add_argument('-e', '--env', type=str, default="production",
                       choices=["development", "production", "testing"],
                       help='运行环境')
    parser.add_argument('-v', '--version', type=str, default="latest",
                       help='提示词模板版本')
    parser.add_argument('-m', '--model', type=str, default="default",
                       help='使用的模型ID')
    parser.add_argument('-s', '--simple', action='store_true',
                       help='使用简化版创建方式')
    args = parser.parse_args()
    
    # 创建智能体
    try:
        if args.simple:
            agent = create_simple_aws_pricing_agent(env=args.env, version=args.version, model_id=args.model)
            print(f"✅ AWS产品报价智能体(简化版)创建成功")
        else:
            agent = create_aws_pricing_agent(env=args.env, version=args.version, model_id=args.model)
            print(f"✅ AWS产品报价智能体创建成功")
        
        # 测试智能体功能
        print(f"🎯 测试输入: {args.input}")
        
        result = agent(args.input)
        print(f"📋 智能体响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")