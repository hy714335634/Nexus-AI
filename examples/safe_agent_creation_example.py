#!/usr/bin/env python3
"""
安全Agent创建示例

展示如何使用安全的Agent工厂创建和验证Agent
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_utils.safe_agent_factory import create_validated_agent, create_agent_with_fallback, batch_create_agents
from nexus_utils.agent_validation import validate_agent_dependencies, validate_all_agents
from nexus_utils.post_generation_processor import process_generated_agent


def example_1_create_validated_agent():
    """示例1：创建经过验证的Agent"""
    print("=" * 60)
    print("示例1：创建经过验证的Agent")
    print("=" * 60)
    
    # 创建AWS定价Agent
    result = create_validated_agent(
        agent_name="generated_agents_prompts/aws_pricing_agent/aws_pricing_agent",
        env="production",
        auto_fix_dependencies=True
    )
    
    if result["success"]:
        print(f"✅ Agent创建成功: {result['agent'].name}")
        
        # 测试Agent功能
        try:
            response = result["agent"]("请帮我分析一下AWS EC2的价格")
            print(f"📋 Agent响应: {response[:200]}...")
        except Exception as e:
            print(f"❌ Agent测试失败: {e}")
    else:
        print(f"❌ Agent创建失败: {result['error']}")


def example_2_validate_dependencies():
    """示例2：验证Agent依赖"""
    print("\n" + "=" * 60)
    print("示例2：验证Agent依赖")
    print("=" * 60)
    
    # 验证特定Agent的依赖
    validation_result = validate_agent_dependencies(
        "generated_agents_prompts/aws_pricing_agent/aws_pricing_agent"
    )
    
    print(f"验证结果: {'✅ 通过' if validation_result['valid'] else '❌ 失败'}")
    
    if not validation_result["valid"]:
        print("问题详情:")
        tools_validation = validation_result.get("tools_validation", {})
        
        missing_tools = tools_validation.get("missing_tools", [])
        if missing_tools:
            print("  缺失的工具:")
            for tool in missing_tools:
                print(f"    - {tool}")
        
        invalid_tools = tools_validation.get("invalid_tools", [])
        if invalid_tools:
            print("  无效的工具:")
            for tool_info in invalid_tools:
                print(f"    - {tool_info['tool_path']}: {tool_info['error']}")


def example_3_create_with_fallback():
    """示例3：使用备用Agent创建"""
    print("\n" + "=" * 60)
    print("示例3：使用备用Agent创建")
    print("=" * 60)
    
    # 尝试创建一个可能不存在的Agent，如果失败则使用备用Agent
    result = create_agent_with_fallback(
        agent_name="generated_agents_prompts/non_existent_agent/agent",
        fallback_agent_name="template_prompts/default",
        env="production"
    )
    
    if result["success"]:
        print(f"✅ Agent创建成功: {result['agent'].name}")
        if "primary_agent_error" in result:
            print(f"ℹ️  使用了备用Agent，主要Agent错误: {result['primary_agent_error']}")
    else:
        print(f"❌ Agent创建失败: {result['error']}")


def example_4_batch_create():
    """示例4：批量创建Agent"""
    print("\n" + "=" * 60)
    print("示例4：批量创建Agent")
    print("=" * 60)
    
    # 定义要创建的Agent配置
    agent_configs = [
        {
            "agent_name": "template_prompts/default",
            "env": "production"
        },
        {
            "agent_name": "template_prompts/requirements_analyzer",
            "env": "production"
        }
    ]
    
    # 批量创建
    result = batch_create_agents(agent_configs, continue_on_error=True)
    
    print(f"批量创建结果:")
    print(f"  总数: {result['total_agents']}")
    print(f"  成功: {result['successful_agents']}")
    print(f"  失败: {result['failed_agents']}")
    
    for agent_name, agent_result in result["agent_results"].items():
        status = "✅ 成功" if agent_result["success"] else "❌ 失败"
        print(f"  {agent_name}: {status}")


def example_5_validate_all():
    """示例5：验证所有Agent"""
    print("\n" + "=" * 60)
    print("示例5：验证所有Agent")
    print("=" * 60)
    
    # 验证所有Agent
    result = validate_all_agents()
    
    if "error" in result:
        print(f"❌ 验证失败: {result['error']}")
        return
    
    print(f"验证结果:")
    print(f"  总数: {result['total_agents']}")
    print(f"  有效: {result['valid_agents']}")
    print(f"  无效: {result['invalid_agents']}")
    
    # 显示前5个无效的Agent
    invalid_count = 0
    for agent_name, agent_result in result["agent_results"].items():
        if not agent_result["valid"] and invalid_count < 5:
            print(f"  ❌ {agent_name}: {agent_result.get('error', '未知错误')}")
            invalid_count += 1
    
    if result['invalid_agents'] > 5:
        print(f"  ... 还有 {result['invalid_agents'] - 5} 个无效Agent")


def example_6_post_process():
    """示例6：后处理生成的Agent项目"""
    print("\n" + "=" * 60)
    print("示例6：后处理生成的Agent项目")
    print("=" * 60)
    
    # 处理AWS定价Agent项目
    project_path = "projects/aws_pricing_agent"
    
    if os.path.exists(project_path):
        result = process_generated_agent(
            agent_project_path=project_path,
            auto_fix=True,
            create_backup=True
        )
        
        if result["success"]:
            print(f"✅ 项目处理成功")
            print(f"  处理的文件数: {len(result['processed_files'])}")
            print(f"  应用的修复数: {len(result['fixes_applied'])}")
        else:
            print(f"❌ 项目处理失败: {result['error']}")
    else:
        print(f"⚠️  项目路径不存在: {project_path}")


if __name__ == "__main__":
    print("🚀 安全Agent创建示例")
    
    try:
        example_1_create_validated_agent()
        example_2_validate_dependencies()
        example_3_create_with_fallback()
        example_4_batch_create()
        example_5_validate_all()
        example_6_post_process()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例执行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()