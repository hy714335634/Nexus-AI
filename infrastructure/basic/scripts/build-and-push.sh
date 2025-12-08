#!/bin/bash
# ============================================
# Build and push Docker images to ECR
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get variables from Terraform
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infrastructure"

echo -e "${GREEN}🚀 Building and pushing Docker images to ECR${NC}"
echo "=========================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Get AWS region and account ID
AWS_REGION=$(cd "${INFRA_DIR}" && terraform output -raw region 2>/dev/null || echo "us-east-1")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}📍 AWS Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}📍 AWS Account: ${AWS_ACCOUNT_ID}${NC}"

# Login to ECR
echo -e "\n${GREEN}🔐 Logging in to ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get ECR repository URLs
API_REPO=$(cd "${INFRA_DIR}" && terraform output -json ecr_repositories 2>/dev/null | jq -r '.api' || echo "")
FRONTEND_REPO=$(cd "${INFRA_DIR}" && terraform output -json ecr_repositories 2>/dev/null | jq -r '.frontend' || echo "")
CELERY_REPO=$(cd "${INFRA_DIR}" && terraform output -json ecr_repositories 2>/dev/null | jq -r '.celery_worker' || echo "")

if [ -z "$API_REPO" ] || [ -z "$FRONTEND_REPO" ] || [ -z "$CELERY_REPO" ]; then
    echo -e "${RED}❌ Could not get ECR repository URLs. Make sure Terraform has been applied.${NC}"
    exit 1
fi

# Build and push API image
echo -e "\n${GREEN}📦 Building API image...${NC}"
cd "${PROJECT_ROOT}/api"
# Build for linux/amd64 platform (required for AWS ECS Fargate)
docker build --platform linux/amd64 -t "${API_REPO}:latest" .
docker tag "${API_REPO}:latest" "${API_REPO}:$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}📤 Pushing API image...${NC}"
docker push "${API_REPO}:latest"
docker push "${API_REPO}:$(date +%Y%m%d-%H%M%S)"

# Build and push Frontend image
echo -e "\n${GREEN}📦 Building Frontend image...${NC}"
cd "${PROJECT_ROOT}/web"
# Build for linux/amd64 platform (required for AWS ECS Fargate)
docker build --platform linux/amd64 -t "${FRONTEND_REPO}:latest" .
docker tag "${FRONTEND_REPO}:latest" "${FRONTEND_REPO}:$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}📤 Pushing Frontend image...${NC}"
docker push "${FRONTEND_REPO}:latest"
docker push "${FRONTEND_REPO}:$(date +%Y%m%d-%H%M%S)"

# Build and push Celery Worker image (reuse API image)
echo -e "\n${GREEN}📦 Building Celery Worker image...${NC}"
cd "${PROJECT_ROOT}/api"
# Build for linux/amd64 platform (required for AWS ECS Fargate)
docker build --platform linux/amd64 -t "${CELERY_REPO}:latest" .
docker tag "${CELERY_REPO}:latest" "${CELERY_REPO}:$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}📤 Pushing Celery Worker image...${NC}"
docker push "${CELERY_REPO}:latest"
docker push "${CELERY_REPO}:$(date +%Y%m%d-%H%M%S)"

echo -e "\n${GREEN}✅ All images built and pushed successfully!${NC}"
echo -e "${YELLOW}💡 To update ECS services, run:${NC}"
echo "   aws ecs update-service --cluster <cluster-name> --service <service-name> --force-new-deployment"

