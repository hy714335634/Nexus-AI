#!/bin/bash
# ============================================
# Nexus-AI 镜像构建脚本
# ============================================
# 用法:
#   ./build.sh              # 构建所有镜像
#   ./build.sh base         # 只构建基础镜像
#   ./build.sh api          # 只构建 API 镜像
#   ./build.sh worker       # 只构建 Worker 镜像
#   ./build.sh web          # 只构建 Web 镜像
#   ./build.sh --push       # 构建并推送到 ECR

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$SCRIPT_DIR"

# 默认配置
REGISTRY="${ECR_REGISTRY:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PLATFORM="${PLATFORM:-linux/amd64}"

# 镜像名称
BASE_IMAGE="nexus-base"
API_IMAGE="nexus-api"
WORKER_IMAGE="nexus-worker"
WEB_IMAGE="nexus-web"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    echo "Nexus-AI 镜像构建脚本"
    echo ""
    echo "用法: $0 [选项] [服务...]"
    echo ""
    echo "服务:"
    echo "  base      构建基础镜像"
    echo "  api       构建 API 服务镜像"
    echo "  worker    构建 Worker 服务镜像"
    echo "  web       构建 Web 前端镜像"
    echo "  all       构建所有镜像 (默认)"
    echo ""
    echo "选项:"
    echo "  --push    构建后推送到 ECR"
    echo "  --no-cache 不使用缓存构建"
    echo "  --help    显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  ECR_REGISTRY  ECR 仓库地址"
    echo "  IMAGE_TAG     镜像标签 (默认: latest)"
    echo "  PLATFORM      目标平台 (默认: linux/amd64)"
}

# 构建基础镜像
build_base() {
    log_info "构建基础镜像: $BASE_IMAGE"
    
    docker build \
        --platform "$PLATFORM" \
        -f "$DOCKER_DIR/base/Dockerfile" \
        -t "$BASE_IMAGE:$IMAGE_TAG" \
        -t "$BASE_IMAGE:$TIMESTAMP" \
        $BUILD_ARGS \
        "$PROJECT_ROOT"
    
    log_success "基础镜像构建完成: $BASE_IMAGE:$IMAGE_TAG"
}

# 构建 API 镜像
build_api() {
    log_info "构建 API 镜像: $API_IMAGE"
    
    # 确保基础镜像存在
    if ! docker image inspect "$BASE_IMAGE:$IMAGE_TAG" &> /dev/null; then
        log_warn "基础镜像不存在，先构建基础镜像..."
        build_base
    fi
    
    docker build \
        --platform "$PLATFORM" \
        -f "$DOCKER_DIR/api/Dockerfile" \
        -t "$API_IMAGE:$IMAGE_TAG" \
        -t "$API_IMAGE:$TIMESTAMP" \
        $BUILD_ARGS \
        "$PROJECT_ROOT"
    
    log_success "API 镜像构建完成: $API_IMAGE:$IMAGE_TAG"
}

# 构建 Worker 镜像
build_worker() {
    log_info "构建 Worker 镜像: $WORKER_IMAGE"
    
    # 确保基础镜像存在
    if ! docker image inspect "$BASE_IMAGE:$IMAGE_TAG" &> /dev/null; then
        log_warn "基础镜像不存在，先构建基础镜像..."
        build_base
    fi
    
    docker build \
        --platform "$PLATFORM" \
        -f "$DOCKER_DIR/worker/Dockerfile" \
        -t "$WORKER_IMAGE:$IMAGE_TAG" \
        -t "$WORKER_IMAGE:$TIMESTAMP" \
        $BUILD_ARGS \
        "$PROJECT_ROOT"
    
    log_success "Worker 镜像构建完成: $WORKER_IMAGE:$IMAGE_TAG"
}

# 构建 Web 镜像
build_web() {
    log_info "构建 Web 镜像: $WEB_IMAGE"
    
    docker build \
        --platform "$PLATFORM" \
        -f "$PROJECT_ROOT/web/Dockerfile" \
        -t "$WEB_IMAGE:$IMAGE_TAG" \
        -t "$WEB_IMAGE:$TIMESTAMP" \
        $BUILD_ARGS \
        "$PROJECT_ROOT/web"
    
    log_success "Web 镜像构建完成: $WEB_IMAGE:$IMAGE_TAG"
}

# 推送镜像到 ECR
push_image() {
    local image_name=$1
    
    if [ -z "$REGISTRY" ]; then
        log_error "ECR_REGISTRY 环境变量未设置"
        exit 1
    fi
    
    log_info "推送镜像: $image_name -> $REGISTRY/$image_name"
    
    # 标记镜像
    docker tag "$image_name:$IMAGE_TAG" "$REGISTRY/$image_name:$IMAGE_TAG"
    docker tag "$image_name:$IMAGE_TAG" "$REGISTRY/$image_name:$TIMESTAMP"
    
    # 推送镜像（带重试）
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        if docker push "$REGISTRY/$image_name:$IMAGE_TAG" && \
           docker push "$REGISTRY/$image_name:$TIMESTAMP"; then
            log_success "镜像推送成功: $REGISTRY/$image_name"
            return 0
        else
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                log_warn "推送失败，重试 ($retry/$max_retries)..."
                sleep 10
            fi
        fi
    done
    
    log_error "镜像推送失败: $image_name"
    return 1
}

# ECR 登录
ecr_login() {
    if [ -z "$REGISTRY" ]; then
        log_warn "ECR_REGISTRY 未设置，跳过 ECR 登录"
        return 0
    fi
    
    log_info "登录 ECR: $REGISTRY"
    
    local region=$(echo "$REGISTRY" | cut -d'.' -f4)
    aws ecr get-login-password --region "$region" | \
        docker login --username AWS --password-stdin "$REGISTRY"
    
    log_success "ECR 登录成功"
}

# 主函数
main() {
    local services=()
    local push=false
    BUILD_ARGS=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --push)
                push=true
                shift
                ;;
            --no-cache)
                BUILD_ARGS="$BUILD_ARGS --no-cache"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            base|api|worker|web|all)
                services+=("$1")
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 默认构建所有服务
    if [ ${#services[@]} -eq 0 ]; then
        services=("all")
    fi
    
    # 切换到项目根目录
    cd "$PROJECT_ROOT"
    
    log_info "项目根目录: $PROJECT_ROOT"
    log_info "目标平台: $PLATFORM"
    log_info "镜像标签: $IMAGE_TAG"
    
    # 如果需要推送，先登录 ECR
    if [ "$push" = true ]; then
        ecr_login
    fi
    
    # 构建镜像
    for service in "${services[@]}"; do
        case $service in
            base)
                build_base
                [ "$push" = true ] && push_image "$BASE_IMAGE"
                ;;
            api)
                build_api
                [ "$push" = true ] && push_image "$API_IMAGE"
                ;;
            worker)
                build_worker
                [ "$push" = true ] && push_image "$WORKER_IMAGE"
                ;;
            web)
                build_web
                [ "$push" = true ] && push_image "$WEB_IMAGE"
                ;;
            all)
                build_base
                build_api
                build_worker
                build_web
                if [ "$push" = true ]; then
                    push_image "$BASE_IMAGE"
                    push_image "$API_IMAGE"
                    push_image "$WORKER_IMAGE"
                    push_image "$WEB_IMAGE"
                fi
                ;;
        esac
    done
    
    log_success "所有镜像构建完成！"
    
    # 显示镜像列表
    echo ""
    log_info "已构建的镜像:"
    docker images | grep -E "^(nexus-|REPOSITORY)" | head -10
}

# 执行主函数
main "$@"
