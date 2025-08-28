#!/usr/bin/env python3
import sys
import os
from typing import Dict, Any, Optional
from strands import Agent, tool
from strands_tools import calculator,file_read,file_write,current_time,shell
from utils.config_loader import get_config
from utils import prompts_manager
from tools.system_tools.project_manager import get_project_config,get_project_readme,get_project_status,update_project_config,update_project_readme,update_project_status,update_project_stage_content,get_project_stage_content
import boto3
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
os.environ["BYPASS_TOOL_CONSENT"] = "true"

config = get_config()

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=10,
    read_timeout=120
)
        
# Create a custom boto3 session
session = boto3.Session(
    region_name=config.get_aws_config().get("bedrock_region_name")
)

# Create a Bedrock model with the custom session
bedrock_model = BedrockModel(
    model_id=config.get_bedrock_config().get("model_id"),
    max_tokens=prompts_manager.get_agent("requirements_analyzer").get_environment_config("production").max_tokens,
    boto_session=session,
    boto_client_config=boto_config
)

# 创建Agent实例
requirements_analyzer = Agent(
    name="requirements_analyzer",
    model=bedrock_model,
    tools=[
        file_read,
        current_time,
        get_project_status,
        get_project_config,
        get_project_readme,
        get_project_stage_content,
        update_project_config,
        update_project_readme,
        update_project_status,
        update_project_stage_content
    ], 
    system_prompt=prompts_manager.get_agent("requirements_analyzer").get_version("latest").system_prompt,
)

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