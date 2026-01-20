"""
API v2 Routers
"""
from .projects import router as projects_router
from .agents import router as agents_router
from .sessions import router as sessions_router
from .tasks import router as tasks_router
from .statistics import router as statistics_router

__all__ = [
    'projects_router',
    'agents_router',
    'sessions_router',
    'tasks_router',
    'statistics_router',
]
