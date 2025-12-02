"""
Configuration settings for Nexus-AI Platform API
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Database Configuration
    DYNAMODB_REGION: str = "us-west-2"
    DYNAMODB_ENDPOINT_URL: Optional[str] = None  # For local development

    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-west-2"
    
    # Application Configuration
    MAX_CONCURRENT_BUILDS: int = 10
    BUILD_TIMEOUT_MINUTES: int = 600

    # AgentCore Deployment Configuration
    AGENTCORE_REGION: Optional[str] = None
    AGENTCORE_AUTO_CREATE_EXECUTION_ROLE: bool = True
    AGENTCORE_AUTO_CREATE_ECR: bool = True
    AGENTCORE_DOCKER_CONTEXT: str = "."
    AGENTCORE_REQUIREMENTS_PATH: str = "requirements.txt"
    AGENTCORE_IMAGE_TAG_TEMPLATE: str = "{agent_name}:latest"
    AGENTCORE_DEFAULT_ALIAS: str = "DEFAULT"
    AGENTCORE_DEPLOY_DRY_RUN: bool = False
    AGENTCORE_EXECUTION_ROLE_NAME: Optional[str] = None
    AGENTCORE_POST_DEPLOY_TEST: bool = True
    AGENTCORE_POST_DEPLOY_TEST_PROMPT: str = "Hello from Nexus-AI"
    
    # Agent Runtime Integration
    AGENT_RUNTIME_URL: str = "http://localhost:8080"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def get_redis_url(self) -> str:
        """
        构建Redis连接URL
        优先使用AWS ElastiCache配置，否则使用默认配置
        """
        if self.REDIS_HOST:
            # 使用AWS ElastiCache
            protocol = "rediss" if self.REDIS_SSL else "redis"
            auth_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            return f"{protocol}://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        else:
            # 使用默认配置
            return self.REDIS_URL
    
    def get_celery_broker_url(self) -> str:
        """获取Celery broker URL"""
        return os.getenv("CELERY_BROKER_URL", self.get_redis_url())
    
    def get_celery_result_backend(self) -> str:
        """获取Celery result backend URL"""
        return os.getenv("CELERY_RESULT_BACKEND", self.get_redis_url())

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
