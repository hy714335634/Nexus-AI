#!/bin/bash

#===============================================================================
# Nexus-AI 一键启动所有服务脚本
# 
# 功能:
#   - 启动后端 API 服务 (FastAPI)
#   - 启动 Worker 服务 (SQS 消费者)
#   - 启动前端服务 (Next.js)
#   - 自动采集所有服务日志到 logs/ 目录
#   - 支持优雅停止所有服务
#
# 使用方法:
#   ./start_all_services.sh          # 启动所有服务
#   ./start_all_services.sh stop     # 停止所有服务
#   ./start_all_services.sh status   # 查看服务状态
#   ./start_all_services.sh restart  # 重启所有服务
#   ./start_all_services.sh logs     # 查看实时日志
#
# 日志位置:
#   - logs/api.log          # API 服务日志
#   - logs/worker.log       # Worker 服务日志
#   - logs/web.log          # 前端服务日志
#   - logs/services.log     # 服务管理日志
#===============================================================================

set -e

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 配置
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"
VENV_DIR="$PROJECT_ROOT/.venv"

# 服务端口
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"

# 运行模式: dev (开发模式) 或 prod (生产模式，使用编译后的代码)
RUN_MODE="${RUN_MODE:-prod}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
    echo -e "${BLUE}$msg${NC}"
    echo "$msg" >> "$LOG_DIR/services.log"
}

log_success() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$LOG_DIR/services.log"
}

log_warning() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$LOG_DIR/services.log"
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1"
    echo -e "${RED}$msg${NC}"
    echo "$msg" >> "$LOG_DIR/services.log"
}

# 初始化目录
init_dirs() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    
    # 初始化服务日志文件
    touch "$LOG_DIR/services.log"
}

# 检查虚拟环境
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_error "虚拟环境不存在: $VENV_DIR"
        log_info "请先运行: uv venv --python python3.12"
        exit 1
    fi
}

# 激活虚拟环境
activate_venv() {
    source "$VENV_DIR/bin/activate"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 获取占用端口的进程
get_port_pid() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null | head -1
}

# 打印横幅
print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              Nexus-AI 服务管理脚本                               ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

#===============================================================================
# 启动 API 服务
#===============================================================================
start_api() {
    log_info "正在启动 API 服务..."
    
    # 检查端口
    if check_port $API_PORT; then
        local pid=$(get_port_pid $API_PORT)
        log_warning "端口 $API_PORT 已被占用 (PID: $pid)"
        log_info "尝试停止现有进程..."
        kill $pid 2>/dev/null || true
        sleep 2
    fi
    
    cd "$PROJECT_ROOT"
    activate_venv
    
    # 设置环境变量
    export AWS_REGION="${AWS_REGION:-us-west-2}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    export PYTHONUNBUFFERED=1
    
    # 启动 API 服务（后台运行，日志输出到文件）
    nohup uvicorn api.v2.main:app \
        --host 0.0.0.0 \
        --port $API_PORT \
        --log-level info \
        >> "$LOG_DIR/api.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_DIR/api.pid"
    
    # 等待服务启动
    sleep 3
    
    if kill -0 $pid 2>/dev/null; then
        log_success "API 服务启动成功 (PID: $pid, Port: $API_PORT)"
    else
        log_error "API 服务启动失败，请检查日志: $LOG_DIR/api.log"
        return 1
    fi
}

#===============================================================================
# 启动 Worker 服务
#===============================================================================
start_worker() {
    log_info "正在启动 Worker 服务..."
    
    cd "$PROJECT_ROOT"
    activate_venv
    
    # 设置环境变量
    export AWS_REGION="${AWS_REGION:-us-west-2}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    export PYTHONUNBUFFERED=1
    
    # 启动 Worker 服务（后台运行，日志输出到文件）
    nohup python -m worker.main --queue build \
        >> "$LOG_DIR/worker.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_DIR/worker.pid"
    
    # 等待服务启动
    sleep 2
    
    if kill -0 $pid 2>/dev/null; then
        log_success "Worker 服务启动成功 (PID: $pid)"
    else
        log_error "Worker 服务启动失败，请检查日志: $LOG_DIR/worker.log"
        return 1
    fi
}

#===============================================================================
# 启动前端服务
#===============================================================================
start_web() {
    log_info "正在启动前端服务 (模式: $RUN_MODE)..."
    
    # 检查端口
    if check_port $WEB_PORT; then
        local pid=$(get_port_pid $WEB_PORT)
        log_warning "端口 $WEB_PORT 已被占用 (PID: $pid)"
        log_info "尝试停止现有进程..."
        kill $pid 2>/dev/null || true
        sleep 2
    fi
    
    cd "$PROJECT_ROOT/web"
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        log_info "正在安装前端依赖..."
        npm install >> "$LOG_DIR/web.log" 2>&1
    fi
    
    # 设置环境变量
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$API_PORT}"
    export PORT=$WEB_PORT
    export HOSTNAME="0.0.0.0"
    
    if [ "$RUN_MODE" = "prod" ]; then
        # 生产模式：使用编译后的代码
        # 检查是否有完整的生产构建（BUILD_ID 文件是生产构建的标志）
        if [ ! -f ".next/BUILD_ID" ] || [ "$FORCE_BUILD" = "true" ]; then
            if [ -d ".next" ] && [ ! -f ".next/BUILD_ID" ]; then
                log_warning "检测到不完整的 .next 目录（可能是开发模式生成），正在清理..."
                rm -rf .next
            fi
            log_info "正在编译前端代码..."
            npm run build >> "$LOG_DIR/web.log" 2>&1
            if [ $? -ne 0 ]; then
                log_error "前端编译失败，请检查日志: $LOG_DIR/web.log"
                return 1
            fi
            log_success "前端编译完成"
        else
            log_info "使用已编译的前端代码 (.next/BUILD_ID 存在)"
        fi
        
        # 启动生产服务
        nohup npm run start \
            >> "$LOG_DIR/web.log" 2>&1 &
    else
        # 开发模式：热更新
        nohup npm run dev -- -H 0.0.0.0 -p $WEB_PORT \
            >> "$LOG_DIR/web.log" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$PID_DIR/web.pid"
    
    # 等待服务启动
    sleep 5
    
    if kill -0 $pid 2>/dev/null; then
        log_success "前端服务启动成功 (PID: $pid, Port: $WEB_PORT, Mode: $RUN_MODE)"
    else
        log_error "前端服务启动失败，请检查日志: $LOG_DIR/web.log"
        return 1
    fi
}

#===============================================================================
# 停止服务
#===============================================================================
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            log_info "正在停止 $service_name 服务 (PID: $pid)..."
            kill $pid 2>/dev/null || true
            
            # 等待进程退出
            local count=0
            while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # 如果还没退出，强制杀死
            if kill -0 $pid 2>/dev/null; then
                log_warning "进程未响应，强制终止..."
                kill -9 $pid 2>/dev/null || true
            fi
            
            log_success "$service_name 服务已停止"
        else
            log_warning "$service_name 服务进程不存在"
        fi
        rm -f "$pid_file"
    else
        log_warning "$service_name 服务 PID 文件不存在"
    fi
}

stop_all() {
    log_info "正在停止所有服务..."
    
    stop_service "web"
    stop_service "worker"
    stop_service "api"
    
    # 清理可能残留的进程
    pkill -f "uvicorn api.v2.main:app" 2>/dev/null || true
    pkill -f "python -m worker.main" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    log_success "所有服务已停止"
}

#===============================================================================
# 查看服务状态
#===============================================================================
check_service_status() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    local port=$2
    
    echo -n "  $service_name: "
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${GREEN}运行中${NC} (PID: $pid)"
            if [ -n "$port" ]; then
                echo -e "    └─ 端口: $port"
            fi
            return 0
        else
            echo -e "${RED}已停止${NC} (PID 文件存在但进程不存在)"
            return 1
        fi
    else
        echo -e "${YELLOW}未启动${NC}"
        return 1
    fi
}

show_status() {
    echo ""
    echo -e "${CYAN}服务状态:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    check_service_status "api" $API_PORT
    check_service_status "worker" ""
    check_service_status "web" $WEB_PORT
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${CYAN}日志文件:${NC}"
    echo "  - API:     $LOG_DIR/api.log"
    echo "  - Worker:  $LOG_DIR/worker.log"
    echo "  - Web:     $LOG_DIR/web.log"
    echo "  - 服务管理: $LOG_DIR/services.log"
    echo ""
}

#===============================================================================
# 查看实时日志
#===============================================================================
show_logs() {
    local service=$1
    
    if [ -z "$service" ]; then
        # 显示所有日志
        log_info "显示所有服务日志 (Ctrl+C 退出)..."
        tail -f "$LOG_DIR/api.log" "$LOG_DIR/worker.log" "$LOG_DIR/web.log"
    else
        # 显示指定服务日志
        local log_file="$LOG_DIR/${service}.log"
        if [ -f "$log_file" ]; then
            log_info "显示 $service 服务日志 (Ctrl+C 退出)..."
            tail -f "$log_file"
        else
            log_error "日志文件不存在: $log_file"
        fi
    fi
}

#===============================================================================
# 启动所有服务
#===============================================================================
start_all() {
    print_banner
    
    log_info "开始启动所有服务..."
    log_info "项目目录: $PROJECT_ROOT"
    echo ""
    
    # 初始化
    init_dirs
    check_venv
    
    # 清空旧日志（可选）
    # > "$LOG_DIR/api.log"
    # > "$LOG_DIR/worker.log"
    # > "$LOG_DIR/web.log"
    
    # 添加启动分隔符
    echo "" >> "$LOG_DIR/api.log"
    echo "========== 服务启动 $(date '+%Y-%m-%d %H:%M:%S') ==========" >> "$LOG_DIR/api.log"
    echo "" >> "$LOG_DIR/worker.log"
    echo "========== 服务启动 $(date '+%Y-%m-%d %H:%M:%S') ==========" >> "$LOG_DIR/worker.log"
    echo "" >> "$LOG_DIR/web.log"
    echo "========== 服务启动 $(date '+%Y-%m-%d %H:%M:%S') ==========" >> "$LOG_DIR/web.log"
    
    # 启动服务
    start_api
    echo ""
    
    start_worker
    echo ""
    
    start_web
    echo ""
    
    # 显示状态
    show_status
    
    # 打印访问信息
    echo -e "${CYAN}访问地址:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  - 前端:     http://localhost:$WEB_PORT"
    echo "  - API:      http://localhost:$API_PORT"
    echo "  - API 文档: http://localhost:$API_PORT/docs"
    echo "  - 健康检查: http://localhost:$API_PORT/health"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "${YELLOW}提示:${NC}"
    echo "  - 查看日志: ./start_all_services.sh logs"
    echo "  - 查看状态: ./start_all_services.sh status"
    echo "  - 停止服务: ./start_all_services.sh stop"
    echo ""
}

#===============================================================================
# 重启所有服务
#===============================================================================
restart_all() {
    log_info "正在重启所有服务..."
    stop_all
    sleep 2
    start_all
}

#===============================================================================
# 主函数
#===============================================================================
main() {
    cd "$PROJECT_ROOT"
    init_dirs
    
    case "${1:-start}" in
        start)
            start_all
            ;;
        stop)
            print_banner
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            print_banner
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        help|--help|-h)
            print_banner
            echo "使用方法:"
            echo "  $0 [命令] [参数]"
            echo ""
            echo "命令:"
            echo "  start     启动所有服务 (默认)"
            echo "  stop      停止所有服务"
            echo "  restart   重启所有服务"
            echo "  status    查看服务状态"
            echo "  logs      查看实时日志"
            echo "            logs api    - 只看 API 日志"
            echo "            logs worker - 只看 Worker 日志"
            echo "            logs web    - 只看前端日志"
            echo "  help      显示帮助信息"
            echo ""
            echo "环境变量:"
            echo "  RUN_MODE      运行模式: prod (默认，编译后运行) 或 dev (开发模式)"
            echo "  FORCE_BUILD   强制重新编译前端: true/false (默认: false)"
            echo "  API_PORT      API 服务端口 (默认: 8000)"
            echo "  WEB_PORT      前端服务端口 (默认: 3000)"
            echo "  AWS_REGION    AWS 区域 (默认: us-west-2)"
            echo "  LOG_LEVEL     日志级别 (默认: INFO)"
            echo ""
            echo "示例:"
            echo "  ./start_all_services.sh                    # 生产模式启动"
            echo "  RUN_MODE=dev ./start_all_services.sh       # 开发模式启动"
            echo "  FORCE_BUILD=true ./start_all_services.sh   # 强制重新编译前端"
            echo ""
            ;;
        *)
            log_error "未知命令: $1"
            echo "使用 '$0 help' 查看帮助信息"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
