#!/usr/bin/env python3
"""
测试 generate_content 工具是否能正常工作
"""

import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tools.system_tools.agent_build_workflow.project_manager import generate_content

def test_generate_prompt():
    """测试生成 prompt 文件"""
    print("=" * 80)
    print("测试 1: 生成 Prompt 文件")
    print("=" * 80)

    prompt_content = """agent:
  name: "test_greeting_agent"
  description: "测试问候 Agent"
  category: "test"
  environments:
    production:
      max_tokens: 4096
      temperature: 0.7
      top_p: 0.9
      streaming: False
  versions:
    - version: "1.0"
      status: "stable"
      created_date: "2025-11-23"
      system_prompt: |
        你是一个测试用的问候 Agent。

        你的职责是：
        1. 接收用户的问候
        2. 返回友好的问候响应

      tools_dependencies:
        - "strands_tools/current_time"
"""

    result = generate_content(
        type="prompt",
        content=prompt_content,
        project_name="greeting_agent",
        artifact_name="test_greeting_prompt"
    )

    print("Result:", result)
    print("\n")

    try:
        result_json = json.loads(result)
        if result_json.get("status") == "success":
            print("✅ Prompt 文件生成成功!")
            print(f"文件路径: {result_json.get('file_path')}")
            return True
        else:
            print("❌ Prompt 文件生成失败!")
            return False
    except json.JSONDecodeError:
        if "错误" in result or "Error" in result:
            print(f"❌ 错误: {result}")
            return False
        else:
            print("⚠️ 无法解析结果")
            return False


def test_generate_tool():
    """测试生成 tool 文件"""
    print("=" * 80)
    print("测试 2: 生成 Tool 文件")
    print("=" * 80)

    tool_content = '''"""
测试工具：问候生成器
"""

def generate_greeting(name: str) -> str:
    """
    生成问候语

    Args:
        name: 用户名称

    Returns:
        问候语字符串
    """
    return f"你好，{name}！欢迎使用 Nexus-AI!"


if __name__ == "__main__":
    print(generate_greeting("测试用户"))
'''

    result = generate_content(
        type="tool",
        content=tool_content,
        project_name="greeting_agent",
        artifact_name="test_greeting_tool"
    )

    print("Result:", result)
    print("\n")

    try:
        result_json = json.loads(result)
        if result_json.get("status") == "success":
            print("✅ Tool 文件生成成功!")
            print(f"文件路径: {result_json.get('file_path')}")
            return True
        else:
            print("❌ Tool 文件生成失败!")
            return False
    except json.JSONDecodeError:
        if "错误" in result or "Error" in result:
            print(f"❌ 错误: {result}")
            return False
        else:
            print("⚠️ 无法解析结果")
            return False


def test_generate_agent():
    """测试生成 agent 文件"""
    print("=" * 80)
    print("测试 3: 生成 Agent 文件")
    print("=" * 80)

    agent_content = '''#!/usr/bin/env python3
"""
测试 Greeting Agent
"""

from typing import Dict, Any


class GreetingAgent:
    """简单的问候 Agent"""

    def __init__(self, name: str = "GreetingAgent"):
        self.name = name

    def greet(self, user_name: str) -> Dict[str, Any]:
        """
        生成问候响应

        Args:
            user_name: 用户名称

        Returns:
            问候响应字典
        """
        return {
            "status": "success",
            "message": f"你好，{user_name}！",
            "agent": self.name
        }


if __name__ == "__main__":
    agent = GreetingAgent()
    print(agent.greet("测试用户"))
'''

    result = generate_content(
        type="agent",
        content=agent_content,
        project_name="greeting_agent",
        artifact_name="test_greeting_agent"
    )

    print("Result:", result)
    print("\n")

    try:
        result_json = json.loads(result)
        if result_json.get("status") == "success":
            print("✅ Agent 文件生成成功!")
            print(f"文件路径: {result_json.get('file_path')}")
            return True
        else:
            print("❌ Agent 文件生成失败!")
            return False
    except json.JSONDecodeError:
        if "错误" in result or "Error" in result:
            print(f"❌ 错误: {result}")
            return False
        else:
            print("⚠️ 无法解析结果")
            return False


def cleanup_test_files():
    """清理测试生成的文件"""
    print("=" * 80)
    print("清理测试文件")
    print("=" * 80)

    import shutil

    test_dirs = [
        "projects/greeting_agent/prompts/generated_agents_prompts/greeting_agent",
        "projects/greeting_agent/tools/generated_tools/greeting_agent",
        "projects/greeting_agent/agents/generated_agents/greeting_agent"
    ]

    for dir_path in test_dirs:
        if os.path.exists(dir_path):
            try:
                # 只删除测试文件，不删除整个目录
                for file in os.listdir(dir_path):
                    if file.startswith("test_"):
                        file_path = os.path.join(dir_path, file)
                        os.remove(file_path)
                        print(f"✅ 已删除: {file_path}")
            except Exception as e:
                print(f"⚠️ 删除失败 {dir_path}: {e}")


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("开始测试 generate_content 工具")
    print("=" * 80 + "\n")

    results = []

    # 测试 1: Prompt 生成
    results.append(("Prompt", test_generate_prompt()))

    # 测试 2: Tool 生成
    results.append(("Tool", test_generate_tool()))

    # 测试 3: Agent 生成
    results.append(("Agent", test_generate_agent()))

    # 显示总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:15} : {status}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)

    print(f"\n总计: {passed_count}/{total} 个测试通过")

    # 询问是否清理
    print("\n是否清理测试文件? (y/n): ", end="")
    # 在脚本模式下自动清理
    cleanup = input().strip().lower() if sys.stdin.isatty() else 'n'

    if cleanup == 'y':
        cleanup_test_files()
    else:
        print("测试文件已保留，可手动检查")

    return passed_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
