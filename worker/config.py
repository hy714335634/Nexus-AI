"""
Worker Service Configuration
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class WorkerSettings(BaseSettings):
    """Worker 服务配置"""
    
    # Worker 标识
    WORKER_ID: str = f"worker-{os.getpid()}"
    
    # AWS Configuration
    AWS_REGION: str = "us-west-2"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # DynamoDB Configuration
    DYNAMODB_ENDPOINT_URL: Optional[str] = None
    DYNAMODB_TABLE_PREFIX: str = "nexus_"
    
    # SQS Configuration
    SQS_ENDPOINT_URL: Optional[str] = None
    SQS_BUILD_QUEUE_NAME: str = "nexus-build-queue"
    SQS_DEPLOY_QUEUE_NAME: str = "nexus-deploy-queue"
    
    # Worker Configuration
    POLL_INTERVAL_SECONDS: int = 5
    MAX_MESSAGES_PER_POLL: int = 1
    VISIBILITY_TIMEOUT: int = 3600  # 1 hour
    HEARTBEAT_INTERVAL: int = 300  # 5 minutes
    MAX_RETRY_COUNT: int = 3
    
    # Build Configuration
    BUILD_TIMEOUT_SECONDS: int = 7200  # 2 hours
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_worker_settings() -> WorkerSettings:
    """Get cached worker settings instance"""
    return WorkerSettings()


worker_settings = get_worker_settings()
