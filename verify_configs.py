#!/usr/bin/env python3

import os
import yaml
from pathlib import Path

def verify_yaml_configs():
    """验证所有 YAML 配置文件"""
    print("=== 验证 YAML 配置文件 ===")
    
    yaml_dir = Path("prompts/system_agents_prompts")
    agent_files = list(yaml_dir.glob("*.yaml"))
    
    expected_models = [
        "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "us.anthropic.claude-opus-4-20250514-v1:0"
    ]
    
    results = {}
    
    for yaml_file in agent_files:
        agent_name = yaml_file.stem
        print(f"\n--- 检查 {agent_name} ---")
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
            
            # 查找 metadata 部分
            metadata = None
            if 'agents' in content:
                for agent_config in content['agents'].values():
                    if 'metadata' in agent_config:
                        metadata = agent_config['metadata']
                        break
            
            if metadata:
                # 检查 supported_models
                supported_models = metadata.get('supported_models', [])
                models_ok = supported_models == expected_models
                
                # 检查 tools_dependencies
                tools_deps = metadata.get('tools_dependencies', [])
                
                results[agent_name] = {
                    'models_ok': models_ok,
                    'models': supported_models,
                    'tools_count': len(tools_deps),
                    'tools': tools_deps[:5]  # 只显示前5个
                }
                
                print(f"✅ 模型配置: {'正确' if models_ok else '错误'}")
                print(f"✅ 工具数量: {len(tools_deps)}")
                
            else:
                results[agent_name] = {'error': 'No metadata found'}
                print(f"❌ 未找到 metadata 配置")
                
        except Exception as e:
            results[agent_name] = {'error': str(e)}
            print(f"❌ 读取错误: {e}")
    
    # 总结
    print(f"\n=== 验证总结 ===")
    success_count = 0
    for agent_name, result in results.items():
        if 'error' not in result and result.get('models_ok', False):
            success_count += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"{status} {agent_name}: {result.get('tools_count', 0)} 工具")
    
    print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

if __name__ == "__main__":
    verify_yaml_configs()