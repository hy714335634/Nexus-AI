"""
Nexus AI API v2 - FastAPI Application

主入口文件，配置 FastAPI 应用和路由
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import uuid

from api.v2.config import settings
from api.v2.routers import (
    projects_router,
    agents_router,
    sessions_router,
    tasks_router,
    statistics_router,
)
from api.v2.routers.config import router as config_router
from api.v2.routers.agentcore import router as agentcore_router
from api.v2.routers.agent_files import router as agent_files_router
from api.v2.routers.agent_tools import router as agent_tools_router
from api.v2.routers.workflow_control import router as workflow_control_router
from api.v2.database import db_client, sqs_client

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Nexus AI API",
    description="Nexus AI Platform API v2 - Agent 构建和管理系统",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# ============== 中间件 ==============

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """添加请求 ID 和计时"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 将 request_id 添加到请求状态
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    # 添加响应头
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # 记录请求日志
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s",
        extra={"request_id": request_id}
    )
    
    return response


# ============== 路由注册 ==============

# API v2 路由
app.include_router(projects_router, prefix="/api/v2")
app.include_router(agents_router, prefix="/api/v2")
app.include_router(agent_files_router, prefix="/api/v2")
app.include_router(agent_tools_router, prefix="/api/v2")
app.include_router(sessions_router, prefix="/api/v2")
app.include_router(tasks_router, prefix="/api/v2")
app.include_router(statistics_router, prefix="/api/v2")
app.include_router(config_router, prefix="/api/v2")
app.include_router(agentcore_router, prefix="/api/v2")
app.include_router(workflow_control_router, prefix="/api/v2")

# API v1 兼容路由 - 前端当前使用 /api/v1 路径
# 将 v1 请求映射到 v2 处理器，保持向后兼容
app.include_router(projects_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(agent_files_router, prefix="/api/v1")
app.include_router(agent_tools_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(statistics_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(agentcore_router, prefix="/api/v1")
app.include_router(workflow_control_router, prefix="/api/v1")


# ============== 健康检查 ==============

@app.get("/health")
async def health_check():
    """健康检查端点"""
    health_status = {
        "status": "healthy",
        "service": "nexus-ai-api",
        "version": settings.APP_VERSION,
        "checks": {}
    }
    
    # 检查 DynamoDB
    try:
        dynamodb_healthy = db_client.health_check()
        health_status["checks"]["dynamodb"] = "healthy" if dynamodb_healthy else "unhealthy"
    except Exception as e:
        health_status["checks"]["dynamodb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # 检查 SQS
    try:
        sqs_healthy = sqs_client.health_check()
        health_status["checks"]["sqs"] = "healthy" if sqs_healthy else "unhealthy"
    except Exception as e:
        health_status["checks"]["sqs"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(status_code=status_code, content=health_status)


@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Nexus AI Platform API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": "/api/v2"
    }


# ============== 异常处理 ==============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={"request_id": request_id})
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "request_id": request_id
            }
        }
    )


# ============== 启动事件 ==============

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Starting Nexus AI API v{settings.APP_VERSION}")
    logger.info(f"AWS Region: {settings.AWS_REGION}")
    logger.info(f"DynamoDB Endpoint: {settings.DYNAMODB_ENDPOINT_URL or 'AWS Default'}")
    logger.info(f"SQS Endpoint: {settings.SQS_ENDPOINT_URL or 'AWS Default'}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down Nexus AI API")


# ============== 开发服务器 ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.v2.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
