#!/bin/bash
# Terraform 重试脚本 - 处理网络问题

set -e

MAX_RETRIES=3
RETRY_COUNT=0
SUCCESS=false

echo "=========================================="
echo "Terraform Apply with Retry"
echo "=========================================="
echo ""

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES"
    echo "----------------------------------------"
    
    if terraform apply "$@"; then
        echo ""
        echo "✅ Terraform apply succeeded!"
        SUCCESS=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo ""
            echo "⚠️  Terraform apply failed, waiting 30 seconds before retry..."
            sleep 30
            echo ""
        fi
    fi
done

if [ "$SUCCESS" = false ]; then
    echo ""
    echo "❌ Terraform apply failed after $MAX_RETRIES attempts"
    echo ""
    echo "建议："
    echo "1. 检查网络连接"
    echo "2. 检查 AWS 凭证: aws sts get-caller-identity"
    echo "3. 尝试跳过 Docker 构建: export TF_VAR_skip_docker_build=true && terraform apply"
    exit 1
fi

