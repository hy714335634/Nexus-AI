#!/bin/bash
# ============================================
# 重新部署脚本 - 修复架构问题后使用
# ============================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 开始重新部署...${NC}"
echo "=========================================="

cd "$(dirname "$0")"

# Step 1: 重新构建并推送 Docker 镜像
echo -e "\n${YELLOW}步骤 1: 重新构建 Docker 镜像（使用 linux/amd64 平台）...${NC}"
terraform apply -replace=null_resource.docker_build_and_push[0] -auto-approve

# Step 2: 等待镜像推送完成
echo -e "\n${YELLOW}步骤 2: 等待镜像推送完成...${NC}"
sleep 5

# Step 3: 强制 ECS 服务重新部署
echo -e "\n${YELLOW}步骤 3: 强制 ECS 服务重新部署...${NC}"

CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "nexus-ai-cluster-prod")
REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")

SERVICES=(
  "nexus-ai-api-prod"
  "nexus-ai-frontend-prod"
  "nexus-ai-celery-worker-builds-prod"
  "nexus-ai-celery-worker-status-prod"
)

for SERVICE in "${SERVICES[@]}"; do
  echo -e "${GREEN}  更新服务: ${SERVICE}...${NC}"
  aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service "$SERVICE" \
    --force-new-deployment \
    --region "$REGION" \
    --output text > /dev/null || echo "  ⚠️  服务 $SERVICE 可能不存在或已更新"
done

echo -e "\n${GREEN}✅ 重新部署完成！${NC}"
echo -e "${YELLOW}💡 等待 2-3 分钟后，服务应该会正常运行。${NC}"
echo -e "${YELLOW}💡 使用以下命令检查服务状态：${NC}"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services ${SERVICES[0]} ${SERVICES[1]} --region $REGION --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount}' --output table"

