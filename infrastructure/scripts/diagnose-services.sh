#!/bin/bash
# 诊断服务状态脚本

set -e

echo "🔍 诊断 Nexus-AI 服务状态..."
echo ""

cd "$(dirname "$0")/.."

# 获取配置
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
AWS_REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")

if [ -z "$CLUSTER_NAME" ]; then
    echo "❌ 无法获取集群名称，请确保 Terraform 已正确初始化"
    exit 1
fi

echo "📋 基本信息:"
echo "  - 集群: $CLUSTER_NAME"
echo "  - 区域: $AWS_REGION"
echo ""

# 1. 检查所有 ECS 服务状态
echo "1️⃣ 检查 ECS 服务状态..."
echo ""
SERVICES=(
    "nexus-ai-api-prod"
    "nexus-ai-frontend-prod"
    "nexus-ai-redis-prod"
    "nexus-ai-celery-worker-builds-prod"
    "nexus-ai-celery-worker-status-prod"
)

for SERVICE in "${SERVICES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 服务: $SERVICE"
    
    SERVICE_INFO=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].{Desired:desiredCount,Running:runningCount,Pending:pendingCount,Status:status,Deployments:deployments[*].{Status:status,Running:runningCount,Desired:desiredCount,Failed:failedTasks}}' \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$SERVICE_INFO" = "{}" ]; then
        echo "  ⚠️  服务不存在或无法访问"
        continue
    fi
    
    echo "$SERVICE_INFO" | jq -r '
        "  - 期望数量: \(.Desired // 0)",
        "  - 运行中: \(.Running // 0)",
        "  - 等待中: \(.Pending // 0)",
        "  - 状态: \(.Status // "unknown")"
    ' 2>/dev/null || echo "  ⚠️  无法解析服务信息"
    
    echo ""
done

# 2. 检查 ALB 目标组健康状态
echo ""
echo "2️⃣ 检查 ALB 目标组健康状态..."
echo ""

# 获取目标组 ARN
TG_ARN_API=$(aws elbv2 describe-target-groups \
    --region "$AWS_REGION" \
    --query "TargetGroups[?contains(TargetGroupName, 'api')].TargetGroupArn" \
    --output text 2>/dev/null | head -1)

TG_ARN_FRONTEND=$(aws elbv2 describe-target-groups \
    --region "$AWS_REGION" \
    --query "TargetGroups[?contains(TargetGroupName, 'frontend')].TargetGroupArn" \
    --output text 2>/dev/null | head -1)

if [ -n "$TG_ARN_API" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 API 目标组健康状态:"
    aws elbv2 describe-target-health \
        --target-group-arn "$TG_ARN_API" \
        --region "$AWS_REGION" \
        --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason,Description:TargetHealth.Description}' \
        --output table 2>/dev/null || echo "  ⚠️  无法获取目标组健康状态"
    echo ""
fi

if [ -n "$TG_ARN_FRONTEND" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Frontend 目标组健康状态:"
    aws elbv2 describe-target-health \
        --target-group-arn "$TG_ARN_FRONTEND" \
        --region "$AWS_REGION" \
        --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason,Description:TargetHealth.Description}' \
        --output table 2>/dev/null || echo "  ⚠️  无法获取目标组健康状态"
    echo ""
fi

# 3. 检查最近停止的任务
echo ""
echo "3️⃣ 检查最近停止的任务（前 5 个）..."
echo ""

for SERVICE in "${SERVICES[@]}"; do
    STOPPED_TASKS=$(aws ecs list-tasks \
        --cluster "$CLUSTER_NAME" \
        --service-name "$SERVICE" \
        --desired-status STOPPED \
        --region "$AWS_REGION" \
        --max-items 3 \
        --query 'taskArns[]' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$STOPPED_TASKS" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🛑 $SERVICE - 最近停止的任务:"
        for TASK_ARN in $STOPPED_TASKS; do
            TASK_ID=$(echo "$TASK_ARN" | cut -d'/' -f3)
            echo ""
            echo "  任务 ID: $TASK_ID"
            aws ecs describe-tasks \
                --cluster "$CLUSTER_NAME" \
                --tasks "$TASK_ARN" \
                --region "$AWS_REGION" \
                --query 'tasks[0].{LastStatus:lastStatus,StoppedReason:stoppedReason,StopCode:stopCode,Containers:containers[0].{ExitCode:exitCode,Reason:reason}}' \
                --output table 2>/dev/null || echo "    ⚠️  无法获取任务信息"
        done
        echo ""
    fi
done

# 4. 检查 DynamoDB 表
echo ""
echo "4️⃣ 检查 DynamoDB 表状态..."
echo ""

DYNAMODB_TABLES=(
    "AgentProjects"
    "AgentInstances"
    "AgentInvocations"
    "AgentSessions"
    "AgentSessionMessages"
)

for TABLE_NAME in "${DYNAMODB_TABLES[@]}"; do
    TABLE_INFO=$(aws dynamodb describe-table \
        --table-name "$TABLE_NAME" \
        --region "$AWS_REGION" \
        --query 'Table.{Name:TableName,Status:TableStatus,ItemCount:ItemCount}' \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$TABLE_INFO" != "{}" ]; then
        echo "$TABLE_INFO" | jq -r '"  ✅ \(.Name // "unknown"): \(.Status // "unknown") (\(.ItemCount // 0) items)"' 2>/dev/null
    else
        echo "  ❌ $TABLE_NAME: 表不存在或无法访问"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 诊断完成！"
echo ""
echo "💡 提示:"
echo "  - 查看服务日志: aws logs tail /ecs/<service-name> --follow"
echo "  - 重新部署服务: ./redeploy.sh <service-name>"
echo "  - 查看完整日志: 访问 CloudWatch Logs"

