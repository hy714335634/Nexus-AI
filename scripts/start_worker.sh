#!/bin/bash
# Nexus AI Worker 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 检查虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 设置环境变量（可选）
export AWS_REGION="${AWS_REGION:-us-west-2}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# 队列类型，默认 build
QUEUE_TYPE="${1:-build}"

echo "Starting Nexus AI Worker..."
echo "Queue Type: $QUEUE_TYPE"
echo "AWS Region: $AWS_REGION"
echo "Log Level: $LOG_LEVEL"

# 启动 Worker 服务
python -m worker.main --queue "$QUEUE_TYPE"
