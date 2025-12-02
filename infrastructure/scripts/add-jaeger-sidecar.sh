#!/bin/bash
# ============================================
# 添加Jaeger Sidecar容器到API Task Definition
# ============================================

set -e

cd "$(dirname "$0")/.."

echo "🔧 添加Jaeger Sidecar容器"
echo "=========================================="
echo ""

# 获取配置
REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")
PROJECT_NAME=$(grep -E "^project_name\s*=" terraform.tfvars 2>/dev/null | sed -E 's/^[^=]*=\s*["'\'']?([^"'\'']+)["'\'']?/\1/' | tr -d ' ' || echo "nexus-ai")
ENVIRONMENT=$(grep -E "^environment\s*=" terraform.tfvars 2>/dev/null | sed -E 's/^[^=]*=\s*["'\'']?([^"'\'']+)["'\'']?/\1/' | tr -d ' ' || echo "prod")
TASK_DEF_NAME="${PROJECT_NAME}-api-${ENVIRONMENT}"
CLUSTER_NAME="${PROJECT_NAME}-cluster-${ENVIRONMENT}"
SERVICE_NAME="${PROJECT_NAME}-api-${ENVIRONMENT}"
LOG_GROUP="/ecs/${PROJECT_NAME}-api-${ENVIRONMENT}"

echo "📋 配置信息"
echo "  区域: $REGION"
echo "  任务定义: $TASK_DEF_NAME"
echo "  集群: $CLUSTER_NAME"
echo "  服务: $SERVICE_NAME"
echo "  日志组: $LOG_GROUP"
echo ""

# 检查jq是否安装
if ! command -v jq &> /dev/null; then
    echo "❌ 错误: 需要安装 jq"
    echo "   macOS: brew install jq"
    echo "   Linux: sudo apt-get install jq 或 sudo yum install jq"
    exit 1
fi

# 检查是否启用Jaeger
ENABLE_JAEGER=$(grep -E "^enable_jaeger\s*=" terraform.tfvars 2>/dev/null | grep -oE "(true|false)" || echo "false")

if [ "$ENABLE_JAEGER" != "true" ]; then
    echo "⚠️  警告: enable_jaeger 在 terraform.tfvars 中未设置为 true"
    echo ""
    read -p "是否继续添加Jaeger容器？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. 获取当前Task Definition
echo "1️⃣  获取当前Task Definition..."
TEMP_DIR=$(mktemp -d)
CURRENT_TASK_DEF="${TEMP_DIR}/current-task-def.json"
NEW_TASK_DEF="${TEMP_DIR}/new-task-def.json"
TASK_DEF_INPUT="${TEMP_DIR}/task-def-input.json"

aws ecs describe-task-definition \
  --task-definition "$TASK_DEF_NAME" \
  --region "$REGION" \
  --query 'taskDefinition' > "$CURRENT_TASK_DEF" 2>/dev/null || {
    echo "❌ 错误: 无法获取Task Definition '$TASK_DEF_NAME'"
    echo "   请确保Task Definition已存在"
    exit 1
}

echo "  ✅ Task Definition获取成功"
echo ""

# 2. 检查是否已有Jaeger容器
echo "2️⃣  检查是否已有Jaeger容器..."
HAS_JAEGER=$(jq -r '.containerDefinitions[] | select(.name == "jaeger") | .name' "$CURRENT_TASK_DEF" 2>/dev/null || echo "")

if [ -n "$HAS_JAEGER" ]; then
    echo "  ✅ Jaeger容器已存在"
    echo ""
    read -p "是否要重新添加Jaeger容器（将更新配置）？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        rm -rf "$TEMP_DIR"
        exit 0
    fi
    
    # 移除现有的Jaeger容器
    echo "  移除现有的Jaeger容器..."
    jq 'del(.containerDefinitions[] | select(.name == "jaeger"))' "$CURRENT_TASK_DEF" > "${TEMP_DIR}/temp.json"
    mv "${TEMP_DIR}/temp.json" "$CURRENT_TASK_DEF"
fi

# 3. 添加Jaeger容器定义
echo "3️⃣  添加Jaeger容器定义..."

JAEGER_CONTAINER=$(cat <<EOF
{
  "name": "jaeger",
  "image": "jaegertracing/all-in-one:latest",
  "essential": false,
  "portMappings": [
    {
      "containerPort": 16686,
      "protocol": "tcp"
    },
    {
      "containerPort": 4317,
      "protocol": "tcp"
    },
    {
      "containerPort": 4318,
      "protocol": "tcp"
    }
  ],
  "environment": [
    {
      "name": "COLLECTOR_ZIPKIN_HOST_PORT",
      "value": ":9411"
    },
    {
      "name": "COLLECTOR_OTLP_ENABLED",
      "value": "true"
    }
  ],
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "${LOG_GROUP}",
      "awslogs-region": "${REGION}",
      "awslogs-stream-prefix": "jaeger"
    }
  }
}
EOF
)

# 添加Jaeger容器到containerDefinitions数组
jq --argjson jaeger "$JAEGER_CONTAINER" '.containerDefinitions += [$jaeger]' "$CURRENT_TASK_DEF" > "$NEW_TASK_DEF"

echo "  ✅ Jaeger容器定义已添加"
echo ""

# 4. 准备Task Definition输入（移除只读字段）
echo "4️⃣  准备Task Definition输入..."
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' "$NEW_TASK_DEF" > "$TASK_DEF_INPUT"

echo "  ✅ 准备完成"
echo ""

# 5. 注册新Task Definition
echo "5️⃣  注册新Task Definition版本..."
NEW_REVISION=$(aws ecs register-task-definition \
  --cli-input-json "file://${TASK_DEF_INPUT}" \
  --region "$REGION" \
  --query 'taskDefinition.revision' \
  --output text 2>/dev/null || echo "")

if [ -z "$NEW_REVISION" ]; then
    echo "  ❌ 错误: 注册Task Definition失败"
    echo ""
    echo "  查看详细错误信息:"
    aws ecs register-task-definition \
      --cli-input-json "file://${TASK_DEF_INPUT}" \
      --region "$REGION" 2>&1 | head -20
    rm -rf "$TEMP_DIR"
    exit 1
fi

NEW_TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition "${TASK_DEF_NAME}:${NEW_REVISION}" \
  --region "$REGION" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "  ✅ 新Task Definition已注册"
echo "  版本: ${NEW_REVISION}"
echo "  ARN: ${NEW_TASK_DEF_ARN}"
echo ""

# 6. 更新ECS Service
echo "6️⃣  更新ECS Service..."
UPDATE_OUTPUT=$(aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --task-definition "${TASK_DEF_NAME}:${NEW_REVISION}" \
  --force-new-deployment \
  --region "$REGION" \
  --query 'service.{Name:serviceName,Status:status,TaskDefinition:taskDefinition,RunningCount:runningCount,DesiredCount:desiredCount}' \
  --output json 2>&1)

if [ $? -eq 0 ]; then
    echo "  ✅ 服务更新成功"
    echo ""
    echo "$UPDATE_OUTPUT" | jq '.'
else
    echo "  ⚠️  服务更新可能失败，请检查输出:"
    echo "$UPDATE_OUTPUT"
fi
echo ""

# 清理临时文件
rm -rf "$TEMP_DIR"

echo "=========================================="
echo "✅ Jaeger Sidecar容器添加完成！"
echo ""
echo "📋 后续步骤："
echo ""
echo "1. 等待ECS服务部署新任务（通常需要1-2分钟）"
echo ""
echo "2. 检查任务状态："
echo "   aws ecs describe-services \\"
echo "     --cluster $CLUSTER_NAME \\"
echo "     --services $SERVICE_NAME \\"
echo "     --region $REGION \\"
echo "     --query 'services[0].{Running:runningCount,Desired:desiredCount,Events:events[0:3]}'"
echo ""
echo "3. 验证Jaeger容器运行："
echo "   TASK_ARN=\$(aws ecs list-tasks \\"
echo "     --cluster $CLUSTER_NAME \\"
echo "     --service-name $SERVICE_NAME \\"
echo "     --region $REGION \\"
echo "     --query 'taskArns[0]' --output text)"
echo ""
echo "   aws ecs describe-tasks \\"
echo "     --cluster $CLUSTER_NAME \\"
echo "     --tasks \$TASK_ARN \\"
echo "     --region $REGION \\"
echo "     --query 'tasks[0].containers[?name==\`jaeger\`]'"
echo ""
echo "4. 访问Jaeger UI："
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "<alb-dns-name>")
echo "   http://${ALB_DNS}/jaeger/"
echo ""
echo "5. 查看Jaeger日志："
echo "   aws logs tail $LOG_GROUP --filter-pattern 'jaeger' --follow --region $REGION"
echo ""

