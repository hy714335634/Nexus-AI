#!/usr/bin/env python3
"""
代码生成Agent

根据需求分析结果生成完整的Strands Agent代码
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import Agent, tool
from strands_tools import calculator, file_read, shell, file_write
from tools.system_tools.agent_template_manager import (
    get_all_templates, 
    search_templates_by_tags, 
    get_template_content,
    get_available_tags
)
from utils.config_loader import get_config
from utils import prompts_manager
import boto3
from strands.models import BedrockModel
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_code_generator_agent():
    try:
        config = get_config()
        
        # 获取环境配置
        env_config = code_generator_agent.get_environment_config(environment)
        if not env_config:
            # 如果指定环境不存在，使用production环境
            env_config = code_generator_agent.get_environment_config("production")
        
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
            name="code_generator",
            model=bedrock_model,
            tools=[
                calculator, 
                file_read, 
                shell, 
                file_write, 
                get_all_templates,
                search_templates_by_tags,
                get_template_content,
                get_available_tags
            ],
            system_prompt=prompts_manager.get_agent("code_generator").get_version("latest").system_prompt,
        )
        
        return agent
        
    except Exception as e:
        return f"创建Agent失败:{str(e)}"


@tool
def code_generator(requirements_analysis: str, environment: str = "production") -> str:
    try:
        # 创建Agent实例
        agent = get_code_generator_agent()
    
        # 调用Agent并返回响应
        response = agent(requirements_analysis)
        print("code_generator==>: ",response)
        return response

    except Exception as e:
        return f"代码生成过程中出现错误: {str(e)}"


def main():
    """主函数，用于测试代码生成Agent"""
    MAIN_SYSTEM_PROMPT = prompts_manager.get_agent("code_generator").get_version("latest").system_prompt
    
    print("=== 代码生成Agent测试 ===")
    
    # 创建Agent实例
    agent = Agent(
        system_prompt=MAIN_SYSTEM_PROMPT,
        callback_handler=None,
        tools=[
            calculator, 
            file_read, 
            shell, 
            file_write, 
            get_all_templates,
            search_templates_by_tags,
            get_template_content,
            get_available_tags,
            code_generator
        ]
    )
    
    # 模拟需求分析结果
    test_requirements_analysis = """
    {
      "requirement_analysis": {
        "user_input": "用户提供IT产品描述和价格信息",
        "business_logic": "根据AWS服务和产品对照，生成完整的报价表单",
        "user_output": "输出markdown格式的报价表单"
      },
      "agent_definition": {
        "name": "it_quote_generator",
        "description": "IT产品报价生成器，根据产品描述和价格生成AWS服务对照的报价表单",
        "system_prompt": "你是一个专业的IT产品报价生成器。用户会提供IT产品的描述和价格信息，你需要根据AWS服务和产品进行对照分析，生成完整的报价表单，并以markdown格式输出。请确保报价表单包含产品信息、AWS服务对照、价格分析等完整内容。"
      },
      "tools_definition": {
        "required_tools": [
          {
            "name": "calculator",
            "description": "数学计算工具",
            "purpose": "用于价格计算和百分比计算",
            "input_parameters": "数学表达式",
            "output_format": "计算结果",
            "dependencies": []
          },
          {
            "name": "file_read",
            "description": "文件读取工具",
            "purpose": "读取AWS服务对照表等参考文件",
            "input_parameters": "文件路径",
            "output_format": "文件内容",
            "dependencies": []
          }
        ]
      }
    }
    """
    
    # 测试代码生成
    result = agent(f"请根据以下需求分析结果生成完整的Strands Agent代码：{test_requirements_analysis}")
    print(result)


if __name__ == "__main__":
    main()
