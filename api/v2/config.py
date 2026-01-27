"""
API v2 Configuration Management

优先级：环境变量 > default_config.yaml > 默认值
使用 nexus_utils.config_loader 统一加载配置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

# 使用统一的配置加载器
from nexus_utils.config_loader import get_config

_config = get_config()
_aws_config = _config.get_aws_config()
_agentcore_config = _config.get_agentcore_config()
_nexus_ai_config = _config.get_nexus_ai_config()


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Nexus-AI API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # AWS Configuration - 从 default_config.yaml 读取默认值
    AWS_REGION: str = _aws_config.get('aws_region_name', 'us-west-2')
    AWS_DEFAULT_REGION: str = _aws_config.get('aws_region_name', 'us-west-2')
    AWS_ACCESS_KEY_ID: Optional[str] = _aws_config.get('aws_access_key_id') or None
    AWS_SECRET_ACCESS_KEY: Optional[str] = _aws_config.get('aws_secret_access_key') or None
    
    # DynamoDB Configuration - endpoint_url 从 default_config.yaml 读取
    DYNAMODB_ENDPOINT_URL: Optional[str] = _aws_config.get('endpoint_url') or None
    DYNAMODB_TABLE_PREFIX: str = "nexus_"
    
    # SQS Configuration - endpoint_url 从 default_config.yaml 读取
    SQS_ENDPOINT_URL: Optional[str] = _aws_config.get('endpoint_url') or None
    SQS_BUILD_QUEUE_NAME: str = "nexus-build-queue"
    SQS_DEPLOY_QUEUE_NAME: str = "nexus-deploy-queue"
    SQS_NOTIFICATION_QUEUE_NAME: str = "nexus-notification-queue"
    SQS_BUILD_DLQ_NAME: str = "nexus-build-dlq"
    SQS_DEPLOY_DLQ_NAME: str = "nexus-deploy-dlq"
    
    # Build Configuration
    BUILD_VISIBILITY_TIMEOUT: int = 3600  # 1 hour
    DEPLOY_VISIBILITY_TIMEOUT: int = 600  # 10 minutes
    MESSAGE_RETENTION_DAYS: int = 7
    MAX_RETRY_COUNT: int = 3
    
    # AgentCore Deployment Configuration - 从 default_config.yaml 读取默认值
    AGENTCORE_REGION: Optional[str] = _aws_config.get('aws_region_name', 'us-west-2')
    AGENTCORE_DEPLOY_DRY_RUN: bool = _agentcore_config.get('deploy_dry_run', False)
    AGENTCORE_DEFAULT_ALIAS: str = _agentcore_config.get('default_alias', 'DEFAULT')
    AGENTCORE_EXECUTION_ROLE_NAME: Optional[str] = _agentcore_config.get('execution_role_arn') or None
    AGENTCORE_AUTO_CREATE_EXECUTION_ROLE: bool = _agentcore_config.get('auto_create_execution_role', True)
    AGENTCORE_AUTO_CREATE_ECR: bool = _agentcore_config.get('ecr_auto_create', True)
    AGENTCORE_POST_DEPLOY_TEST: bool = _agentcore_config.get('post_deploy_test', False)
    AGENTCORE_POST_DEPLOY_TEST_PROMPT: str = _agentcore_config.get('post_deploy_test_prompt', 'Hello')
    AGENTCORE_AUTO_UPDATE_ON_CONFLICT: bool = _agentcore_config.get('auto_update_on_conflict', True)
    AGENTCORE_REQUIREMENTS_PATH: str = "requirements.txt"
    AGENTCORE_IMAGE_TAG_TEMPLATE: str = "{agent_name}:{timestamp}"
    
    # Session Storage Configuration - 从 default_config.yaml 读取
    SESSION_STORAGE_S3_BUCKET: Optional[str] = _nexus_ai_config.get('session_storage_s3_bucket') or None
    SESSION_STORAGE_S3_PREFIX: str = "sessions/"  # S3 存储前缀
    
    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()


# Table names with prefix
TABLE_PROJECTS = f"{settings.DYNAMODB_TABLE_PREFIX}projects"
TABLE_STAGES = f"{settings.DYNAMODB_TABLE_PREFIX}stages"
TABLE_AGENTS = f"{settings.DYNAMODB_TABLE_PREFIX}agents"
TABLE_INVOCATIONS = f"{settings.DYNAMODB_TABLE_PREFIX}invocations"
TABLE_SESSIONS = f"{settings.DYNAMODB_TABLE_PREFIX}sessions"
TABLE_MESSAGES = f"{settings.DYNAMODB_TABLE_PREFIX}messages"
TABLE_TASKS = f"{settings.DYNAMODB_TABLE_PREFIX}tasks"
TABLE_TOOLS = f"{settings.DYNAMODB_TABLE_PREFIX}tools"

# All table names for iteration
ALL_TABLES = [
    TABLE_PROJECTS,
    TABLE_STAGES,
    TABLE_AGENTS,
    TABLE_INVOCATIONS,
    TABLE_SESSIONS,
    TABLE_MESSAGES,
    TABLE_TASKS,
    TABLE_TOOLS,
]

# All queue names
ALL_QUEUES = [
    settings.SQS_BUILD_QUEUE_NAME,
    settings.SQS_DEPLOY_QUEUE_NAME,
    settings.SQS_NOTIFICATION_QUEUE_NAME,
    settings.SQS_BUILD_DLQ_NAME,
    settings.SQS_DEPLOY_DLQ_NAME,
]
