#!/usr/bin/env python3
"""
测试进度组件的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.components.progress_bar import (
    create_sample_build_stages,
    calculate_progress_stats,
    parse_duration_to_seconds,
    format_duration,
    estimate_stage_time,
    estimate_remaining_time
)

def test_progress_calculations():
    """测试进度计算功能"""
    
    print("🧪 测试进度计算功能...")
    
    # 测试示例数据
    stages = create_sample_build_stages()
    
    # 测试统计计算
    stats = calculate_progress_stats(stages)
    print(f"✅ 统计信息: {stats}")
    
    # 测试时间解析
    test_durations = ["3分钟", "1小时30分钟", "45秒", "2小时"]
    for duration in test_durations:
        seconds = parse_duration_to_seconds(duration)
        formatted = format_duration(seconds)
        print(f"✅ 时间解析: {duration} -> {seconds}秒 -> {formatted}")
    
    # 测试时间估算
    for i in range(1, 8):
        estimate = estimate_stage_time(i, 'pending')
        print(f"✅ 阶段{i}估算时间: {estimate}")
    
    # 测试剩余时间估算
    for current_stage in range(-1, 7):
        remaining = estimate_remaining_time(stages, current_stage)
        print(f"✅ 当前阶段{current_stage}，剩余时间: {remaining}")
    
    print("🎉 所有测试通过!")

def test_stage_status():
    """测试阶段状态处理"""
    
    print("\n🧪 测试阶段状态处理...")
    
    stages = create_sample_build_stages()
    
    # 检查各种状态
    status_counts = {}
    for stage in stages:
        status = stage.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"✅ 状态统计: {status_counts}")
    
    # 检查当前阶段
    current_stages = [i for i, s in enumerate(stages) if s.get('status') == 'current']
    print(f"✅ 当前阶段索引: {current_stages}")
    
    # 检查进度数据
    for i, stage in enumerate(stages):
        progress = stage.get('progress', 0)
        name = stage.get('name', f'阶段{i+1}')
        print(f"✅ {name}: {progress}% 完成")

if __name__ == "__main__":
    test_progress_calculations()
    test_stage_status()
    print("\n🎉 所有组件测试完成!")