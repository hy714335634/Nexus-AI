#!/usr/bin/env python3
"""
本地测试 Agent 的脚本，模拟 AgentCore 调用
"""
import sys
import os
import json

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_agent(agent_path: str, test_input: str = "一加一等于几"):
    """
    本地测试 agent

    Args:
        agent_path: agent 文件路径（相对于项目根目录）
        test_input: 测试输入
    """
    print(f"{'='*80}")
    print(f"测试 Agent: {agent_path}")
    print(f"测试输入: {test_input}")
    print(f"{'='*80}\n")

    try:
        # 导入 agent 模块
        agent_module_name = agent_path.replace('/', '.').replace('.py', '')
        print(f"导入模块: {agent_module_name}")

        # 动态导入
        import importlib
        agent_module = importlib.import_module(agent_module_name)

        # 检查是否有 handler 函数
        if not hasattr(agent_module, 'handler'):
            print(f"❌ Agent 缺少 handler 函数")
            return False

        print(f"✅ 找到 handler 函数\n")

        # 构建测试 event（模拟 AgentCore）
        event = {"prompt": test_input}
        print(f"调用 handler，event: {json.dumps(event, ensure_ascii=False)}\n")

        # 调用 handler
        response = agent_module.handler(event)

        print(f"{'='*80}")
        print(f"响应结果:")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        print(f"{'='*80}\n")

        if response.get('success'):
            print(f"✅ Agent 测试成功")
            print(f"响应内容: {response.get('response')}")
            return True
        else:
            print(f"❌ Agent 返回失败")
            print(f"错误信息: {response.get('error')}")
            return False

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print(f"\n可能的原因:")
        print(f"1. agent 文件路径不正确")
        print(f"2. 缺少依赖包")
        print(f"3. nexus_utils 或 prompts 目录不在 Python 路径中")
        import traceback
        traceback.print_exc()
        return False

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_agent_locally.py <agent_path> [test_input]")
        print("示例: python test_agent_locally.py agents.generated_agents.natural_language_calculator.natural_language_calculator '一加一等于几'")
        sys.exit(1)

    agent_path = sys.argv[1]
    test_input = sys.argv[2] if len(sys.argv) > 2 else "一加一等于几"

    success = test_agent(agent_path, test_input)
    sys.exit(0 if success else 1)
