#!/usr/bin/env python3
"""
需求分析Agent

根据客户需求生成标准化的需求分析文档，为后续agent开发提供指导
"""

import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import Agent, tool
from strands_tools import calculator,file_read,file_write
from utils.config_loader import get_config
from utils import prompts_manager
import boto3
from strands.models import BedrockModel
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_requirements_analyzer_agent():
    try:
        config = get_config()
        strands_config = config.get_strands_config()
        # 获取提示词管理器

        # 获取环境配置
        env_config = requirements_agent.get_environment_config(environment)
        if not env_config:
            # 如果指定环境不存在，使用production环境
            env_config = requirements_agent.get_environment_config("production")
        

        # Create a custom boto3 session
        session = boto3.Session(
            region_name=config.get_aws_config().get("bedrock_region_name")
        )

        # Create a Bedrock model with the custom session
        bedrock_model = BedrockModel(
            model_id=config.get_bedrock_config().get("model_id"),
            max_tokens=env_config.max_tokens,
            boto_session=session
        )

        # 创建Agent实例
        agent = Agent(
            name="requirements_analyzer",
            model=bedrock_model,
            tools=[file_read,file_write],  # 可以添加更多工具
            system_prompt=prompts_manager.get_agent("requirements_analyzer").get_version("latest").system_prompt,
        )
        
        return agent
        
    except Exception as e:
        return f"创建Agent失败: {str(e)}"

@tool
def requirements_analyzer(user_input: str, environment: str = "production") -> str:
    try:
        # 创建Agent实例
        agent = get_requirements_analyzer_agent()
        
        # 调用Agent并返回响应
        response = agent(user_input)
        print("requirements_analyzer==>: ",response)
        return response
        
    except Exception as e:
        return f"需求分析过程中出现错误: {str(e)}"


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试需求分析Agent"""
    test_requirements = """
    我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。
    """
    
    print("=== 需求分析Agent测试 ===")
    print("测试需求:", test_requirements)
    print("\n=== 分析结果 ===")
    
    # 测试基础需求分析
    result = requirements_analyzer(test_requirements)
    print(result)

if __name__ == "__main__":
    main()