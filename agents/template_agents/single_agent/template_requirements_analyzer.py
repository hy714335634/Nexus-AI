#!/usr/bin/env python3
"""
简化的工作流编排器 - 使用 agent_factory 动态创建 agents
"""

import os
from strands.multiagent import GraphBuilder
from utils.agent_factory import create_agent_from_prompt_template
import boto3
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()      # Send traces to OTLP endpoint


# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"


if __name__ == "__main__":
    # 定义 agent 创建的通用参数
    agent_params = {
        "env": "production",
        "version": "latest", 
        "model_id": "default"
    }
    
    # 使用agent_factory创建agent
    requirements_analyzer = create_agent_from_prompt_template(
        agent_name="template_prompts/test/template_requirements_analyzer", **agent_params
    )
    requirements_analyzer("我想要构建一个文档协作助手，帮我完成文档格式转换和内容生成工作，我应该如何实现")