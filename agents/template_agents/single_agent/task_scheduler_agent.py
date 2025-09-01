#!/usr/bin/env python3
"""
任务调度Agent模板

专业的任务调度专家，能够管理和执行各种任务。
支持任务创建、调度执行、状态监控、结果收集等功能。
"""

import os
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
task_scheduler = create_agent_from_prompt_template(
    agent_name="template_prompts/task_scheduler_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='任务调度Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请创建一个定时任务来执行指定操作",
                       help='测试输入内容')
    parser.add_argument('-s', '--schedule', type=str, 
                       help='任务调度时间 (cron格式)')
    args = parser.parse_args()
    
    print(f"✅ Task Scheduler Agent 创建成功: {task_scheduler.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.schedule:
        test_input += f"\n调度时间: {args.schedule}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = task_scheduler(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
