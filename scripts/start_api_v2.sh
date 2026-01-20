#!/bin/bash
# Nexus AI API v2 启动脚本

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

echo "Starting Nexus AI API v2..."
echo "AWS Region: $AWS_REGION"
echo "Log Level: $LOG_LEVEL"

# 启动 API 服务
uvicorn api.v2.main:app --host 0.0.0.0 --port 8000 --reload
