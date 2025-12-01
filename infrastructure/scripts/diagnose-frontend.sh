#!/bin/bash
# 诊断前端容器重启循环问题

set -e

echo "🔍 诊断前端容器重启循环问题..."
echo ""

cd "$(dirname "$0")/.."

# 获取配置
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
FRONTEND_SERVICE=$(terraform output -raw frontend_service_name 2>/dev/null || echo "")
AWS_REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")
LOG_GROUP="/ecs/nexus-ai-frontend-$(terraform output -raw environment 2>/dev/null || echo 'prod')"

if [ -z "$CLUSTER_NAME" ] || [ -z "$FRONTEND_SERVICE" ]; then
    echo "❌ 无法获取集群或服务名称，请确保 Terraform 已正确初始化"
    exit 1
fi

echo "📋 基本信息:"
echo "  - 集群: $CLUSTER_NAME"
echo "  - 服务: $FRONTEND_SERVICE"
echo "  - 区域: $AWS_REGION"
echo "  - 日志组: $LOG_GROUP"
echo ""

# 1. 检查服务状态
echo "1️⃣ 检查 ECS 服务状态..."
aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$FRONTEND_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].[desiredCount,runningCount,deployments[0].status,deployments[0].failedTasks]' \
    --output table

echo ""

# 2. 获取最近失败的任务
echo "2️⃣ 查找最近停止的任务..."
STOPPED_TASKS=$(aws ecs list-tasks \
    --cluster "$CLUSTER_NAME" \
    --service-name "$FRONTEND_SERVICE" \
    --desired-status STOPPED \
    --region "$AWS_REGION" \
    --max-items 5 \
    --query 'taskArns[]' \
    --output text)

if [ -n "$STOPPED_TASKS" ]; then
    echo "发现停止的任务，获取详细信息..."
    for TASK_ARN in $STOPPED_TASKS; do
        echo ""
        echo "任务: $TASK_ARN"
        aws ecs describe-tasks \
            --cluster "$CLUSTER_NAME" \
            --tasks "$TASK_ARN" \
            --region "$AWS_REGION" \
            --query 'tasks[0].[lastStatus,stoppedReason,stopCode,containers[0].exitCode,containers[0].reason]' \
            --output table
    done
else
    echo "✅ 没有找到最近停止的任务"
fi

echo ""

# 3. 获取运行中的任务
echo "3️⃣ 检查运行中的任务..."
RUNNING_TASKS=$(aws ecs list-tasks \
    --cluster "$CLUSTER_NAME" \
    --service-name "$FRONTEND_SERVICE" \
    --desired-status RUNNING \
    --region "$AWS_REGION" \
    --query 'taskArns[]' \
    --output text)

if [ -n "$RUNNING_TASKS" ]; then
    echo "运行中的任务:"
    for TASK_ARN in $RUNNING_TASKS; do
        echo "  - $TASK_ARN"
        aws ecs describe-tasks \
            --cluster "$CLUSTER_NAME" \
            --tasks "$TASK_ARN" \
            --region "$AWS_REGION" \
            --query 'tasks[0].[lastStatus,healthStatus,containers[0].healthStatus,containers[0].lastStatus]' \
            --output table
    done
else
    echo "⚠️  没有运行中的任务"
fi

echo ""

# 4. 检查最近的日志（如果有停止的任务）
if [ -n "$STOPPED_TASKS" ]; then
    echo "4️⃣ 获取最近停止任务的日志..."
    FIRST_STOPPED_TASK=$(echo "$STOPPED_TASKS" | head -1)
    TASK_ID=$(basename "$FIRST_STOPPED_TASK")
    
    echo "任务 ID: $TASK_ID"
    echo "获取最后 50 行日志..."
    aws logs tail "$LOG_GROUP" \
        --region "$AWS_REGION" \
        --filter-pattern "$TASK_ID" \
        --format short \
        --since 1h 2>/dev/null | tail -50 || echo "无法获取日志"
fi

echo ""

# 5. 检查目标组健康状态
echo "5️⃣ 检查目标组健康状态..."
ALB_ARN=$(terraform output -raw alb_arn 2>/dev/null || echo "")
if [ -n "$ALB_ARN" ]; then
    TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
        --load-balancer-arn "$ALB_ARN" \
        --region "$AWS_REGION" \
        --query 'TargetGroups[?contains(TargetGroupName, `frontend`)].TargetGroupArn' \
        --output text | head -1)
    
    if [ -n "$TARGET_GROUP_ARN" ]; then
        echo "目标组: $TARGET_GROUP_ARN"
        aws elbv2 describe-target-health \
            --target-group-arn "$TARGET_GROUP_ARN" \
            --region "$AWS_REGION" \
            --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Reason]' \
            --output table
    fi
fi

echo ""
echo "✅ 诊断完成！"
echo ""
echo "💡 建议检查:"
echo "  1. 查看 CloudWatch 日志: aws logs tail $LOG_GROUP --follow --region $AWS_REGION"
echo "  2. 检查任务定义中的资源限制和健康检查配置"
echo "  3. 验证 EFS 挂载是否正常"
echo "  4. 检查目标组健康检查配置是否合理"

