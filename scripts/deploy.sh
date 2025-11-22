#!/bin/bash
# Nexus-AI Platform API Deployment Script
# This script handles the deployment of the API service

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-production}"
API_PORT="${API_PORT:-8000}"
LOG_DIR="${PROJECT_ROOT}/logs"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    log_info "Checking Python installation..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: $PYTHON_VERSION"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check if virtual environment exists
    if [ ! -d "${PROJECT_ROOT}/venv" ]; then
        log_warn "Virtual environment not found. Creating..."
        python3 -m venv "${PROJECT_ROOT}/venv"
    fi

    # Activate virtual environment
    source "${PROJECT_ROOT}/venv/bin/activate"

    # Install/update requirements
    log_info "Installing/updating requirements..."
    pip install -r "${PROJECT_ROOT}/requirements.txt" --quiet
}

check_environment() {
    log_info "Checking environment configuration..."

    # Check if .env file exists
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        log_warn ".env file not found. Using default configuration"
        if [ -f "${PROJECT_ROOT}/.env.example" ]; then
            log_info "Copying .env.example to .env"
            cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
        fi
    fi

    # Source environment variables
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        export $(cat "${PROJECT_ROOT}/.env" | grep -v '^#' | xargs)
    fi
}

check_aws_credentials() {
    log_info "Checking AWS credentials..."

    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        log_warn "AWS credentials not configured"
        log_warn "Some features may not work without AWS credentials"
    else
        log_info "AWS credentials configured"
    fi
}

create_log_directory() {
    log_info "Creating log directory..."
    mkdir -p "${LOG_DIR}"

    # Set proper permissions
    chmod 755 "${LOG_DIR}"
}

run_health_check() {
    log_info "Running health check..."

    # Wait for API to start
    sleep 5

    # Check if API is responding
    if curl -f "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
        log_info "Health check passed ✓"
        return 0
    else
        log_error "Health check failed ✗"
        return 1
    fi
}

start_api() {
    log_info "Starting Nexus-AI Platform API..."

    # Activate virtual environment
    source "${PROJECT_ROOT}/venv/bin/activate"

    # Start API in background
    cd "${PROJECT_ROOT}"

    if [ "$ENVIRONMENT" == "production" ]; then
        log_info "Starting in production mode..."

        # Use gunicorn for production
        if ! command -v gunicorn &> /dev/null; then
            log_info "Installing gunicorn..."
            pip install gunicorn
        fi

        gunicorn api.main:app \
            --workers 4 \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind "0.0.0.0:${API_PORT}" \
            --access-logfile "${LOG_DIR}/access.log" \
            --error-logfile "${LOG_DIR}/error.log" \
            --log-level info \
            --daemon \
            --pid "${PROJECT_ROOT}/api.pid"

        log_info "API started with PID $(cat ${PROJECT_ROOT}/api.pid)"
    else
        log_info "Starting in development mode..."

        # Use uvicorn for development
        nohup python3 -m uvicorn api.main:app \
            --host 0.0.0.0 \
            --port "${API_PORT}" \
            --reload \
            > "${LOG_DIR}/api.log" 2>&1 &

        echo $! > "${PROJECT_ROOT}/api.pid"
        log_info "API started with PID $(cat ${PROJECT_ROOT}/api.pid)"
    fi

    # Run health check
    if run_health_check; then
        log_info "API is ready at http://localhost:${API_PORT}"
        log_info "API Documentation: http://localhost:${API_PORT}/docs"
    else
        log_error "API failed to start properly"
        stop_api
        exit 1
    fi
}

stop_api() {
    log_info "Stopping Nexus-AI Platform API..."

    if [ -f "${PROJECT_ROOT}/api.pid" ]; then
        PID=$(cat "${PROJECT_ROOT}/api.pid")

        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            log_info "Stopped API process (PID: $PID)"
        else
            log_warn "API process not running (PID: $PID)"
        fi

        rm "${PROJECT_ROOT}/api.pid"
    else
        log_warn "PID file not found. API may not be running."

        # Try to find and kill the process by port
        if command -v lsof &> /dev/null; then
            PID=$(lsof -ti :${API_PORT})
            if [ ! -z "$PID" ]; then
                kill $PID
                log_info "Stopped process on port ${API_PORT} (PID: $PID)"
            fi
        fi
    fi
}

restart_api() {
    log_info "Restarting Nexus-AI Platform API..."
    stop_api
    sleep 2
    start_api
}

show_status() {
    log_info "Checking API status..."

    if [ -f "${PROJECT_ROOT}/api.pid" ]; then
        PID=$(cat "${PROJECT_ROOT}/api.pid")

        if ps -p $PID > /dev/null 2>&1; then
            log_info "API is running (PID: $PID)"

            # Check health endpoint
            if curl -f "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
                log_info "Health check: ✓ HEALTHY"
            else
                log_warn "Health check: ✗ UNHEALTHY"
            fi
        else
            log_warn "API process not found (PID: $PID)"
        fi
    else
        log_warn "API is not running (no PID file found)"
    fi
}

show_logs() {
    log_info "Showing API logs..."

    if [ "$ENVIRONMENT" == "production" ]; then
        tail -f "${LOG_DIR}/error.log" "${LOG_DIR}/access.log"
    else
        tail -f "${LOG_DIR}/api.log"
    fi
}

show_usage() {
    cat << EOF
Nexus-AI Platform API Deployment Script

Usage: $0 {start|stop|restart|status|logs|help}

Commands:
    start       Start the API service
    stop        Stop the API service
    restart     Restart the API service
    status      Show API service status
    logs        Show API logs (tail -f)
    help        Show this help message

Environment Variables:
    ENVIRONMENT     Deployment environment (development|production) [default: production]
    API_PORT        API service port [default: 8000]

Examples:
    # Start in production mode
    ./deploy.sh start

    # Start in development mode
    ENVIRONMENT=development ./deploy.sh start

    # Use custom port
    API_PORT=9000 ./deploy.sh start

    # Check status
    ./deploy.sh status

    # View logs
    ./deploy.sh logs
EOF
}

# Main script
main() {
    case "${1:-}" in
        start)
            log_info "=== Nexus-AI Platform API Deployment ==="
            log_info "Environment: $ENVIRONMENT"
            log_info "Port: $API_PORT"
            echo ""

            check_python
            check_dependencies
            check_environment
            check_aws_credentials
            create_log_directory
            start_api

            log_info ""
            log_info "=== Deployment Complete ==="
            log_info "API URL: http://localhost:${API_PORT}"
            log_info "API Docs: http://localhost:${API_PORT}/docs"
            log_info "Health: http://localhost:${API_PORT}/health"
            ;;
        stop)
            stop_api
            ;;
        restart)
            restart_api
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Invalid command: ${1:-}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
