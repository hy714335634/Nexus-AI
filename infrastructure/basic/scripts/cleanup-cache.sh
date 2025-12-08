#!/bin/bash
# 清理 Docker 和 Terraform 缓存，准备重新构建

set -e

echo "🧹 清理缓存文件..."

# 1. 清理 Docker 构建缓存
echo "📦 清理 Docker 构建缓存..."
docker builder prune -af --filter "until=24h" || true

# 2. 清理未使用的 Docker 镜像
echo "🗑️  清理未使用的 Docker 镜像..."
docker image prune -af --filter "until=24h" || true

# 3. 清理未使用的容器
echo "🗑️  清理未使用的容器..."
docker container prune -f || true

# 4. 清理未使用的卷
echo "🗑️  清理未使用的卷..."
docker volume prune -f || true

# 5. 清理 Terraform 的 null_resource 状态（强制重新构建）
echo "🔄 清理 Terraform null_resource 状态..."
cd "$(dirname "$0")"
if terraform state list | grep -q "null_resource.docker_build_and_push"; then
    echo "  移除 null_resource.docker_build_and_push 状态..."
    terraform state rm 'null_resource.docker_build_and_push[0]' 2>/dev/null || true
fi

# 6. 显示清理后的空间
echo ""
echo "✅ 清理完成！"
echo ""
echo "📊 Docker 系统空间使用："
docker system df

echo ""
echo "🚀 现在可以运行: terraform apply"

