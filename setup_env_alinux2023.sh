#!/bin/bash

#===============================================================================
# Nexus-AI 环境快速初始化脚本
# ⚠️  仅适用于 Amazon Linux 2023，不支持其他操作系统
# 
# 使用方法:
#   curl -O https://raw.githubusercontent.com/<your-repo>/Nexus-AI/main/setup_env_alinux2023.sh
#   chmod +x setup_env_alinux2023.sh
#   ./setup_env_alinux2023.sh
#
# 说明:
#   - 本脚本仅支持 Amazon Linux 2023
#   - 默认在 /home/ec2-user/ 目录执行
#   - 会自动克隆代码到 /home/ec2-user/Nexus-AI
#   - 容器部分只包含 Jaeger（用于追踪诊断）
#   - 运行完成后请手动配置 AWS 凭证
#===============================================================================

set -e  # 遇到错误立即退出

# 配置变量
REPO_URL="https://github.com/hy714335634/Nexus-AI.git"  # 公开仓库，无需认证
PROJECT_DIR="/home/ec2-user/Nexus-AI"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查操作系统
check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" != "amzn" ]] || [[ "$VERSION_ID" != "2023" ]]; then
            log_error "=============================================="
            log_error "此脚本仅支持 Amazon Linux 2023！"
            log_error "当前系统: $PRETTY_NAME"
            log_error "=============================================="
            exit 1
        fi
        log_success "操作系统检测通过: Amazon Linux 2023"
    else
        log_error "无法检测操作系统版本，此脚本仅支持 Amazon Linux 2023"
        exit 1
    fi
}

# 检查是否以 root 运行
check_not_root() {
    if [ "$EUID" -eq 0 ]; then
        log_error "请不要以 root 用户运行此脚本，请使用普通用户（如 ec2-user）"
        exit 1
    fi
}

# 打印横幅
print_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           Nexus-AI 环境快速初始化脚本                            ║"
    echo "║           ⚠️  仅适用于 Amazon Linux 2023                          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${YELLOW}注意：此脚本专为 Amazon Linux 2023 设计，不支持其他操作系统。${NC}"
    echo ""
}

#===============================================================================
# 第一部分：系统依赖安装
#===============================================================================

install_system_deps() {
    log_info "[Amazon Linux 2023] 正在安装系统依赖..."
    
    # 注意: 不安装 curl，因为 Amazon Linux 2023 默认使用 curl-minimal，功能足够
    sudo dnf install -y git wget htop unzip tar gcc gcc-c++ make
    
    # 安装 Python 3.12
    log_info "[Amazon Linux 2023] 正在安装 Python 3.12..."
    sudo dnf install -y python3.12 python3.12-pip python3.12-devel
    
    # 安装 Node.js
    log_info "[Amazon Linux 2023] 正在安装 Node.js..."
    sudo dnf install -y nodejs npm
    
    # 验证安装
    log_info "验证安装..."
    python3.12 --version
    node --version
    npm --version
    git --version
    curl --version  # curl-minimal 也提供 curl 命令
    
    log_success "系统依赖安装完成"
}

#===============================================================================
# 第二部分：安装 uv (Python 包管理器)
#===============================================================================

install_uv() {
    log_info "正在安装 uv (Python 包管理器)..."
    
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # 添加到 PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    # 添加到 bashrc（如果尚未添加）
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
    
    # 验证
    if command -v uv &> /dev/null; then
        uv --version
        log_success "uv 安装完成"
    else
        # 重新加载 PATH
        source ~/.bashrc 2>/dev/null || true
        export PATH="$HOME/.local/bin:$PATH"
        if command -v uv &> /dev/null; then
            uv --version
            log_success "uv 安装完成"
        else
            log_warning "uv 安装完成，但可能需要重新登录终端才能使用"
        fi
    fi
}

#===============================================================================
# 第三部分：安装 Terraform
#===============================================================================

install_terraform() {
    log_info "[Amazon Linux 2023] 正在安装 Terraform..."
    
    sudo dnf install -y dnf-plugins-core
    sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
    sudo dnf install -y terraform
    
    # 验证
    terraform --version
    
    log_success "Terraform 安装完成"
}

#===============================================================================
# 第四部分：安装 Docker
#===============================================================================

install_docker() {
    log_info "[Amazon Linux 2023] 正在安装 Docker..."
    
    sudo dnf install -y docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # 将当前用户添加到 docker 组
    sudo usermod -aG docker $USER
    
    log_success "Docker 安装完成"
    log_warning "Docker 组权限已更新，需要重新登录或运行 'newgrp docker' 才能生效"
}

#===============================================================================
# 第五部分：启动 Jaeger 容器
#===============================================================================

start_jaeger() {
    log_info "正在启动 Jaeger 容器..."
    
    # 检查是否已有 jaeger 容器在运行
    if sudo docker ps -a --format '{{.Names}}' | grep -q '^jaeger$'; then
        log_warning "检测到已存在的 jaeger 容器，正在删除..."
        sudo docker rm -f jaeger 2>/dev/null || true
    fi
    
    # 启动 Jaeger
    sudo docker run -d \
        --name jaeger \
        --restart unless-stopped \
        -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
        -e COLLECTOR_OTLP_ENABLED=true \
        -p 6831:6831/udp \
        -p 6832:6832/udp \
        -p 5778:5778 \
        -p 16686:16686 \
        -p 4317:4317 \
        -p 4318:4318 \
        -p 14250:14250 \
        -p 14268:14268 \
        -p 14269:14269 \
        -p 9411:9411 \
        jaegertracing/all-in-one:latest
    
    log_success "Jaeger 容器启动完成"
    log_info "Jaeger UI 地址: http://localhost:16686"
}

#===============================================================================
# 第六部分：克隆代码仓库
#===============================================================================

clone_repository() {
    log_info "正在检查代码仓库..."
    
    if [ -d "$PROJECT_DIR" ]; then
        log_info "项目目录已存在: $PROJECT_DIR"
        read -p "是否拉取最新代码? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$PROJECT_DIR"
            git pull
            log_success "代码更新完成"
        else
            log_info "跳过代码更新"
        fi
    else
        log_info "正在克隆代码仓库..."
        read -p "请输入 Git 仓库地址 (直接回车使用默认: $REPO_URL): " input_url
        if [ -n "$input_url" ]; then
            REPO_URL="$input_url"
        fi
        
        git clone "$REPO_URL" "$PROJECT_DIR"
        log_success "代码克隆完成: $PROJECT_DIR"
    fi
}

#===============================================================================
# 第七部分：初始化 Python 虚拟环境
#===============================================================================

setup_python_env() {
    log_info "正在初始化 Python 虚拟环境..."
    
    cd "$PROJECT_DIR"
    
    # 确保 uv 可用
    export PATH="$HOME/.local/bin:$PATH"
    
    # 创建虚拟环境
    if [ ! -d ".venv" ]; then
        log_info "创建虚拟环境..."
        uv venv --python python3.12
    else
        log_info "虚拟环境已存在，跳过创建"
    fi
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 添加激活命令到 bashrc（如果尚未添加）
    ACTIVATE_CMD="source $PROJECT_DIR/.venv/bin/activate"
    if ! grep -q "source.*Nexus-AI/.venv/bin/activate" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# Nexus-AI 虚拟环境" >> ~/.bashrc
        echo "$ACTIVATE_CMD" >> ~/.bashrc
    fi
    
    # 添加 cd 到项目目录
    if ! grep -q "cd $PROJECT_DIR" ~/.bashrc; then
        echo "cd $PROJECT_DIR" >> ~/.bashrc
    fi
    
    log_success "Python 虚拟环境初始化完成"
}

#===============================================================================
# 第八部分：安装 Python 依赖
#===============================================================================

install_python_deps() {
    log_info "正在安装 Python 依赖..."
    
    cd "$PROJECT_DIR"
    
    # 确保 uv 可用
    export PATH="$HOME/.local/bin:$PATH"
    
    # 激活虚拟环境
    source .venv/bin/activate
    
    # 升级 pip
    uv pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        log_info "安装 requirements.txt 中的依赖..."
        uv pip install -r requirements.txt
    else
        log_warning "未找到 requirements.txt"
    fi
    
    # 安装额外依赖
    log_info "安装 strands-agents[otel]..."
    uv pip install strands-agents[otel]
    
    # 安装当前包
    if [ -f "pyproject.toml" ]; then
        log_info "安装项目包..."
        uv pip install -e .
    fi
    
    log_success "Python 依赖安装完成"
}

#===============================================================================
# 第九部分：安装前端依赖
#===============================================================================

install_frontend_deps() {
    log_info "正在安装前端依赖..."
    
    if [ -d "$PROJECT_DIR/web" ]; then
        cd "$PROJECT_DIR/web"
        if [ -f "package.json" ]; then
            npm install
            log_success "前端依赖安装完成"
        else
            log_warning "未找到 web/package.json，跳过前端依赖安装"
        fi
        cd "$PROJECT_DIR"
    else
        log_warning "未找到 web 目录，跳过前端依赖安装"
    fi
}

#===============================================================================
# 打印完成信息
#===============================================================================

print_completion() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              环境初始化完成！(Amazon Linux 2023)                 ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    log_success "所有组件安装完成！"
    echo ""
    echo "=============================================="
    echo "后续步骤："
    echo "=============================================="
    echo ""
    echo "1. 重新登录终端或执行以下命令使 Docker 组权限生效："
    echo -e "   ${YELLOW}newgrp docker${NC}"
    echo ""
    echo "2. 配置 AWS 凭证（必须）："
    echo -e "   ${YELLOW}aws configure${NC}"
    echo "   或设置环境变量："
    echo -e "   ${YELLOW}export AWS_ACCESS_KEY_ID=<your-access-key>${NC}"
    echo -e "   ${YELLOW}export AWS_SECRET_ACCESS_KEY=<your-secret-key>${NC}"
    echo -e "   ${YELLOW}export AWS_DEFAULT_REGION=us-east-1${NC}"
    echo ""
    echo "3. 初始化基础设施（如需要）："
    echo -e "   ${YELLOW}python scripts/init_infrastructure.py${NC}"
    echo ""
    echo "4. 启动后端服务："
    echo -e "   ${YELLOW}cd $PROJECT_DIR && uvicorn api.v2.main:app --host 0.0.0.0 --port 8000${NC}"
    echo ""
    echo "5. 启动前端服务："
    echo -e "   ${YELLOW}cd $PROJECT_DIR/web && npm run dev -- -H 0.0.0.0${NC}"
    echo ""
    echo "=============================================="
    echo "服务访问地址："
    echo "=============================================="
    echo "  - Jaeger UI:   http://localhost:16686"
    echo "  - 前端服务:     http://<EC2-IP>:3000"
    echo "  - 后端 API:    http://<EC2-IP>:8000"
    echo ""
    echo "=============================================="
    echo "SSH 端口转发（如需本地访问）："
    echo "=============================================="
    echo -e "  ${YELLOW}ssh -i your-key.pem -L 16686:localhost:16686 -L 3000:localhost:3000 -L 8000:localhost:8000 ec2-user@<EC2-IP>${NC}"
    echo ""
    echo "=============================================="
    echo "项目目录："
    echo "=============================================="
    echo "  $PROJECT_DIR"
    echo ""
    echo "重新登录后将自动进入项目目录并激活虚拟环境。"
    echo ""
}

#===============================================================================
# 主函数
#===============================================================================

main() {
    print_banner
    check_os        # 检查操作系统版本
    check_not_root
    
    log_info "开始环境初始化..."
    log_info "项目将安装到: $PROJECT_DIR"
    echo ""
    
    # 安装系统依赖
    install_system_deps
    echo ""
    
    # 安装 uv
    install_uv
    echo ""
    
    # 安装 Terraform
    install_terraform
    echo ""
    
    # 安装 Docker
    install_docker
    echo ""
    
    # 启动 Jaeger
    start_jaeger
    echo ""
    
    # 克隆代码仓库
    clone_repository
    echo ""
    
    # 设置 Python 环境
    setup_python_env
    echo ""
    
    # 安装 Python 依赖
    install_python_deps
    echo ""
    
    # 安装前端依赖
    install_frontend_deps
    echo ""
    
    # 打印完成信息
    print_completion
}

# 运行主函数
main "$@"
