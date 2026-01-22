#!/bin/bash
# ============================================
# LocalStack 初始化脚本
# ============================================
# 创建 Nexus-AI 所需的 AWS 资源

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# LocalStack 端点
ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
REGION="${AWS_REGION:-us-west-2}"

# 等待 LocalStack 就绪
log_info "等待 LocalStack 启动..."
until curl -s "$ENDPOINT/_localstack/health" | grep -q '"dynamodb"'; do
    sleep 2
done
log_success "LocalStack 已就绪"

# ============================================
# 创建 DynamoDB 表
# ============================================
log_info "创建 DynamoDB 表..."

# 项目表
aws --endpoint-url=$ENDPOINT dynamodb create-table \
    --table-name nexus-projects \
    --attribute-definitions \
        AttributeName=project_id,AttributeType=S \
    --key-schema \
        AttributeName=project_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION 2>/dev/null || log_info "表 nexus-projects 已存在"

# 任务表
aws --endpoint-url=$ENDPOINT dynamodb create-table \
    --table-name nexus-tasks \
    --attribute-definitions \
        AttributeName=task_id,AttributeType=S \
        AttributeName=project_id,AttributeType=S \
    --key-schema \
        AttributeName=task_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\": \"project-index\", \"KeySchema\": [{\"AttributeName\": \"project_id\", \"KeyType\": \"HASH\"}], \"Projection\": {\"ProjectionType\": \"ALL\"}}]" \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION 2>/dev/null || log_info "表 nexus-tasks 已存在"

# 会话表
aws --endpoint-url=$ENDPOINT dynamodb create-table \
    --table-name nexus-sessions \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION 2>/dev/null || log_info "表 nexus-sessions 已存在"

log_success "DynamoDB 表创建完成"

# ============================================
# 创建 SQS 队列
# ============================================
log_info "创建 SQS 队列..."

# 构建队列
aws --endpoint-url=$ENDPOINT sqs create-queue \
    --queue-name nexus-build-queue \
    --attributes VisibilityTimeout=3600 \
    --region $REGION 2>/dev/null || log_info "队列 nexus-build-queue 已存在"

# 部署队列
aws --endpoint-url=$ENDPOINT sqs create-queue \
    --queue-name nexus-deploy-queue \
    --attributes VisibilityTimeout=3600 \
    --region $REGION 2>/dev/null || log_info "队列 nexus-deploy-queue 已存在"

log_success "SQS 队列创建完成"

# ============================================
# 创建 S3 存储桶
# ============================================
log_info "创建 S3 存储桶..."

aws --endpoint-url=$ENDPOINT s3 mb s3://nexus-uploads --region $REGION 2>/dev/null || log_info "存储桶 nexus-uploads 已存在"
aws --endpoint-url=$ENDPOINT s3 mb s3://nexus-artifacts --region $REGION 2>/dev/null || log_info "存储桶 nexus-artifacts 已存在"

log_success "S3 存储桶创建完成"

# ============================================
# 验证资源
# ============================================
log_info "验证已创建的资源..."

echo ""
echo "DynamoDB 表:"
aws --endpoint-url=$ENDPOINT dynamodb list-tables --region $REGION

echo ""
echo "SQS 队列:"
aws --endpoint-url=$ENDPOINT sqs list-queues --region $REGION

echo ""
echo "S3 存储桶:"
aws --endpoint-url=$ENDPOINT s3 ls --region $REGION

log_success "LocalStack 初始化完成！"
