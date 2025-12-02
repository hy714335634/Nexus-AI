#!/bin/bash
# 排查 agent_designer 卡住的问题

echo "=== Agent Designer 排查脚本 ==="
echo ""

# 1. 检查 API 容器状态
echo "1️⃣ 检查 API 容器状态..."
docker ps -a | grep nexus-ai-api
echo ""

# 2. 查看最近的日志
echo "2️⃣ 查看 API 容器最近日志（最后 50 行）..."
docker logs --tail 50 nexus-ai-api
echo ""

# 3. 检查容器内进程
echo "3️⃣ 检查容器内运行的进程..."
docker exec nexus-ai-api ps aux | grep -E "python|uvicorn|celery"
echo ""

# 4. 检查是否有僵尸进程
echo "4️⃣ 检查僵尸进程..."
docker exec nexus-ai-api ps aux | grep defunct
echo ""

# 5. 检查内存使用
echo "5️⃣ 检查容器资源使用..."
docker stats nexus-ai-api --no-stream
echo ""

# 6. 检查 EFS 挂载
echo "6️⃣ 检查 EFS 挂载状态..."
df -h | grep efs
echo ""

# 7. 查看 stage tracker 状态
echo "7️⃣ 查看最近的项目状态（需要 AWS CLI）..."
if command -v aws &> /dev/null; then
    echo "请输入 project_id 或按 Enter 跳过："
    read -r PROJECT_ID
    if [ -n "$PROJECT_ID" ]; then
        aws dynamodb get-item \
            --table-name nexus-ai-agent-projects-prod \
            --key "{\"project_id\": {\"S\": \"$PROJECT_ID\"}}" \
            --query 'Item.current_stage' \
            --output json
    fi
fi
echo ""

# 8. 进入容器进行交互式排查
echo "8️⃣ 是否进入容器进行交互式排查？(y/n)"
read -r ENTER_CONTAINER
if [ "$ENTER_CONTAINER" = "y" ]; then
    echo "进入容器..."
    docker exec -it nexus-ai-api bash
fi
