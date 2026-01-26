#!/usr/bin/env python3
"""
修复阶段状态不一致问题

此脚本用于修复有 completed_at 时间戳但状态为 pending 的阶段记录。
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v2.database import db_client


def fix_stage_status(project_id: str, dry_run: bool = True) -> dict:
    """
    修复阶段状态不一致问题
    
    Args:
        project_id: 项目ID
        dry_run: 如果为 True，只显示将要修复的记录，不实际修复
        
    Returns:
        dict: 修复结果统计
    """
    print(f"\n{'='*60}")
    print(f"项目: {project_id}")
    print(f"模式: {'预览（不修复）' if dry_run else '实际修复'}")
    print(f"{'='*60}")
    
    # 获取所有阶段
    stages = db_client.list_stages(project_id)
    print(f"\n当前阶段数量: {len(stages)}")
    
    # 找出状态不一致的阶段
    inconsistent_stages = []
    
    for stage in stages:
        stage_name = stage.get('stage_name', '')
        status = stage.get('status', '')
        completed_at = stage.get('completed_at')
        
        # 如果有 completed_at 但状态不是 completed，则需要修复
        if completed_at and status != 'completed':
            inconsistent_stages.append(stage)
    
    print(f"状态不一致的阶段: {len(inconsistent_stages)}")
    
    # 显示并修复不一致的阶段
    fixed_count = 0
    if inconsistent_stages:
        print(f"\n状态不一致的阶段列表:")
        for stage in inconsistent_stages:
            stage_name = stage.get('stage_name', '')
            status = stage.get('status', '')
            completed_at = stage.get('completed_at', '')
            print(f"  - {stage_name}: status={status}, completed_at={completed_at}")
            print(f"    -> 将修复为 status=completed")
            
            if not dry_run:
                try:
                    db_client.update_stage(project_id, stage_name, {
                        'status': 'completed'
                    })
                    print(f"    ✓ 已修复")
                    fixed_count += 1
                except Exception as e:
                    print(f"    ✗ 修复失败: {e}")
    
    # 验证修复结果
    if not dry_run and fixed_count > 0:
        print(f"\n修复后的阶段状态:")
        stages = db_client.list_stages(project_id)
        for stage in sorted(stages, key=lambda x: x.get('stage_number', 0)):
            print(f"  - {stage.get('stage_name')}: {stage.get('status')}")
    
    return {
        'project_id': project_id,
        'total_stages': len(stages),
        'inconsistent_stages': len(inconsistent_stages),
        'fixed': fixed_count,
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='修复阶段状态不一致问题')
    parser.add_argument('project_id', help='项目ID')
    parser.add_argument('--execute', action='store_true', 
                        help='实际执行修复（默认只预览）')
    
    args = parser.parse_args()
    
    result = fix_stage_status(args.project_id, dry_run=not args.execute)
    
    print(f"\n{'='*60}")
    print("修复结果统计:")
    print(f"  总阶段数: {result['total_stages']}")
    print(f"  不一致阶段: {result['inconsistent_stages']}")
    print(f"  已修复: {result['fixed']}")
    
    if not args.execute and result['inconsistent_stages'] > 0:
        print(f"\n提示: 使用 --execute 参数实际执行修复操作")
        print(f"  python scripts/fix_stage_status.py {args.project_id} --execute")


if __name__ == '__main__':
    main()
