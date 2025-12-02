"""
DynamoDB client and table management
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json
import time
import asyncio
from functools import wraps
import threading
from decimal import Decimal

from api.core.config import settings
from api.core.exceptions import APIException
from api.models.schemas import (
    ProjectRecord,
    StageRecord,
    AgentRecord,
    AgentInvocationRecord,
    ArtifactRecord,
    ProjectStatus,
    StageStatus,
    AgentStatus,
    BuildStage,
    StageData,
    AgentSessionRecord,
    AgentSessionMessageRecord,
    create_stage_data,
    build_initial_stage_snapshot,
    get_all_stages,
)

logger = logging.getLogger(__name__)

def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying DynamoDB operations on transient errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ClientError, BotoCoreError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    # Check if error is retryable
                    if isinstance(e, ClientError):
                        error_code = e.response.get('Error', {}).get('Code', '')
                        if error_code in ['ProvisionedThroughputExceededException', 
                                        'ThrottlingException', 
                                        'ServiceUnavailable',
                                        'InternalServerError']:
                            wait_time = delay * (backoff ** attempt)
                            logger.warning(f"Retryable error {error_code}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                            time.sleep(wait_time)
                            continue
                    
                    # Non-retryable error, re-raise immediately
                    raise e
                except Exception as e:
                    # Non-AWS errors, re-raise immediately
                    raise e
            
            # All retries exhausted
            logger.error(f"All retries exhausted for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator

class DynamoDBClient:
    """DynamoDB client for Nexus-AI Platform API with connection pooling and error handling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for DynamoDB client"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DynamoDBClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # Configure boto3 with connection pooling and retry settings
        config = Config(
            region_name=settings.DYNAMODB_REGION,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            connect_timeout=10,
            read_timeout=30
        )
        
        # Initialize DynamoDB resource with enhanced configuration
        # In ECS/Fargate, use IAM role if credentials are not explicitly provided
        # This allows boto3 to automatically use the task's IAM role
        session_kwargs = {
            'region_name': settings.DYNAMODB_REGION
        }
        
        # Only provide explicit credentials if they are set (for local development)
        # In production on ECS, boto3 will automatically use the task's IAM role
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        session = boto3.Session(**session_kwargs)
        
        self.dynamodb = session.resource(
            'dynamodb',
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL,
            config=config
        )
        
        # Initialize DynamoDB client for low-level operations
        self.dynamodb_client = session.client(
            'dynamodb',
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL,
            config=config
        )
        
        # Table references - will be initialized lazily
        self._projects_table = None
        self._agents_table = None
        self._invocations_table = None
        self._agent_sessions_table = None
        self._agent_session_messages_table = None
        
        # Connection health tracking
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
        
        self._initialized = True
        logger.info("DynamoDB client initialized with connection pooling")
    
    @property
    def projects_table(self):
        """Lazy initialization of projects table"""
        if self._projects_table is None:
            self._projects_table = self.dynamodb.Table('AgentProjects')
        return self._projects_table
    
    @property
    def agents_table(self):
        """Lazy initialization of agents table"""
        if self._agents_table is None:
            self._agents_table = self.dynamodb.Table('AgentInstances')
        return self._agents_table

    @property
    def invocations_table(self):
        """Lazy initialization of agent invocations table"""
        if self._invocations_table is None:
            self._invocations_table = self.dynamodb.Table('AgentInvocations')
        return self._invocations_table

    @property
    def agent_sessions_table(self):
        """Lazy initialization of agent sessions table"""
        if self._agent_sessions_table is None:
            self._agent_sessions_table = self.dynamodb.Table('AgentSessions')
        return self._agent_sessions_table

    @property
    def agent_session_messages_table(self):
        """Lazy initialization of agent session messages table"""
        if self._agent_session_messages_table is None:
            self._agent_session_messages_table = self.dynamodb.Table('AgentSessionMessages')
        return self._agent_session_messages_table

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def health_check(self) -> bool:
        """Check DynamoDB connection health"""
        try:
            current_time = time.time()
            if (self._last_health_check is None or 
                current_time - self._last_health_check > self._health_check_interval):
                
                # Simple health check - list tables
                response = self.dynamodb_client.list_tables(Limit=1)
                self._last_health_check = current_time
                logger.debug("DynamoDB health check passed")
                return True
            return True
        except Exception as e:
            logger.error(f"DynamoDB health check failed: {str(e)}")
            return False
    
    def _ensure_connection(self):
        """Ensure DynamoDB connection is healthy"""
        if not self.health_check():
            logger.warning("DynamoDB connection unhealthy, attempting to reconnect")
            # Reset table references to force reconnection
            self._projects_table = None
            self._agents_table = None
            self._invocations_table = None
            self._agent_sessions_table = None
            self._agent_session_messages_table = None

            # Force health check
            self._last_health_check = None
            if not self.health_check():
                raise APIException("Failed to establish DynamoDB connection")
    
    def create_tables(self):
        """Create DynamoDB tables if they don't exist"""
        try:
            self._create_projects_table()
            self._create_agents_table()
            self._create_invocations_table()
            self._create_agent_sessions_table()
            self._create_agent_session_messages_table()
            logger.info("DynamoDB tables created successfully")
        except Exception as e:
            logger.error(f"Error creating DynamoDB tables: {str(e)}")
            raise APIException(f"Failed to create database tables: {str(e)}")
    
    def _create_projects_table(self):
        """Create AgentProjects table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentProjects',
                KeySchema=[
                    {
                        'AttributeName': 'project_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'status',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'UserIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'StatusIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'status',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("AgentProjects table already exists")
                return self.projects_table
            raise
    
    def _create_agents_table(self):
        """Create AgentInstances table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentInstances',
                KeySchema=[
                    {
                        'AttributeName': 'agent_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'agent_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'status',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'category',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'ProjectIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'project_id',
                                'KeyType': 'HASH'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'StatusIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'status',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    },
                    {
                        'IndexName': 'CategoryIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'category',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("AgentInstances table already exists")
                return self.agents_table
            raise

    def _create_invocations_table(self):
        """Create AgentInvocations table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentInvocations',
                KeySchema=[
                    {
                        'AttributeName': 'invocation_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'invocation_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'agent_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'AgentInvocationIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'agent_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'timestamp',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("AgentInvocations table already exists")
                return self.invocations_table
            raise


    def _create_agent_sessions_table(self):
        """Create AgentSessions table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentSessions',
                KeySchema=[
                    {
                        'AttributeName': 'agent_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'session_id',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'agent_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'session_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'last_active_at',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'LastActiveIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'agent_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'last_active_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("AgentSessions table already exists")
                return self.agent_sessions_table
            raise

    def _create_agent_session_messages_table(self):
        """Create AgentSessionMessages table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentSessionMessages',
                KeySchema=[
                    {
                        'AttributeName': 'session_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'created_at',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'session_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("AgentSessionMessages table already exists")
                return self.agent_session_messages_table
            raise
    
    # Project operations

    # Agent session operations
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_agent_session(self, session: AgentSessionRecord) -> None:
        """Create a new agent session record."""
        try:
            self._ensure_connection()
            item = self._serialize_item(session.dict())
            self.agent_sessions_table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Error creating agent session {session.session_id}: {str(e)}")
            raise APIException(f"Failed to create agent session: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def get_agent_session(self, agent_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific agent session."""
        try:
            self._ensure_connection()
            response = self.agent_sessions_table.get_item(Key={'agent_id': agent_id, 'session_id': session_id})
            item = response.get('Item')
            return self._deserialize_item(item) if item else None
        except Exception as e:
            logger.error(f"Error fetching agent session {session_id} for agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to fetch agent session: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_agent_sessions(
        self,
        agent_id: str,
        limit: int = 50,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        descending: bool = True,
    ) -> Dict[str, Any]:
        """List sessions for an agent ordered by last activity."""
        try:
            self._ensure_connection()
            query_kwargs = {
                'KeyConditionExpression': Key('agent_id').eq(agent_id),
                'Limit': limit,
                'ScanIndexForward': not descending,
            }
            if last_evaluated_key:
                query_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = self.agent_sessions_table.query(**query_kwargs)
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return {
                'items': items,
                'last_evaluated_key': response.get('LastEvaluatedKey'),
            }
        except Exception as e:
            logger.error(f"Error listing sessions for agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to list agent sessions: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_agent_session_activity(
        self,
        agent_id: str,
        session_id: str,
        *,
        last_active_at: Optional[datetime] = None,
    ) -> None:
        """Update session last active timestamp."""
        try:
            self._ensure_connection()
            timestamp = last_active_at or datetime.utcnow().replace(tzinfo=timezone.utc)
            iso_value = timestamp.isoformat().replace('+00:00', 'Z')
            self.agent_sessions_table.update_item(
                Key={'agent_id': agent_id, 'session_id': session_id},
                UpdateExpression="SET last_active_at = :last_active",
                ExpressionAttributeValues={':last_active': iso_value},
            )
        except Exception as e:
            logger.error(f"Error updating activity for session {session_id}: {str(e)}")
            raise APIException(f"Failed to update session activity: {str(e)}")

    # Agent session messages
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def append_session_message(self, message: AgentSessionMessageRecord) -> None:
        """Append a message to a session."""
        try:
            self._ensure_connection()
            item = self._serialize_item(message.dict())
            self.agent_session_messages_table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Error appending message {message.message_id} to session {message.session_id}: {str(e)}")
            raise APIException(f"Failed to append session message: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_session_messages(
        self,
        session_id: str,
        limit: int = 200,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
        ascending: bool = True,
    ) -> Dict[str, Any]:
        """List messages for a session."""
        try:
            self._ensure_connection()
            query_kwargs = {
                'KeyConditionExpression': Key('session_id').eq(session_id),
                'Limit': limit,
                'ScanIndexForward': ascending,
            }
            if last_evaluated_key:
                query_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = self.agent_session_messages_table.query(**query_kwargs)
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return {
                'items': items,
                'last_evaluated_key': response.get('LastEvaluatedKey'),
            }
        except Exception as e:
            logger.error(f"Error listing messages for session {session_id}: {str(e)}")
            raise APIException(f"Failed to list session messages: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_project(self, project_data: ProjectRecord) -> None:
        """Create a new project record"""
        try:
            self._ensure_connection()
            item = self._serialize_item(project_data.dict())
            
            self.projects_table.put_item(Item=item)
            logger.info(f"Created project record: {project_data.project_id}")
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise APIException(f"Failed to create project record: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        try:
            self._ensure_connection()
            response = self.projects_table.get_item(
                Key={'project_id': project_id}
            )
            item = response.get('Item')
            return self._deserialize_item(item) if item else None
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            raise APIException(f"Failed to get project: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_project_status(self, project_id: str, status: Union[str, ProjectStatus], **kwargs) -> None:
        """Update project status and other fields"""
        try:
            self._ensure_connection()
            
            # Convert enum to string if needed
            if isinstance(status, ProjectStatus):
                status = status.value
            
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_values = {
                ':status': status,
                ':updated_at': datetime.utcnow().isoformat() + "Z"
            }
            expression_names = {'#status': 'status'}
            
            # Add optional fields
            for key, value in kwargs.items():
                if value is not None:
                    if isinstance(value, datetime):
                        value = value.isoformat() + "Z"
                    elif isinstance(value, (ProjectStatus, StageStatus, AgentStatus, BuildStage)):
                        value = value.value
                    elif isinstance(value, dict):
                        value = json.dumps(value, default=str)
                    
                    # Handle reserved keywords
                    attr_name = f"#{key}" if key in ['status', 'data', 'timestamp'] else key
                    update_expression += f", {attr_name} = :{key}"
                    expression_values[f":{key}"] = value
                    if attr_name.startswith('#'):
                        expression_names[attr_name] = key
            
            self.projects_table.update_item(
                Key={'project_id': project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None
            )
            logger.info(f"Updated project {project_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating project status: {str(e)}")
            raise APIException(f"Failed to update project status: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_projects_by_user(self, user_id: str, limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        """List projects by user with pagination"""
        try:
            self._ensure_connection()
            
            query_kwargs = {
                'IndexName': 'UserIndex',
                'KeyConditionExpression': Key('user_id').eq(user_id),
                'ScanIndexForward': False,  # Sort by created_at descending
                'Limit': limit
            }
            
            if last_key:
                query_kwargs['ExclusiveStartKey'] = {'user_id': user_id, 'created_at': last_key}
            
            response = self.projects_table.query(**query_kwargs)
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('created_at'),
                'count': len(items)
            }
        except Exception as e:
            logger.error(f"Error listing projects for user {user_id}: {str(e)}")
            raise APIException(f"Failed to list projects: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_projects_by_status(self, status: Union[str, ProjectStatus], limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        """List projects by status with pagination"""
        try:
            self._ensure_connection()
            
            # Convert enum to string if needed
            if isinstance(status, ProjectStatus):
                status = status.value
            
            query_kwargs = {
                'IndexName': 'StatusIndex',
                'KeyConditionExpression': Key('status').eq(status),
                'ScanIndexForward': False,  # Sort by created_at descending
                'Limit': limit
            }
            
            if last_key:
                query_kwargs['ExclusiveStartKey'] = {'status': status, 'created_at': last_key}
            
            response = self.projects_table.query(**query_kwargs)
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('created_at'),
                'count': len(items)
            }
        except Exception as e:
            logger.error(f"Error listing projects by status {status}: {str(e)}")
            raise APIException(f"Failed to list projects by status: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_projects(
        self,
        limit: int = 20,
        last_key: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Scan projects table with optional filters."""

        try:
            self._ensure_connection()

            collected: List[Dict[str, Any]] = []
            scanned = 0
            exclusive_start_key = last_key

            status_filter = None
            if filters and filters.get('status'):
                status_value = filters['status']
                if isinstance(status_value, ProjectStatus):
                    status_value = status_value.value
                status_filter = str(status_value)

            user_filter = str(filters.get('user_id', '')).strip() if filters else ''
            search_filter = str(filters.get('search', '')).strip().lower() if filters else ''

            while len(collected) < limit:
                scan_kwargs: Dict[str, Any] = {
                    'Limit': limit,
                }

                if exclusive_start_key:
                    scan_kwargs['ExclusiveStartKey'] = exclusive_start_key

                response = self.projects_table.scan(**scan_kwargs)
                items = response.get('Items', [])
                scanned += len(items)

                for item in items:
                    project = self._deserialize_item(item)

                    if status_filter and str(project.get('status')) != status_filter:
                        continue
                    if user_filter and str(project.get('user_id', '')).strip() != user_filter:
                        continue
                    if search_filter:
                        searchable = ' '.join(
                            str(project.get(field, '') or '')
                            for field in ('project_id', 'project_name', 'tags')
                        ).lower()
                        if search_filter not in searchable:
                            continue

                    collected.append(project)
                    if len(collected) >= limit:
                        break

                exclusive_start_key = response.get('LastEvaluatedKey')
                if not exclusive_start_key:
                    break

            last_evaluated = exclusive_start_key.get('project_id') if exclusive_start_key else None

            return {
                'items': collected[:limit],
                'last_key': last_evaluated,
                'count': len(collected[:limit]),
                'scanned_count': scanned,
            }
        except Exception as exc:
            logger.error(f"Error scanning projects: {exc}")
            raise APIException(f"Failed to list projects: {exc}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def delete_project(self, project_id: str) -> bool:
        """Delete a project record"""
        try:
            self._ensure_connection()
            
            # Check if project exists first
            existing = self.get_project(project_id)
            if not existing:
                return False
            
            self.projects_table.delete_item(
                Key={'project_id': project_id}
            )
            logger.info(f"Deleted project record: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise APIException(f"Failed to delete project: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_project_progress(self, project_id: str, progress_percentage: float, 
                              current_stage: Optional[Union[BuildStage, int]] = None,
                              estimated_completion: Optional[datetime] = None) -> None:
        """Update project progress information"""
        try:
            self._ensure_connection()
            
            update_expression = "SET progress_percentage = :progress, updated_at = :updated_at"
            expression_values = {
                ':progress': Decimal(str(progress_percentage)),  # Convert float to Decimal
                ':updated_at': datetime.utcnow().isoformat() + "Z"
            }
            expression_names = {}
            
            if current_stage is not None:
                if isinstance(current_stage, BuildStage):
                    stage_number = BuildStage.get_stage_number(current_stage)
                    stage_value = current_stage.value
                elif isinstance(current_stage, int):
                    stage_number = current_stage
                    stage_value = BuildStage.get_stage_by_number(current_stage).value
                else:
                    raise ValueError(f"Invalid current_stage type: {type(current_stage)}")
                
                update_expression += ", current_stage = :current_stage, current_stage_number = :stage_number"
                expression_values[':current_stage'] = stage_value
                expression_values[':stage_number'] = Decimal(stage_number)  # Convert int to Decimal
            
            if estimated_completion:
                update_expression += ", estimated_completion = :estimated_completion"
                expression_values[':estimated_completion'] = estimated_completion.isoformat() + "Z"

            # Build update_item parameters conditionally
            update_params = {
                'Key': {'project_id': project_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values
            }
            # Only add ExpressionAttributeNames if it has content
            if expression_names:
                update_params['ExpressionAttributeNames'] = expression_names

            self.projects_table.update_item(**update_params)
            logger.info(f"Updated project {project_id} progress to {progress_percentage}%")
        except Exception as e:
            logger.error(f"Error updating project progress: {str(e)}")
            raise APIException(f"Failed to update project progress: {str(e)}")

    # Build stages operations
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_stage_record(self, stage_data: StageRecord) -> None:
        """Create or replace a stage snapshot entry for a project."""
        try:
            self._ensure_connection()
            payload = self._stage_record_to_snapshot(stage_data)
            self._upsert_stage_snapshot(
                stage_data.project_id,
                stage_data.stage,
                payload,
                replace=True,
            )
            logger.info(
                "Created stage snapshot for project %s stage %s",
                stage_data.project_id,
                stage_data.stage.value,
            )
        except Exception as e:
            logger.error(f"Error creating stage record: {str(e)}")
            raise APIException(f"Failed to create stage record: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def get_stage_record(self, project_id: str, stage_number: int) -> Optional[Dict[str, Any]]:
        """Get stage snapshot entry by project ID and stage number."""
        try:
            project = self.get_project(project_id)
            if not project:
                return None
            
            stage = BuildStage.get_stage_by_number(stage_number)
            snapshot = project.get('stages_snapshot') or {}
            
            # 新格式：从stages列表中查找 - 支持新格式(stage_name)和旧格式(name)
            if isinstance(snapshot, dict) and 'stages' in snapshot:
                stages_list = snapshot.get('stages', [])
                for s in stages_list:
                    s_name = s.get('stage_name') or s.get('name')
                    if s_name == stage.value:
                        return s
                return None
            
            # 格式不正确
            logger.warning(f"Project {project_id} has invalid stages_snapshot format")
            return None
        except Exception as e:
            logger.error(f"Error getting stage record {project_id}-{stage_number}: {str(e)}")
            raise APIException(f"Failed to get stage record: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_project_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """
        列出项目的所有阶段
        
        返回格式: stages_snapshot.stages 列表
        """
        try:
            project = self.get_project(project_id)
            if not project:
                return []

            snapshot = project.get('stages_snapshot') or {}
            
            # 新格式：stages_snapshot包含stages列表
            if isinstance(snapshot, dict) and 'stages' in snapshot:
                return snapshot['stages']
            
            # 如果没有stages字段，返回空列表
            logger.warning(f"Project {project_id} has invalid stages_snapshot format")
            return []
        except Exception as e:
            logger.error(f"Error listing stages for project {project_id}: {str(e)}")
            raise APIException(f"Failed to list project stages: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_stage_status(self, project_id: str, stage_number: int,
                           status: Union[str, StageStatus], **kwargs) -> None:
        """Update stage status within the project snapshot."""
        try:
            self._ensure_connection()

            stage = BuildStage.get_stage_by_number(stage_number)
            stage_status = status.value if isinstance(status, StageStatus) else status

            payload: Dict[str, Any] = {
                'status': stage_status,
            }

            logs = kwargs.get('logs')
            if logs:
                payload['logs'] = logs

            if 'output_data' in kwargs and kwargs['output_data'] is not None:
                payload['output_data'] = kwargs['output_data']

            if 'error_message' in kwargs and kwargs['error_message'] is not None:
                payload['error_message'] = kwargs['error_message']

            now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')

            if stage_status == StageStatus.RUNNING.value:
                started_at = kwargs.get('started_at')
                payload['started_at'] = self._datetime_to_iso(started_at) or now
            elif stage_status == StageStatus.COMPLETED.value:
                completed_at = kwargs.get('completed_at')
                payload['completed_at'] = self._datetime_to_iso(completed_at) or now

            if 'duration_seconds' in kwargs and kwargs['duration_seconds'] is not None:
                payload['duration_seconds'] = kwargs['duration_seconds']

            self._upsert_stage_snapshot(
                project_id,
                stage,
                payload,
                append_logs=bool(logs),
            )
            logger.info(
                "Updated stage snapshot for project %s stage %s -> %s",
                project_id,
                stage.value,
                stage_status,
            )
        except Exception as e:
            logger.error(f"Error updating stage status: {str(e)}")
            raise APIException(f"Failed to update stage status: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def add_stage_log(self, project_id: str, stage_number: int, log_message: str) -> None:
        """Add a log message to a stage"""
        try:
            self._ensure_connection()

            timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            stage = BuildStage.get_stage_by_number(stage_number)
            self._upsert_stage_snapshot(
                project_id,
                stage,
                {'logs': [f"[{timestamp}] {log_message}"]},
                append_logs=True,
            )
            logger.debug("Added log to stage %s-%s: %s", project_id, stage_number, log_message)
        except Exception as e:
            logger.error(f"Error adding stage log: {str(e)}")
            raise APIException(f"Failed to add stage log: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def initialize_project_stages(
        self,
        project_id: str,
        *,
        agent_name_map: Optional[Dict[BuildStage, Optional[str]]] = None,
    ) -> None:
        """
        初始化项目的所有6个阶段（使用新的完整格式）
        
        新格式包含:
        - total: 总阶段数
        - completed: 已完成阶段数
        - stages: 阶段列表（包含所有详细信息、日志、输出数据、子阶段）
        """
        try:
            self._ensure_connection()
            snapshot = build_initial_stage_snapshot(
                include_agent_names=agent_name_map is not None,
                agent_name_map=agent_name_map,
            )
            serialized_snapshot = json.dumps(snapshot, default=str)
            self.projects_table.update_item(
                Key={'project_id': project_id},
                UpdateExpression="SET stages_snapshot = :snapshot, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ':snapshot': serialized_snapshot,
                    ':updated_at': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            )
            logger.info("Initialized complete stage snapshot for project %s with %d stages", project_id, snapshot['total'])
        except Exception as e:
            logger.error(f"Error initializing project stages: {str(e)}")
            raise APIException(f"Failed to initialize project stages: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def get_current_stage(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the current active stage for a project"""
        try:
            stages = self.list_project_stages(project_id)
            
            # Find the first non-completed stage
            for stage in stages:
                if stage.get('status') != StageStatus.COMPLETED.value:
                    return stage
            
            # All stages completed, return the last stage
            return stages[-1] if stages else None
        except Exception as e:
            logger.error(f"Error getting current stage for project {project_id}: {str(e)}")
            raise APIException(f"Failed to get current stage: {str(e)}")    

    # ------------------------------------------------------------------
    # Internal helpers for stage snapshot management
    # ------------------------------------------------------------------

    @staticmethod
    def _datetime_to_iso(value: Optional[Union[str, datetime]]) -> Optional[str]:
        """Convert datetime or ISO string to standardized ISO format with Z suffix."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if value.tzinfo:
            return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None

    def _stage_record_to_snapshot(self, stage_record: StageRecord) -> Dict[str, Any]:
        stage_data = StageData(
            stage=stage_record.stage,
            stage_number=stage_record.stage_number,
            stage_name=stage_record.stage_name,
            stage_name_cn=stage_record.stage_name_cn,
            status=stage_record.status,
            started_at=stage_record.started_at,
            completed_at=stage_record.completed_at,
            duration_seconds=stage_record.duration_seconds,
            agent_name=stage_record.agent_name,
            output_data=stage_record.output_data,
            error_message=stage_record.error_message,
            logs=stage_record.logs,
        )
        return stage_data.model_dump(mode="json")

    def _upsert_stage_snapshot(
        self,
        project_id: str,
        stage: BuildStage,
        payload: Dict[str, Any],
        *,
        replace: bool = False,
        append_logs: bool = False,
    ) -> None:
        """
        更新阶段快照（仅支持新格式）
        
        格式: stages_snapshot.stages 是一个列表
        """
        project = self.get_project(project_id)
        if not project:
            raise APIException(f"Project {project_id} not found for stage update")

        snapshot = project.get('stages_snapshot')
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = {}
        if snapshot is None:
            snapshot = {}

        # 确保是新格式
        if not isinstance(snapshot, dict) or 'stages' not in snapshot:
            raise APIException(f"Project {project_id} has invalid stages_snapshot format. Expected format with 'stages' list.")
        
        # 在stages列表中查找并更新（只支持新格式：stage_name）
        stages_list = snapshot.get('stages', [])
        stage_index = None
        existing = None

        # 查找目标阶段 - 使用 stage_name 字段
        for i, s in enumerate(stages_list):
            if s.get('stage_name') == stage.value:
                stage_index = i
                existing = s
                break

        # 如果没找到，创建新条目
        if existing is None:
            base_entry = create_stage_data(stage, StageStatus.PENDING, logs=[]).model_dump(mode="json")
            existing = base_entry
            stages_list.append(existing)
            stage_index = len(stages_list) - 1
        
        # 准备更新的条目
        entry = create_stage_data(stage, StageStatus.PENDING, logs=[]).model_dump(mode="json") if replace else existing.copy()
        
        if not replace:
            entry.update(existing)
        
        # 处理日志
        if append_logs:
            new_logs = payload.get('logs') or []
            existing_logs = entry.get('logs') or []
            entry['logs'] = existing_logs + new_logs
        elif 'logs' in payload and payload['logs'] is not None:
            entry['logs'] = payload['logs']
        
        # 更新其他字段
        for key, value in payload.items():
            if key == 'logs' and append_logs:
                continue
            if value is None:
                continue
            if isinstance(value, StageStatus):
                entry[key] = value.value
            elif isinstance(value, BuildStage):
                entry[key] = value.value
            else:
                entry[key] = value
        
        # 计算duration_seconds
        if entry.get('status') == StageStatus.COMPLETED.value and 'completed_at' in entry:
            start_dt = self._parse_datetime(entry.get('started_at'))
            end_dt = self._parse_datetime(entry.get('completed_at'))
            if start_dt and end_dt:
                entry['duration_seconds'] = int(max((end_dt - start_dt).total_seconds(), 0))
        
        # 更新列表中的条目
        stages_list[stage_index] = entry
        
        # 更新completed计数
        completed_count = sum(1 for s in stages_list if s.get('status') == 'completed')
        snapshot['completed'] = completed_count

        serialized_snapshot = json.dumps(snapshot, default=str)
        self.projects_table.update_item(
            Key={'project_id': project_id},
            UpdateExpression="SET stages_snapshot = :snapshot, updated_at = :updated_at",
            ExpressionAttributeValues={
                ':snapshot': serialized_snapshot,
                ':updated_at': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        )
   
 # Agent instances operations
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_agent_record(self, agent_data: AgentRecord) -> None:
        """Create a new agent record"""
        try:
            self._ensure_connection()
            item = self._serialize_item(agent_data.dict())
            
            self.agents_table.put_item(Item=item)
            logger.info(f"Created agent record: {agent_data.agent_id}")
        except Exception as e:
            logger.error(f"Error creating agent record: {str(e)}")
            raise APIException(f"Failed to create agent record: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def get_agent_record(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent record by ID"""
        try:
            self._ensure_connection()
            response = self.agents_table.get_item(
                Key={'agent_id': agent_id}
            )
            item = response.get('Item')
            return self._deserialize_item(item) if item else None
        except Exception as e:
            logger.error(f"Error getting agent record {agent_id}: {str(e)}")
            raise APIException(f"Failed to get agent record: {str(e)}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID (alias for get_agent_record)"""
        return self.get_agent_record(agent_id)
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_agents(self, limit: int = 20, last_key: Optional[str] = None, 
                   filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List agents with pagination and optional filters"""
        try:
            self._ensure_connection()
            
            scan_kwargs = {
                'Limit': limit
            }
            
            if last_key:
                scan_kwargs['ExclusiveStartKey'] = {'agent_id': last_key}
            
            # Apply filters
            if filters:
                filter_expressions = []
                expression_values = {}
                expression_names = {}
                
                for key, value in filters.items():
                    if value is not None:
                        if key == 'status':
                            if isinstance(value, AgentStatus):
                                value = value.value
                            filter_expressions.append('#status = :status')
                            expression_values[':status'] = value
                            expression_names['#status'] = 'status'
                        elif key == 'category':
                            filter_expressions.append('category = :category')
                            expression_values[':category'] = value
                        elif key == 'project_id':
                            filter_expressions.append('project_id = :project_id')
                            expression_values[':project_id'] = value
                        elif key == 'search':
                            # Search in agent_name and description
                            filter_expressions.append('(contains(agent_name, :search) OR contains(description, :search))')
                            expression_values[':search'] = value
                
                if filter_expressions:
                    scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
                    scan_kwargs['ExpressionAttributeValues'] = expression_values
                    if expression_names:
                        scan_kwargs['ExpressionAttributeNames'] = expression_names
            
            response = self.agents_table.scan(**scan_kwargs)
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('agent_id'),
                'count': len(items),
                'scanned_count': response.get('ScannedCount', 0)
            }
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            raise APIException(f"Failed to list agents: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_agents_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List all agents for a specific project"""
        try:
            self._ensure_connection()
            response = self.agents_table.query(
                IndexName='ProjectIndex',
                KeyConditionExpression=Key('project_id').eq(project_id)
            )
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return items
        except Exception as e:
            logger.error(f"Error listing agents for project {project_id}: {str(e)}")
            raise APIException(f"Failed to list agents by project: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_agents_by_category(self, category: str, limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        """List agents by category with pagination"""
        try:
            self._ensure_connection()
            
            query_kwargs = {
                'IndexName': 'CategoryIndex',
                'KeyConditionExpression': Key('category').eq(category),
                'ScanIndexForward': False,  # Sort by created_at descending
                'Limit': limit
            }
            
            if last_key:
                query_kwargs['ExclusiveStartKey'] = {'category': category, 'created_at': last_key}
            
            response = self.agents_table.query(**query_kwargs)
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('created_at'),
                'count': len(items)
            }
        except Exception as e:
            logger.error(f"Error listing agents by category {category}: {str(e)}")
            raise APIException(f"Failed to list agents by category: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_agent_status(self, agent_id: str, status: Union[str, AgentStatus], **kwargs) -> None:
        """Update agent status and other fields"""
        try:
            self._ensure_connection()
            
            # Convert enum to string if needed
            if isinstance(status, AgentStatus):
                status = status.value
            
            update_expression = "SET #status = :status"
            expression_values = {':status': status}
            expression_names = {'#status': 'status'}
            
            # Add optional fields
            for key, value in kwargs.items():
                if value is not None:
                    if isinstance(value, datetime):
                        iso_value = value.astimezone(timezone.utc).isoformat()
                        if iso_value.endswith("+00:00"):
                            iso_value = iso_value[:-6] + "Z"
                        value = iso_value
                    elif isinstance(value, (ProjectStatus, StageStatus, AgentStatus, BuildStage)):
                        value = value.value
                    elif isinstance(value, (dict, list)):
                        value = json.dumps(value, default=str)

                    attr_name = f"#attr_{key}"
                    update_expression += f", {attr_name} = :{key}"
                    expression_values[f":{key}"] = value
                    expression_names[attr_name] = key
            
            self.agents_table.update_item(
                Key={'agent_id': agent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            logger.info(f"Updated agent {agent_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating agent status: {str(e)}")
            raise APIException(f"Failed to update agent status: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def update_agent_statistics(self, agent_id: str, call_count: Optional[int] = None, 
                               success_rate: Optional[float] = None, 
                               last_called_at: Optional[datetime] = None) -> None:
        """Update agent usage statistics"""
        try:
            self._ensure_connection()
            
            update_parts = []
            expression_values = {}
            
            if call_count is not None:
                update_parts.append("call_count = :call_count")
                expression_values[':call_count'] = call_count
            
            if success_rate is not None:
                update_parts.append("success_rate = :success_rate")
                expression_values[':success_rate'] = success_rate
            
            if last_called_at is not None:
                update_parts.append("last_called_at = :last_called_at")
                expression_values[':last_called_at'] = last_called_at.isoformat() + "Z"
            
            if not update_parts:
                return  # Nothing to update
            
            update_expression = "SET " + ", ".join(update_parts)
            
            self.agents_table.update_item(
                Key={'agent_id': agent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            logger.info(f"Updated agent {agent_id} statistics")
        except Exception as e:
            logger.error(f"Error updating agent statistics: {str(e)}")
            raise APIException(f"Failed to update agent statistics: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def delete_agent_record(self, agent_id: str) -> bool:
        """Delete an agent record"""
        try:
            self._ensure_connection()
            
            # Check if agent exists first
            existing = self.get_agent_record(agent_id)
            if not existing:
                return False
            
            self.agents_table.delete_item(
                Key={'agent_id': agent_id}
            )
            logger.info(f"Deleted agent record: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to delete agent: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def search_agents(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search agents by name, description, or tags"""
        try:
            self._ensure_connection()
            
            # Use scan with filter expression for text search
            response = self.agents_table.scan(
                FilterExpression=Attr('agent_name').contains(search_term) | 
                               Attr('description').contains(search_term) |
                               Attr('tags').contains(search_term),
                Limit=limit
            )
            
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return items
        except Exception as e:
            logger.error(f"Error searching agents: {str(e)}")
            raise APIException(f"Failed to search agents: {str(e)}")

    # Artifact operations (DEPRECATED - artifacts now stored in stages_snapshot)
    # These methods are retained as stubs to prevent crashes during refactoring

    def create_artifact_record(self, artifact: ArtifactRecord) -> None:
        """
        DEPRECATED: AgentArtifacts table has been removed per design specs.
        Artifacts are now stored in AgentProjects.stages_snapshot.
        This method is a no-op stub to prevent crashes.
        """
        logger.warning(
            "create_artifact_record called but AgentArtifacts table no longer exists. "
            "Artifacts should be stored in stages_snapshot. artifact_id=%s",
            artifact.artifact_id
        )
        # No-op - do nothing

    def list_artifacts_by_agent(self, agent_id: str, limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        """
        DEPRECATED: AgentArtifacts table has been removed per design specs.
        This method returns empty results to prevent crashes.
        """
        logger.warning(
            "list_artifacts_by_agent called but AgentArtifacts table no longer exists. "
            "Returning empty results. agent_id=%s",
            agent_id
        )
        return {
            'items': [],
            'last_key': None,
            'count': 0,
        }

    def list_artifacts_by_project(self, project_id: str, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        DEPRECATED: AgentArtifacts table has been removed per design specs.
        This method returns empty results to prevent crashes.
        """
        logger.warning(
            "list_artifacts_by_project called but AgentArtifacts table no longer exists. "
            "Returning empty results. project_id=%s stage=%s",
            project_id,
            stage
        )
        return []
        # No-op - do nothing

    # Invocation operations
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def log_agent_invocation(self, invocation: AgentInvocationRecord) -> None:
        try:
            self._ensure_connection()
            item = self._serialize_item(invocation.dict())
            self.invocations_table.put_item(Item=item)
            logger.debug("Logged invocation %s for agent %s", invocation.invocation_id, invocation.agent_id)
        except Exception as e:
            logger.error("Error logging agent invocation: %s", e)
            raise APIException(f"Failed to log agent invocation: {e}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_agent_invocations(self, agent_id: str, limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        try:
            self._ensure_connection()
            query_kwargs = {
                'IndexName': 'AgentInvocationIndex',
                'KeyConditionExpression': Key('agent_id').eq(agent_id),
                'ScanIndexForward': False,
                'Limit': limit,
            }
            if last_key:
                query_kwargs['ExclusiveStartKey'] = {'agent_id': agent_id, 'timestamp': last_key}
            response = self.invocations_table.query(**query_kwargs)
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('timestamp'),
                'count': len(items),
            }
        except Exception as e:
            logger.error("Error listing invocations for agent %s: %s", agent_id, e)
            raise APIException(f"Failed to list agent invocations: {e}")
    
    # Utility methods
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize item for DynamoDB storage"""
        serialized = {}
        for key, value in item.items():
            if value is not None:
                if isinstance(value, datetime):
                    iso_value = value.astimezone(timezone.utc).isoformat()
                    if iso_value.endswith("+00:00"):
                        iso_value = iso_value[:-6] + "Z"
                    serialized[key] = iso_value
                elif isinstance(value, (ProjectStatus, StageStatus, AgentStatus, BuildStage)):
                    serialized[key] = value.value
                elif isinstance(value, float):
                    serialized[key] = Decimal(str(value))
                elif isinstance(value, (dict, list)):
                    serialized[key] = json.dumps(value, default=str)
                else:
                    serialized[key] = value
        return serialized
    
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize item from DynamoDB storage"""
        if not item:
            return item
        
        deserialized = {}
        # Fields that are typically stored as JSON strings
        json_fields = [
            'agent_config', 'build_summary', 'error_info', 'output_data',
            'dependencies', 'supported_models', 'supported_inputs', 'tags', 'logs', 'config',
            'stages_snapshot', 'agents', 'artifact_paths', 'runtime_config', 'metadata'
        ]
        
        datetime_fields = {
            'created_at',
            'updated_at',
            'last_deployed_at',
            'completed_at',
            'started_at',
            'last_active_at',
            'last_called_at',
            'timestamp',
        }

        for key, value in item.items():
            # Convert Decimal to int or float
            if isinstance(value, Decimal):
                deserialized[key] = int(value) if value % 1 == 0 else float(value)
            elif isinstance(value, str) and key in datetime_fields:
                deserialized[key] = self._parse_datetime(value)
            elif isinstance(value, str) and key in json_fields:
                # Try to parse JSON strings for known JSON fields
                try:
                    deserialized[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    deserialized[key] = value
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                # Try to parse any string that looks like JSON
                try:
                    deserialized[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    deserialized[key] = value
            elif isinstance(value, dict):
                # Recursively deserialize nested dicts
                deserialized[key] = self._deserialize_item(value)
            else:
                deserialized[key] = value
        return deserialized

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        if not value:
            return None

        cleaned = value.strip()
        if cleaned.endswith('Z'):
            cleaned = cleaned[:-1]
            if not cleaned.endswith('+00:00'):
                cleaned = f"{cleaned}+00:00"
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None

# Global DynamoDB client instance
db_client = DynamoDBClient()
