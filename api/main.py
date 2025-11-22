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
    description="RESTful API service for Nexus-AI agent creation and management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
@app.get("/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
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
