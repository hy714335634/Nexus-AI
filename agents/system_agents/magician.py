#!/usr/bin/env python3

from email.policy import default
import os
import json
import re

from strands.tools.decorator import R
from utils.agent_factory import create_agent_from_prompt_template
from tools.system_tools.agent_build_workflow.prompt_template_provider import list_prompt_templates
from strands.telemetry import StrandsTelemetry
from utils.magician import Magician

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
default_agent_path = "prompts/template_prompts/default.yaml"

def get_agent_list():
    template_agents = json.loads(list_prompt_templates(type="template"))
    generated_agents = json.loads(list_prompt_templates(type="generated"))
    
    all_templates = [item for item in generated_agents["templates"]] + [item for item in template_agents["templates"]]

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



def interactive_mode(agent,agent_path=None):
    """交互式模式"""
    if agent:
        magician_agent = agent
        agent_name = agent.name
    elif agent_path:
        # 指定agent进行交互访问
        agent_template = get_agent_list().get(agent_path)
        if not agent_template:
            print(f"❌ 未找到路径为 '{agent_path}' 的代理模板")
            print("可用的代理路径:")
            for path in sorted(get_agent_list().keys()):
                print(f"  - {path}")
            return
        print(f"✅ 找到代理模板: {agent_path}")
        magician_agent = get_magician_agent(agent_path)
        agent_name = agent_template.get("name")
    else:
        # 默认agent交互访问
        magician_agent = get_magician_agent(default_agent_path)
        agent_name = "默认Agent"
    
    print(f"🤖 已启动 {agent_name} 交互模式")
    print("💡 输入 'quit' 或 'exit' 退出交互模式")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见！")
                break
            
            if not user_input:
                print("⚠️  请输入有效内容")
                continue
            
            print(f"🤖 {agent_name} 正在思考...")
            
            
            result = run_magician_agent(magician_agent, user_input)
            if result:
                print(f"🤖 {agent_name}:\n{result}")
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='指定Agent进行测试')
    parser.add_argument('-a', '--agent', type=str,
                       help='指定要使用的Agent模板路径')
    parser.add_argument('-i', '--input', type=str, 
                       help='指定用户输入内容')
    parser.add_argument('--interactive', action='store_true',
                       help='启用交互式模式')
    args = parser.parse_args()

    # 处理交互式模式
    if args.interactive:
        interactive_mode(args.agent)
    # 如果没有任何参数，则进行默认交互式模式
    elif not args.agent and not args.input:
        interactive_mode()
    # 处理指定agent的情况
    elif args.agent:
        agent_path = args.agent
        agent_template = get_agent_list().get(agent_path)
        if agent_template:
            print(f"✅ 找到代理模板: {agent_path}")
            print(f"🎯 用户输入: {args.input}")
            magician_agent = get_magician_agent(agent_path)
            result = run_magician_agent(magician_agent, args.input if args.input else "请介绍一下你自己，告诉我你有哪些能力，以及你有哪些工具可供使用")
            print(f"📋 Agent 响应:\n{result}")
        else:
            print(f"❌ 未找到路径为 '{agent_path}' 的代理模板")
            print("可用的代理路径:")
            for path in sorted(get_agent_list().keys()):
                print(f"  - {path}")
    # 处理只指定输入的情况，调用magician_orchestration_agent
    elif args.input:
        if not args.interactive:
            mgician = Magician(args.input)
            magician_agent = mgician.build_magician_agent()
            result = run_magician_agent(magician_agent, args.input)
            print(f"📋 Agent 响应:\n{result}")
            magician_agent.get_magician_description()
        else:
            mgician = Magician(args.input)
            magician_agent = mgician.build_magician_agent()
            interactive_mode(magician_agent,args.input)
            magician_agent.get_magician_description()
        
    else:
        # 默认情况，显示帮助信息
        parser.print_help()