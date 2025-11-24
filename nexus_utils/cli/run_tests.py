#!/usr/bin/env python3
"""
运行所有CLI测试的脚本
"""

import sys
import os
import unittest

# 添加Nexus-AI根目录到Python路径
NEXUS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, NEXUS_ROOT)

def run_all_tests():
    """运行所有测试"""
    # 发现并运行所有测试
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回退出码
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_name):
    """运行特定的测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{test_name}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 运行特定测试
        test_name = sys.argv[1]
        print(f"运行测试: {test_name}")
        exit_code = run_specific_test(test_name)
    else:
        # 运行所有测试
        print("运行所有CLI测试...")
        print("=" * 70)
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
