#!/usr/bin/env python3
"""
提示词工程师 Agent - 使用 agent_factory 创建
"""

import os
from strands import Agent
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
from tools.system_tools.agent_build_workflow.stage_tracker import (
    mark_sub_stage_running,
    mark_sub_stage_completed,
    mark_sub_stage_failed,
)

loader = ConfigLoader()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"


def _get_project_id():
    """获取当前项目ID"""
    return os.environ.get("NEXUS_STAGE_TRACKER_PROJECT_ID")


def get_prompt_engineer(env: str = "production", version: str = None, enable_sub_stage_tracking: bool = True) -> Agent:
    """
    创建提示词工程师 Agent

    Args:
        env: 环境名称
        version: Agent版本
        enable_sub_stage_tracking: 是否启用子阶段追踪（默认True）

    Returns:
        Agent: 提示词工程师 Agent（可能被包装以支持子阶段追踪）
    """
    if version is None:
        version = loader.get_nested("nexus_ai", "workflow_default_version", "agent_build")
    prompt_engineer = create_agent_from_prompt_template(
        agent_name="system_agents_prompts/agent_build_workflow/prompt_engineer",
        env=env,
        version=version
    )

    # 如果启用子阶段追踪，包装Agent
    if enable_sub_stage_tracking:
        prompt_engineer = _wrap_with_sub_stage_tracking(prompt_engineer, "prompt_engineer")

    return prompt_engineer


def _wrap_with_sub_stage_tracking(agent: Agent, sub_stage_name: str) -> Agent:
    """
    包装Agent以支持子阶段追踪

    Requirements: 7.2, 7.3, 7.4
    """
    # 检查是否已经包装过，避免重复包装
    if getattr(agent, f"_sub_stage_tracking_wrapped_{sub_stage_name}", False):
        return agent

    # 保存原始的__call__方法
    original_call = agent.__call__

    def wrapped_call(*args, **kwargs):
        """带子阶段跟踪的Agent调用方法"""
        project_id = _get_project_id()

        if project_id:
            print(f"\n🔄 [{sub_stage_name}] 标记子阶段为运行中...")
            mark_sub_stage_running(project_id, sub_stage_name)

        try:
            # 调用原始的Agent方法
            result = original_call(*args, **kwargs)

            if project_id:
                # TODO: 从result中提取artifacts信息
                # 目前先传空列表，后续可以从result中解析
                artifacts = []
                print(f"✅ [{sub_stage_name}] 标记子阶段为已完成")
                mark_sub_stage_completed(project_id, sub_stage_name, artifacts=artifacts)

            return result
        except Exception as e:
            if project_id:
                print(f"❌ [{sub_stage_name}] 标记子阶段为失败: {str(e)}")
                mark_sub_stage_failed(project_id, sub_stage_name, str(e))
            raise

    # 替换Agent的__call__方法
    agent.__call__ = wrapped_call  # type: ignore[assignment]
    # 标记已包装，避免重复包装
    setattr(agent, f"_sub_stage_tracking_wrapped_{sub_stage_name}", True)

    return agent

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='提示词工程师 Agent 测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="根据 Agent 设计方案，编写高质量的提示词模板",
                       help='测试输入内容')
    args = parser.parse_args()
    prompt_engineer = get_prompt_engineer()
    print(f"✅ Prompt Engineer Agent 创建成功: {prompt_engineer.name}")
    
    # 测试 agent 功能
    test_input = args.input
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = prompt_engineer(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")