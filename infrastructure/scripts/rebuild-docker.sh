#!/bin/bash
# 重新构建并推送 Docker 镜像

set -e

echo "🚀 重新构建并推送 Docker 镜像到 ECR..."

cd "$(dirname "$0")"

# 获取 Terraform 输出
PROJECT_ROOT="$(cd .. && pwd)"
AWS_REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 获取 ECR 仓库 URL
API_REPO=$(terraform output -json ecr_repositories | jq -r '.api')
FRONTEND_REPO=$(terraform output -json ecr_repositories | jq -r '.frontend')
CELERY_REPO=$(terraform output -json ecr_repositories | jq -r '.celery_worker')

# Login to ECR
echo "🔐 登录到 ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $API_REPO

# Build and push API image
echo "📦 构建 API 镜像..."
cd $PROJECT_ROOT
# Build from project root with project root as context (not api/)
# This allows Dockerfile to access parent directories (nexus_utils, agents, tools, etc.)
docker build --no-cache --platform linux/amd64 -f api/Dockerfile -t $API_REPO:latest .
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag $API_REPO:latest $API_REPO:$TIMESTAMP
echo "📤 推送 API 镜像..."
docker push $API_REPO:latest
docker push $API_REPO:$TIMESTAMP

# Build and push Frontend image
echo "📦 构建 Frontend 镜像..."
cd $PROJECT_ROOT/web
docker build  --no-cache  --platform linux/amd64 -t $FRONTEND_REPO:latest .
docker tag $FRONTEND_REPO:latest $FRONTEND_REPO:$TIMESTAMP
echo "📤 推送 Frontend 镜像..."
docker push $FRONTEND_REPO:latest
docker push $FRONTEND_REPO:$TIMESTAMP

# Build and push Celery Worker image (reuse API image)
echo "📦 构建 Celery Worker 镜像..."
cd $PROJECT_ROOT
# Build from project root with project root as context (same as API image)
docker build --no-cache --platform linux/amd64 -f api/Dockerfile -t $CELERY_REPO:latest .
docker tag $CELERY_REPO:latest $CELERY_REPO:$TIMESTAMP
echo "📤 推送 Celery Worker 镜像..."
docker push $CELERY_REPO:latest
docker push $CELERY_REPO:$TIMESTAMP

echo "✅ 所有镜像构建并推送成功！"
echo ""
echo "下一步：强制重新部署 ECS 服务"
echo "执行以下命令："
echo ""
echo "CLUSTER_NAME=\$(terraform output -raw ecs_cluster_name)"
echo "REGION=\$(terraform output -raw region)"
echo ""
echo "for service in nexus-ai-api-prod nexus-ai-frontend-prod nexus-ai-celery-worker-builds-prod nexus-ai-celery-worker-status-prod nexus-ai-redis-prod; do"
echo "  aws ecs update-service \\"
echo "    --cluster \$CLUSTER_NAME \\"
echo "    --service \$service \\"
echo "    --force-new-deployment \\"
echo "    --region \$REGION"
echo "done"

