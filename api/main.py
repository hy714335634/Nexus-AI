"""
Nexus-AI Platform API - FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime
import uuid

from api.core.config import settings
from api.core.exceptions import APIException
from api.routers import agents, agents_management, projects, sessions, statistics, agent_dialog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Nexus-AI Platform API",
    description="""
## Nexus-AI Platform API

RESTful API service for automated AI agent creation, deployment, and management.

### Key Features

* **Automated Agent Building**: Multi-stage workflow from requirements to deployment
* **Agent Management**: Full lifecycle management of AI agents
* **Session Management**: Multi-turn conversation support with context
* **Real-time Statistics**: Build metrics, invocation stats, and trends
* **AWS Bedrock Integration**: Deploy agents to AWS Bedrock AgentCore

### Build Stages

1. **Orchestrator** (5%): Project initialization and planning
2. **Requirements Analysis** (10%): Analyze and structure requirements
3. **System Architecture** (15%): Design system architecture
4. **Agent Design** (15%): Define agent specifications
5. **Agent Developer Manager** (45%): Develop tools, prompts, and code
   - Tool Developer (40%)
   - Prompt Engineer (30%)
   - Agent Code Developer (30%)
6. **Agent Deployer** (10%): Deploy to AWS Bedrock

### API Conventions

* All timestamps in ISO 8601 format with 'Z' suffix
* All responses include `success`, `data`, and `timestamp` fields
* Error responses include detailed error codes and suggestions
* Pagination using cursor-based approach with `limit` and `last_key`

### Authentication

Currently, the API does not require authentication. This will be added in future releases.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "projects",
            "description": "Project lifecycle management - create, monitor, control, and delete projects"
        },
        {
            "name": "agents-management",
            "description": "Agent instance management - invoke, query, update, and delete deployed agents"
        },
        {
            "name": "agents",
            "description": "Legacy agent operations - backwards compatibility endpoints"
        },
        {
            "name": "sessions",
            "description": "Multi-turn conversation sessions with agents"
        },
        {
            "name": "statistics",
            "description": "Real-time system statistics, build metrics, and trends"
        },
        {
            "name": "agent-dialog",
            "description": "Agent dialog operations"
        }
    ],
    contact={
        "name": "Nexus-AI Support",
        "email": "support@nexus-ai.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for custom API exceptions
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions with proper logging and response format"""
    request_id = str(uuid.uuid4())

    # Log the error with request context
    logger.error(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details or {},
                "suggestion": exc.suggestion or _get_suggestion(exc.error_code),
                "trace_id": request_id
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    )

# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with detailed logging"""
    request_id = str(uuid.uuid4())

    # Log the unexpected error with full context
    logger.exception(
        f"Unexpected exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error occurred",
                "details": {"error": str(exc)} if settings.DEBUG else {},
                "suggestion": "Please retry later or contact technical support",
                "trace_id": request_id
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    )

def _get_suggestion(error_code: str) -> str:
    """Get suggestion message for error code"""
    suggestions = {
        "VALIDATION_ERROR": "Please check request parameters format and required fields",
        "RESOURCE_NOT_FOUND": "Please confirm the resource ID is correct",
        "RESOURCE_CONFLICT": "Please use a different name or identifier",
        "INVALID_STATE": "Please check the resource's current state before performing this operation",
        "PERMISSION_DENIED": "Please check your permissions or contact the administrator",
        "RATE_LIMIT_EXCEEDED": "Please retry later or upgrade your quota",
        "STAGE_UPDATE_FAILED": "Please retry or contact technical support",
        "AGENT_INVOCATION_FAILED": "Please check the agent status and logs",
        "DATABASE_ERROR": "Please retry later or contact technical support",
        "BUILD_ERROR": "Please check the build logs and retry",
        "INTERNAL_ERROR": "Please contact technical support"
    }
    return suggestions.get(error_code, "Please contact technical support")

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Basic health check endpoint

    Returns the service status and version information.
    Use this endpoint for load balancer health checks.
    """
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

# Detailed health check endpoint
@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """
    Detailed health check with service dependencies

    Returns comprehensive health information including:
    - API service status
    - Database connectivity
    - AWS credentials configuration
    - System uptime
    """
    from api.database.dynamodb_client import dynamodb_client
    import os
    import psutil

    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }

    # Check database connectivity
    try:
        # Simple check to see if DynamoDB client is configured
        dynamodb_client.list_tables(MaxResults=1)
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "DynamoDB connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"DynamoDB connection failed: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Check AWS credentials
    aws_configured = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    health_status["checks"]["aws_credentials"] = {
        "status": "configured" if aws_configured else "not_configured",
        "message": "AWS credentials configured" if aws_configured else "AWS credentials not configured"
    }

    # System information
    try:
        process = psutil.Process()
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": process.memory_info().rss / 1024 / 1024,
            "uptime_seconds": int((datetime.utcnow() - datetime.fromtimestamp(process.create_time())).total_seconds())
        }
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        health_status["system"] = {
            "message": "System information not available"
        }

    return {
        "success": True,
        "data": health_status
    }

# Readiness check endpoint
@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration

    Returns 200 if the service is ready to accept traffic,
    503 if the service is not ready.
    """
    from api.database.dynamodb_client import dynamodb_client

    try:
        # Check if database is accessible
        dynamodb_client.list_tables(MaxResults=1)

        return {
            "success": True,
            "data": {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "data": {
                    "status": "not_ready",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }
        )

# Liveness check endpoint
@app.get("/health/live", tags=["health"])
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration

    Returns 200 if the service is alive.
    This endpoint should always return 200 unless the process is dead.
    """
    return {
        "success": True,
        "data": {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

# Stage information endpoint
@app.get("/stages/info")
async def get_stages_info():
    """Get information about all build stages"""
    from api.core.stage_manager import stage_manager
    
    return {
        "success": True,
        "data": stage_manager.get_stage_summary(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": str(uuid.uuid4())
    }

# Include routers
# Note: projects, agents_management, and sessions routers are registered before agents to ensure new endpoints take precedence
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(agents_management.router, prefix="/api/v1", tags=["agents-management"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(statistics.router, prefix="/api/v1", tags=["statistics"])
app.include_router(agent_dialog.router, prefix="/api/v1", tags=["agent-dialog"])

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
