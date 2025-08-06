#!/usr/bin/env python3
"""
编排器Agent - Swarm版本

使用Swarm架构协调多个专业Agent完成复杂任务
"""

import logging
import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from strands import Agent
from strands.multiagent import Swarm
from strands.models import BedrockModel
from strands_tools import calculator, file_read, shell, file_write
import boto3
from utils.config_loader import get_config
from utils import prompts_manager
from utils.agent_logging import LoggingHook

# 引用已开发的system agents
from agents.system_agents.requirements_analyzer_agent import get_requirements_analyzer_agent
from agents.system_agents.code_generator_agent import get_code_generator_agent

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 启用调试日志
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)


def create_bedrock_model(max_tokens: int = 4096) -> BedrockModel:
    """创建Bedrock模型实例"""
    try:
        config = get_config()
        
        # 创建自定义boto3会话
        session = boto3.Session(
            region_name=config.get_aws_config().get("bedrock_region_name")
        )
        
        # 创建Bedrock模型
        bedrock_model = BedrockModel(
            model_id=config.get_bedrock_config().get("model_id"),
            max_tokens=max_tokens,
            boto_session=session
        )
        
        return bedrock_model
        
    except Exception as e:
        raise Exception(f"创建Bedrock模型失败: {str(e)}")


def create_orchestrator_swarm() -> Swarm:
    """创建编排器Swarm"""
    try:
        # 获取orchestrator系统提示词
        orchestrator_prompt = prompts_manager.get_agent("orchestrator").get_version("latest").system_prompt
        
        # 创建Bedrock模型实例
        bedrock_model = create_bedrock_model(max_tokens=4096)
        
        # 创建orchestrator agent
        orchestrator = Agent(
            model=bedrock_model,
            name="orchestrator",
            system_prompt=orchestrator_prompt,
            tools=[file_read, file_write, calculator]
        )
        
        requirements_agent = None
        # 使用已开发的专业化Agent
        print("正在创建requirements_analyzer...")
        try:
            requirements_analyzer = get_requirements_analyzer_agent()
            # 检查返回值是否为字符串（错误信息）
            if isinstance(requirements_analyzer, str):
                raise Exception(requirements_analyzer)
            # 确保agent有正确的名称用于swarm
            requirements_analyzer.name = "requirements_analyzer"
        except Exception as e:
            print(f"创建requirements_analyzer失败: {e}")
            # 创建备用的requirements_analyzer
            requirements_analyzer = Agent(
                model=bedrock_model,
                name="requirements_analyzer",
                system_prompt=prompts_manager.get_agent("requirements_analyzer").get_version("latest").system_prompt,
                tools=[file_read, file_write, calculator]
            )
        
        code_generator = None
        print("正在创建code_generator...")
        try:
            code_generator = get_code_generator_agent()
            # 检查返回值是否为字符串（错误信息）
            if isinstance(code_generator, str):
                raise Exception(code_generator)
            # 确保agent有正确的名称用于swarm
            code_generator.name = "code_generator"
        except Exception as e:
            print(f"创建code_generator失败: {e}")
            # 创建备用的code_generator
            code_generator = Agent(
                model=bedrock_model,
                name="code_generator",
                system_prompt=prompts_manager.get_agent("code_generator").get_version("latest").system_prompt,
                tools=[file_read, file_write, calculator, shell]
            )
        
        print("开始创建Swarm...")
        
        # 创建agent列表
        # agents = [orchestrator, requirements_analyzer, code_generator]
        
        # 创建Swarm
        swarm = Swarm(
            [orchestrator, requirements_analyzer, code_generator],
            max_handoffs=25,
            max_iterations=30,
            execution_timeout=1200.0,  # 20分钟
            node_timeout=400.0,        # 6.7分钟每个Agent
            repetitive_handoff_detection_window=10,
            repetitive_handoff_min_unique_agents=2
        )
        
        return swarm
        
    except Exception as e:
        raise Exception(f"创建Swarm失败: {str(e)}")


def execute_orchestrator_task(user_input: str) -> Dict[str, Any]:
    """执行编排器任务"""
    try:
        # 创建Swarm
        swarm = create_orchestrator_swarm()
        
        # 执行任务
        print(f"=== 开始执行任务 ===")
        print(f"用户输入: {user_input}")
        
        result = swarm(user_input)
        
        # 处理结果
        print(f"\n=== 执行结果 ===")
        print(f"状态: {result.status}")
        print(f"总迭代次数: {result.execution_count}")
        print(f"执行时间: {result.execution_time}ms")
        print(f"Token使用量: {result.accumulated_usage}")
        
        # 显示参与的Agent
        print(f"\n=== 参与的Agent ===")
        for node in result.node_history:
            print(f"Agent: {node.node_id}")
        
        # 获取各Agent的结果
        results = {}
        available_agents = ["orchestrator", "requirements_analyzer", "code_generator"]
            
        for agent_name in available_agents:
            if agent_name in result.results:
                agent_result = result.results[agent_name].result
                results[agent_name] = agent_result
                print(f"\n=== {agent_name} 结果 ===")
                print(agent_result)
        
        return {
            "status": result.status,
            "execution_count": result.execution_count,
            "execution_time": result.execution_time,
            "token_usage": result.accumulated_usage,
            "agent_results": results,
            "node_history": [node.node_id for node in result.node_history]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agent_results": {},
            "node_history": []
        }


def main():
    """主函数，用于测试编排器Swarm"""
    test_input = """我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。"""
    
    print("=== 编排器Swarm测试 ===")
    
    # 执行任务
    result = execute_orchestrator_task(test_input)
    
    if result["status"] == "error":
        print(f"执行失败: {result['error']}")
    else:
        print(f"\n=== 最终总结 ===")
        print(f"任务执行成功!")
        print(f"参与Agent: {', '.join(result['node_history'])}")
        print(f"总执行时间: {result['execution_time']}ms")


if __name__ == "__main__":
    main()