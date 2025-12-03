#!/bin/bash
# 快速测试脚本 - 验证CLI基本功能

echo "🧪 Nexus-AI CLI 快速功能测试"
echo "================================"
echo ""

# 获取脚本所在目录的父目录（Nexus-AI根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NEXUS_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$NEXUS_ROOT"

# 设置Python路径
export PYTHONPATH="$NEXUS_ROOT:$PYTHONPATH"

# CLI命令别名
CLI_CMD="python3 -c 'import sys; sys.path.insert(0, \"$NEXUS_ROOT\"); from nexus_utils.cli.main import main; main()'"

echo "📍 测试目录: $NEXUS_ROOT"
echo ""

# 测试计数器
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "[$TESTS_RUN] 测试: $test_name ... "
    
    if eval "$test_cmd" > /dev/null 2>&1; then
        echo "✅ 通过"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo "❌ 失败"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# 开始测试
echo "开始功能测试..."
echo ""

# 测试 1: --version
run_test "CLI版本显示" "$CLI_CMD --version"

# 测试 2: --help
run_test "CLI帮助信息" "$CLI_CMD --help"

# 测试 3: project list
run_test "项目列表" "$CLI_CMD project list"

# 测试 4: project list --output json
run_test "项目列表(JSON)" "$CLI_CMD project list --output json"

# 测试 5: project list --output text
run_test "项目列表(Text)" "$CLI_CMD project list --output text"

# 测试 6: agents list
run_test "Agent列表" "$CLI_CMD agents list"

# 测试 7: agents list --output json
run_test "Agent列表(JSON)" "$CLI_CMD agents list --output json"

# 测试 8: overview
run_test "系统概览" "$CLI_CMD overview"

# 测试 9: overview --output json
run_test "系统概览(JSON)" "$CLI_CMD overview --output json"

# 测试 10: project help
run_test "项目命令帮助" "$CLI_CMD project --help"

# 测试 11: agents help
run_test "Agent命令帮助" "$CLI_CMD agents --help"

# 测试 12: backup list
run_test "备份列表" "$CLI_CMD backup list"

# 测试 13: backup list --output json
run_test "备份列表(JSON)" "$CLI_CMD backup list --output json"

# 测试 14: backup help
run_test "备份命令帮助" "$CLI_CMD backup --help"

# 测试 15: 路径映射逻辑测试
run_test "路径映射逻辑" "python3 $NEXUS_ROOT/nexus_utils/cli/test_restore_logic.py"

echo ""
echo "================================"
echo "📊 测试结果汇总"
echo "================================"
echo "总测试数: $TESTS_RUN"
echo "通过: $TESTS_PASSED ✅"
echo "失败: $TESTS_FAILED ❌"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "🎉 所有测试通过！"
    exit 0
else
    echo "⚠️  有 $TESTS_FAILED 个测试失败"
    exit 1
fi
