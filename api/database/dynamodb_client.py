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
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.DYNAMODB_REGION
        )
        
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
        self._stages_table = None
        self._agents_table = None
        self._stats_table = None
        self._artifacts_table = None
        self._invocations_table = None
        
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
    def stages_table(self):
        """Lazy initialization of stages table"""
        if self._stages_table is None:
            self._stages_table = self.dynamodb.Table('BuildStages')
        return self._stages_table
    
    @property
    def agents_table(self):
        """Lazy initialization of agents table"""
        if self._agents_table is None:
            self._agents_table = self.dynamodb.Table('AgentInstances')
        return self._agents_table
    
    @property
    def stats_table(self):
        """Lazy initialization of statistics table"""
        if self._stats_table is None:
            self._stats_table = self.dynamodb.Table('BuildStatistics')
        return self._stats_table

    @property
    def artifacts_table(self):
        """Lazy initialization of artifacts table"""
        if self._artifacts_table is None:
            self._artifacts_table = self.dynamodb.Table('AgentArtifacts')
        return self._artifacts_table

    @property
    def invocations_table(self):
        """Lazy initialization of agent invocations table"""
        if self._invocations_table is None:
            self._invocations_table = self.dynamodb.Table('AgentInvocations')
        return self._invocations_table
    
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
            self._stages_table = None
            self._agents_table = None
            self._stats_table = None
            self._artifacts_table = None
            self._invocations_table = None
            
            # Force health check
            self._last_health_check = None
            if not self.health_check():
                raise APIException("Failed to establish DynamoDB connection")
    
    def create_tables(self):
        """Create DynamoDB tables if they don't exist"""
        try:
            self._create_projects_table()
            self._create_stages_table()
            self._create_agents_table()
            self._create_statistics_table()
            self._create_artifacts_table()
            self._create_invocations_table()
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
    
    def _create_stages_table(self):
        """Create BuildStages table"""
        try:
            table = self.dynamodb.create_table(
                TableName='BuildStages',
                KeySchema=[
                    {
                        'AttributeName': 'project_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'stage_number',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'stage_number',
                        'AttributeType': 'N'
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
                logger.info("BuildStages table already exists")
                return self.stages_table
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

    def _create_artifacts_table(self):
        """Create AgentArtifacts table"""
        try:
            table = self.dynamodb.create_table(
                TableName='AgentArtifacts',
                KeySchema=[
                    {
                        'AttributeName': 'artifact_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'artifact_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'agent_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'AgentIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'agent_id',
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
                        'IndexName': 'ProjectIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'project_id',
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
                logger.info("AgentArtifacts table already exists")
                return self.artifacts_table
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
    def _create_statistics_table(self):
        """Create BuildStatistics table"""
        try:
            table = self.dynamodb.create_table(
                TableName='BuildStatistics',
                KeySchema=[
                    {
                        'AttributeName': 'date',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'metric_type',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'date',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'metric_type',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info("BuildStatistics table already exists")
                return self.stats_table
            raise
    
    # Project operations
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
                ':progress': progress_percentage,
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
                expression_values[':stage_number'] = stage_number
            
            if estimated_completion:
                update_expression += ", estimated_completion = :estimated_completion"
                expression_values[':estimated_completion'] = estimated_completion.isoformat() + "Z"
            
            self.projects_table.update_item(
                Key={'project_id': project_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names if expression_names else None
            )
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
            entry = snapshot.get(stage.value)
            return entry
        except Exception as e:
            logger.error(f"Error getting stage record {project_id}-{stage_number}: {str(e)}")
            raise APIException(f"Failed to get stage record: {str(e)}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_project_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """List all stage snapshot entries for a project."""
        try:
            project = self.get_project(project_id)
            if not project:
                return []

            snapshot = project.get('stages_snapshot') or {}
            stages: List[Dict[str, Any]] = []
            for stage in get_all_stages():
                entry = snapshot.get(stage.value)
                if not entry:
                    entry = create_stage_data(stage, StageStatus.PENDING, logs=[]).model_dump(mode="json")
                stages.append(entry)
            return stages
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
        """Initialize all 8 stages for a project with PENDING status"""
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
            logger.info("Initialized stage snapshot for project %s", project_id)
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

        existing = snapshot.get(stage.value)
        if replace or not existing:
            base_entry = create_stage_data(stage, StageStatus.PENDING, logs=[]).model_dump(mode="json")
            existing = base_entry

        entry = create_stage_data(stage, StageStatus.PENDING, logs=[]).model_dump(mode="json") if replace else existing.copy()

        if not replace:
            entry.update(existing)

        if append_logs:
            new_logs = payload.get('logs') or []
            existing_logs = entry.get('logs') or []
            entry['logs'] = existing_logs + new_logs
        elif 'logs' in payload and payload['logs'] is not None:
            entry['logs'] = payload['logs']

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

        if entry.get('status') == StageStatus.COMPLETED.value and 'completed_at' in entry:
            start_dt = self._parse_datetime(entry.get('started_at'))
            end_dt = self._parse_datetime(entry.get('completed_at'))
            if start_dt and end_dt:
                entry['duration_seconds'] = int(max((end_dt - start_dt).total_seconds(), 0))

        snapshot[stage.value] = entry

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

    # Artifact operations
    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_artifact_record(self, artifact: ArtifactRecord) -> None:
        try:
            self._ensure_connection()
            item = self._serialize_item(artifact.dict())
            self.artifacts_table.put_item(Item=item)
            logger.debug("Created artifact record %s", artifact.artifact_id)
        except Exception as e:
            logger.error("Error creating artifact record: %s", e)
            raise APIException(f"Failed to create artifact record: {e}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_artifacts_by_agent(self, agent_id: str, limit: int = 20, last_key: Optional[str] = None) -> Dict[str, Any]:
        try:
            self._ensure_connection()
            query_kwargs = {
                'IndexName': 'AgentIndex',
                'KeyConditionExpression': Key('agent_id').eq(agent_id),
                'ScanIndexForward': False,
                'Limit': limit,
            }
            if last_key:
                query_kwargs['ExclusiveStartKey'] = {'agent_id': agent_id, 'created_at': last_key}
            response = self.artifacts_table.query(**query_kwargs)
            items = [self._deserialize_item(item) for item in response.get('Items', [])]
            return {
                'items': items,
                'last_key': response.get('LastEvaluatedKey', {}).get('created_at'),
                'count': len(items),
            }
        except Exception as e:
            logger.error("Error listing artifacts for agent %s: %s", agent_id, e)
            raise APIException(f"Failed to list artifacts: {e}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def list_artifacts_by_project(self, project_id: str, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            self._ensure_connection()
            query_kwargs = {
                'IndexName': 'ProjectIndex',
                'KeyConditionExpression': Key('project_id').eq(project_id),
                'ScanIndexForward': False,
            }
            if stage:
                query_kwargs['FilterExpression'] = Attr('stage').eq(stage)
            response = self.artifacts_table.query(**query_kwargs)
            items = response.get('Items', [])
            return [self._deserialize_item(item) for item in items]
        except Exception as e:
            logger.error("Error listing artifacts for project %s: %s", project_id, e)
            raise APIException(f"Failed to list artifacts: {e}")

    @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
    def delete_artifacts_for_stage(self, project_id: str, stage: str) -> None:
        try:
            self._ensure_connection()
            query_kwargs = {
                'IndexName': 'ProjectIndex',
                'KeyConditionExpression': Key('project_id').eq(project_id),
                'FilterExpression': Attr('stage').eq(stage),
            }
            response = self.artifacts_table.query(**query_kwargs)
            for item in response.get('Items', []):
                self.artifacts_table.delete_item(Key={'artifact_id': item['artifact_id']})
        except Exception as e:
            logger.error(
                "Error deleting artifacts for project %s stage %s: %s",
                project_id,
                stage,
                e,
            )
            raise APIException(f"Failed to delete artifacts: {e}")

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
            'stages_snapshot', 'agents', 'artifact_paths'
        ]
        
        datetime_fields = {
            'created_at',
            'updated_at',
            'last_deployed_at',
            'completed_at',
            'started_at',
        }

        for key, value in item.items():
            if isinstance(value, str) and key in datetime_fields:
                deserialized[key] = self._parse_datetime(value)
                continue
            if isinstance(value, str) and key in json_fields:
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
