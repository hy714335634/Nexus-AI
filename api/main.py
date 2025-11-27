"""
FastAPI main application for NexusAI Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.routers import agents, projects, sessions, statistics, agents_management, agent_dialog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Nexus-AI Platform API",
    description="让 AI 帮你构建 AI，统一管理与运维智能体",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(statistics.router, prefix="/api/v1", tags=["statistics"])
app.include_router(agents_management.router, prefix="/api/v1", tags=["agents-management"])
app.include_router(agent_dialog.router, prefix="/api/v1", tags=["agent-dialog"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Nexus-AI Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
