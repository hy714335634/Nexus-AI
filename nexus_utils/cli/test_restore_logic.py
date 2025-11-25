#!/usr/bin/env python3
"""
测试恢复逻辑 - 验证项目名称映射
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nexus_utils.cli.models.backup import BackupManifest
from datetime import datetime

def test_path_mapping():
    """测试路径映射逻辑"""
    
    # 模拟 manifest
    manifest = BackupManifest(
        version="1.0.0",
        project_name="old_project",
        created_at=datetime.now(),
        nexus_version="v2.1.0",
        resources={
            'project': [
                'projects/old_project/config.yaml',
                'projects/old_project/README.md'
            ],
            'agents': [
                'agents/generated_agents/old_project/agent1.py'
            ],
            'prompts': [
                'prompts/generated_agents_prompts/old_project/agent1.yaml'
            ],
            'tools': [
                'tools/generated_tools/old_project/tool1.py'
            ]
        },
        checksums={}
    )
    
    original_project_name = manifest.project_name
    new_project_name = "new_project"
    
    print("=" * 70)
    print("测试路径映射逻辑")
    print("=" * 70)
    print(f"原项目名: {original_project_name}")
    print(f"新项目名: {new_project_name}")
    print()
    
    # 测试路径映射
    test_cases = [
        ('projects/old_project/config.yaml', 'projects/new_project/config.yaml'),
        ('agents/generated_agents/old_project/agent1.py', 'agents/generated_agents/new_project/agent1.py'),
        ('prompts/generated_agents_prompts/old_project/agent1.yaml', 'prompts/generated_agents_prompts/new_project/agent1.yaml'),
        ('tools/generated_tools/old_project/tool1.py', 'tools/generated_tools/new_project/tool1.py'),
    ]
    
    print("路径映射测试:")
    print()
    
    all_passed = True
    for original_path, expected_path in test_cases:
        # 模拟路径映射逻辑
        path_str = original_path
        
        if path_str.startswith(f'projects/{original_project_name}/'):
            path_str = path_str.replace(
                f'projects/{original_project_name}/',
                f'projects/{new_project_name}/',
                1
            )
        elif path_str.startswith(f'agents/generated_agents/{original_project_name}/'):
            path_str = path_str.replace(
                f'agents/generated_agents/{original_project_name}/',
                f'agents/generated_agents/{new_project_name}/',
                1
            )
        elif path_str.startswith(f'prompts/generated_agents_prompts/{original_project_name}/'):
            path_str = path_str.replace(
                f'prompts/generated_agents_prompts/{original_project_name}/',
                f'prompts/generated_agents_prompts/{new_project_name}/',
                1
            )
        elif path_str.startswith(f'tools/generated_tools/{original_project_name}/'):
            path_str = path_str.replace(
                f'tools/generated_tools/{original_project_name}/',
                f'tools/generated_tools/{new_project_name}/',
                1
            )
        
        passed = (path_str == expected_path)
        status = "✓" if passed else "✗"
        
        print(f"{status} {original_path}")
        print(f"  → {path_str}")
        if not passed:
            print(f"  预期: {expected_path}")
            all_passed = False
        print()
    
    print("=" * 70)
    if all_passed:
        print("✓ 所有路径映射测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = test_path_mapping()
    sys.exit(0 if success else 1)
