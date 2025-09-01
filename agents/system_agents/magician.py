#!/usr/bin/env python3

import os
import json
import re
from utils.agent_factory import create_agent_from_prompt_template
from tools.system_tools.agent_build_workflow.prompt_template_provider import list_prompt_templates
from strands.telemetry import StrandsTelemetry

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

def get_agent_list():
    template_agents = json.loads(list_prompt_templates(type="template"))
    system_agents = json.loads(list_prompt_templates(type="system"))
    generated_agents = json.loads(list_prompt_templates(type="generated"))
    
    all_templates = [item for item in system_agents["templates"]] + [item for item in generated_agents["templates"]] + [item for item in template_agents["templates"]]

    agent_dict = {}
    for template in all_templates:
        if "relative_path" in template:
            agent_dict[template["relative_path"]] = template

    return agent_dict

def get_magician_agent(template_path):
    # 创建 agent 的通用参数
    agent_params = {
        "env": "production",
        "version": "latest", 
        "model_id": "default"
    }
    magician_agent = create_agent_from_prompt_template(
        agent_name=template_path, 
        **agent_params
    )
    return magician_agent

def run_magician_agent(magician_agent, input):
    try:
        result = magician_agent(input)
        return result
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None
    
def get_test_case(num):
    test_cases = [
        """
用户请求意图识别结果如下：
user_input="我需要一个agent，我会提供关于IT产品的描述和价格，它需要帮我根据aws服务和产品对照，生成完整的报价表单，并输出markdown格式。请注意，务必采用真实价格数据。",
📊 意图分析结果:
  - 意图类型: new_project
  - 提到的项目: None
  - 项目存在: False
  - 处理建议: 启动新项目创建流程。
        """
    ]
    return test_cases[num]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='指定Agent进行测试')
    parser.add_argument('-a', '--agent', type=str, 
                       default="template_prompts/default.yaml",
                       help='指定要使用的Agent模板路径')
    parser.add_argument('-i', '--input', type=str, 
                       default="请介绍一下你自己，告诉我你有哪些能力，以及你有哪些工具可供使用",
                       help='指定用户输入内容')
    args = parser.parse_args()
    args.input = get_test_case(0) if type(args.input) == int else args.input

    agent_path = re.sub(r'^prompts/', '', args.agent)
    agent_template = get_agent_list().get(agent_path)
    
    if agent_template:
        print(f"✅ 找到代理模板: {agent_path}")
        print(f"🎯 用户输入: {args.input}")
        magician_agent = get_magician_agent(agent_path)
        result = run_magician_agent(magician_agent, args.input)
        print(f"📋 Agent 响应:\n{result}")
    else:
        print(f"❌ 未找到路径为 '{agent_path}' 的代理模板")
        print("可用的代理路径:")
        for path in sorted(get_agent_list().keys()):
            print(f"  - {path}")
    
    