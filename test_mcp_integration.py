#!/usr/bin/env python3
"""
测试MCP集成的Agent模板搜索功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/peijiaw/Desktop/git_repos/Nexus-AI')

from tools.system_tools.agent_build_workflow.agent_template_provider import search_templates_with_graphrag

def test_mcp_integration():
    """测试MCP集成的模板搜索"""
    
    print("🧪 测试MCP集成的Agent模板搜索")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        "找一个把html转化为pdf的工具",
        "我需要处理医学文档的Agent", 
        "有没有能做AWS架构设计的Agent？"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case}")
        print("-" * 40)
        
        try:
            result = search_templates_with_graphrag(test_case, top_k=3)
            print("✅ 搜索成功")
            print("📄 结果:")
            print(result)
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
        
        print()

if __name__ == "__main__":
    test_mcp_integration()
