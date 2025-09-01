#!/usr/bin/env python3
"""
系统监控Agent模板

专业的系统监控专家，能够监控系统状态并发出告警。
支持性能监控、异常检测、告警通知、日志分析等功能。
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
system_monitor = create_agent_from_prompt_template(
    agent_name="template_prompts/system_monitor_agent", 
    **agent_params
)

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='系统监控Agent测试')
    parser.add_argument('-i', '--input', type=str, 
                       default="请监控系统状态并报告异常情况",
                       help='测试输入内容')
    parser.add_argument('-m', '--metric', type=str, 
                       help='要监控的指标 (cpu, memory, disk, network)')
    args = parser.parse_args()
    
    print(f"✅ System Monitor Agent 创建成功: {system_monitor.name}")
    
    # 测试 agent 功能
    test_input = args.input
    if args.metric:
        test_input += f"\n监控指标: {args.metric}"
    
    print(f"🎯 测试输入: {test_input}")
    
    try:
        result = system_monitor(test_input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
