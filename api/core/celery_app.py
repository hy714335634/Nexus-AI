"""
Celery application configuration
"""
from celery import Celery
import logging

from api.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "nexus-ai-api",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
    include=['api.tasks.agent_build_tasks'],
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_track_started=True,
    task_time_limit=settings.BUILD_TIMEOUT_MINUTES * 60,  # Convert to seconds
    task_soft_time_limit=settings.BUILD_TIMEOUT_MINUTES * 60 - 60,  # 1 minute before hard limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    task_default_queue='default',
    task_create_missing_queues=True,
)

celery_app.conf.task_routes = {
    'api.tasks.agent_build_tasks.build_agent': {'queue': 'agent_builds'},
}

# Task result expires after 24 hours
celery_app.conf.result_expires = 86400

# Configure logging
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    logger.info(f'Request: {self.request!r}')
    return 'Celery is working!'

logger.info("Celery application configured successfully")
