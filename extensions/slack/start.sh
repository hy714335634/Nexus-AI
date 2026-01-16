#!/bin/bash

# Nexus-AI Slack Bot 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "🤖 Nexus-AI Slack Bot 启动脚本"
echo "================================"

# 检查环境变量
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "❌ 错误: 未设置 SLACK_BOT_TOKEN"
    echo ""
    echo "请先设置环境变量:"
    echo "export SLACK_BOT_TOKEN='xoxb-your-token'"
    echo "export SLACK_APP_TOKEN='xapp-your-token'"
    echo ""
    echo "获取 Token:"
    echo "1. 访问: https://api.slack.com/apps"
    echo "2. 选择你的 App"
    echo "3. Bot Token: OAuth & Permissions 页面"
    echo "4. App Token: Socket Mode 页面"
    exit 1
fi

if [ -z "$SLACK_APP_TOKEN" ]; then
    echo "❌ 错误: 未设置 SLACK_APP_TOKEN"
    echo ""
    echo "请先设置环境变量:"
    echo "export SLACK_APP_TOKEN='xapp-your-token'"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
source .nexus-ai/bin/activate && python -c "import slack_bolt" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  未安装 slack-bolt，正在安装..."
    source .nexus-ai/bin/activate && pip install slack-bolt
fi

# 创建日志目录
mkdir -p logs

# 启动 Bot
echo "✅ 环境检查完成"
echo ""

source .nexus-ai/bin/activate && python -m extensions.slack.main
