#!/bin/bash
# ============================================
# 检查服务状态脚本
# ============================================

cd "$(dirname "$0")"

CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "nexus-ai-cluster-prod")
REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")

echo "📊 ECS 服务状态"
echo "=========================================="

aws ecs describe-services \
  --cluster "$CLUSTER_NAME" \
  --services nexus-ai-api-prod nexus-ai-frontend-prod nexus-ai-celery-worker-builds-prod nexus-ai-celery-worker-status-prod nexus-ai-redis-prod \
  --region "$REGION" \
  --query 'services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
  --output table

echo ""
echo "🌐 ALB 访问地址:"
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "未找到")
echo "   http://$ALB_DNS"

