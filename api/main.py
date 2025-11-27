"""
FastAPI application for Nexus-AI Platform API

This is the main entry point for the API service running on ECS Fargate.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Import all routers
from api.routers import (
    agents,
    agents_management,
    agent_dialog,
    projects,
    sessions,
    statistics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Nexus-AI Platform API",
    description="API for Nexus-AI Platform - Agent building and management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
# Note: When allow_origins=["*"], allow_credentials must be False
# To allow credentials, specify exact origins instead of "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (no restrictions)
    allow_credentials=False,  # Must be False when using "*" for origins
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to frontend
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Register all routers
# ALB routes /api/* to this service, so requests arrive with /api prefix
# Frontend calls /api/v1/..., so we need to register routers with /api/v1 prefix
# Routes in routers already have their paths (e.g., /agents/create, /projects)
app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
app.include_router(agents_management.router, prefix="/api/v1", tags=["Agent Management"])
app.include_router(agent_dialog.router, prefix="/api/v1", tags=["Agent Dialog"])
app.include_router(projects.router, prefix="/api/v1", tags=["Projects"])
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
app.include_router(statistics.router, prefix="/api/v1", tags=["Statistics"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "nexus-ai-api",
            "version": "1.0.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Nexus-AI Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Lambda handler (kept for backward compatibility, but not used in ECS)
def lambda_handler(event, context):
    """
    AWS Lambda handler function (legacy, not used in ECS Fargate)
    """
    logger.warning("Lambda handler called, but service is running on ECS Fargate")
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': {
            'message': 'NexusAI API is running on ECS Fargate',
            'version': '1.0.0'
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)