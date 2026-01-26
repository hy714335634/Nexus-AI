#!/usr/bin/env python3
"""
清理项目中的重复阶段记录

此脚本用于清理由于阶段命名不一致导致的重复记录。
删除使用旧命名方式（如 requirements_analyzer）的阶段记录，
保留使用新命名方式（如 requirements_analysis）的记录。
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v2.database import db_client
from api.v2.models.schemas import BuildStage

# 旧命名到新命名的映射
OLD_TO_NEW_MAPPING = {
    "requirements_analyzer": "requirements_analysis",
    "system_architect": "system_architecture",
    "agent_designer": "agent_design",
    "tool_developer": "tools_developer",
}

# 有效的阶段名称（BuildStage 枚举值）
VALID_STAGE_NAMES = {stage.value for stage in BuildStage}


def cleanup_duplicate_stages(project_id: str, dry_run: bool = True) -> dict:
    """
    清理项目中的重复阶段记录
    
    Args:
        project_id: 项目ID
        dry_run: 如果为 True，只显示将要删除的记录，不实际删除
        
    Returns:
        dict: 清理结果统计
    """
    print(f"\n{'='*60}")
    print(f"项目: {project_id}")
    print(f"模式: {'预览（不删除）' if dry_run else '实际删除'}")
    print(f"{'='*60}")
    
    # 获取所有阶段
    stages = db_client.list_stages(project_id)
    print(f"\n当前阶段数量: {len(stages)}")
    
    # 分类阶段
    valid_stages = []
    invalid_stages = []
    
    for stage in stages:
        stage_name = stage.get('stage_name', '')
        if stage_name in VALID_STAGE_NAMES:
            valid_stages.append(stage)
        else:
            invalid_stages.append(stage)
    
    print(f"有效阶段: {len(valid_stages)}")
    print(f"无效阶段（将被删除）: {len(invalid_stages)}")
    
    # 显示有效阶段
    print(f"\n有效阶段列表:")
    for stage in sorted(valid_stages, key=lambda x: x.get('stage_number', 0)):
        print(f"  - {stage.get('stage_name')}: {stage.get('status')} "
              f"(stage_number: {stage.get('stage_number', 'N/A')})")
    
    # 显示并删除无效阶段
    if invalid_stages:
        print(f"\n无效阶段列表（将被删除）:")
        for stage in invalid_stages:
            stage_name = stage.get('stage_name', '')
            status = stage.get('status', 'unknown')
            new_name = OLD_TO_NEW_MAPPING.get(stage_name, 'unknown')
            print(f"  - {stage_name}: {status} -> 应该是 {new_name}")
            
            if not dry_run:
                try:
                    db_client.delete_stage(project_id, stage_name)
                    print(f"    ✓ 已删除")
                except Exception as e:
                    print(f"    ✗ 删除失败: {e}")
    
    # 验证清理结果
    if not dry_run:
        remaining_stages = db_client.list_stages(project_id)
        print(f"\n清理后阶段数量: {len(remaining_stages)}")
    
    return {
        'project_id': project_id,
        'total_stages': len(stages),
        'valid_stages': len(valid_stages),
        'invalid_stages': len(invalid_stages),
        'deleted': 0 if dry_run else len(invalid_stages),
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='清理项目中的重复阶段记录')
    parser.add_argument('project_id', help='项目ID')
    parser.add_argument('--execute', action='store_true', 
                        help='实际执行删除（默认只预览）')
    
    args = parser.parse_args()
    
    result = cleanup_duplicate_stages(args.project_id, dry_run=not args.execute)
    
    print(f"\n{'='*60}")
    print("清理结果统计:")
    print(f"  总阶段数: {result['total_stages']}")
    print(f"  有效阶段: {result['valid_stages']}")
    print(f"  无效阶段: {result['invalid_stages']}")
    print(f"  已删除: {result['deleted']}")
    
    if not args.execute and result['invalid_stages'] > 0:
        print(f"\n提示: 使用 --execute 参数实际执行删除操作")
        print(f"  python scripts/cleanup_duplicate_stages.py {args.project_id} --execute")


if __name__ == '__main__':
    main()
