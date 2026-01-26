"""
Infrastructure Manager - handles DynamoDB tables and SQS queues initialization and cleanup

Provides functionality for:
- Creating DynamoDB tables
- Creating SQS queues
- Clearing table data
- Purging queue messages
- Deleting agent-specific data
- Validating workflow configuration
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TableDefinition:
    """DynamoDB table definition"""
    table_name: str
    key_schema: List[Dict[str, str]]
    attribute_definitions: List[Dict[str, str]]
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = None


@dataclass
class InfrastructureResult:
    """Result of infrastructure operation"""
    success: bool
    created_count: int = 0
    deleted_count: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class WorkflowConfigValidationResult:
    """工作流配置验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stages_count: int = 0
    config_path: str = ''


class InfrastructureManager:
    """Manages AWS infrastructure for Nexus-AI"""
    
    def __init__(self, region: str = None, dynamodb_endpoint: str = None, sqs_endpoint: str = None):
        """
        Initialize infrastructure manager.
        
        Args:
            region: AWS region
            dynamodb_endpoint: Custom DynamoDB endpoint (for local development)
            sqs_endpoint: Custom SQS endpoint (for local development)
        """
        self.region = region or 'us-west-2'
        self.dynamodb_endpoint = dynamodb_endpoint
        self.sqs_endpoint = sqs_endpoint
        self._dynamodb_client = None
        self._dynamodb_resource = None
        self._sqs_client = None
    
    @classmethod
    def from_settings(cls) -> 'InfrastructureManager':
        """Create manager from API settings"""
        try:
            from api.v2.config import settings
            return cls(
                region=settings.AWS_REGION,
                dynamodb_endpoint=settings.DYNAMODB_ENDPOINT_URL,
                sqs_endpoint=settings.SQS_ENDPOINT_URL
            )
        except ImportError:
            return cls()
    
    def _get_dynamodb_client(self):
        """Get or create DynamoDB client"""
        if self._dynamodb_client is None:
            import boto3
            kwargs = {'region_name': self.region}
            if self.dynamodb_endpoint:
                kwargs['endpoint_url'] = self.dynamodb_endpoint
            self._dynamodb_client = boto3.client('dynamodb', **kwargs)
        return self._dynamodb_client
    
    def _get_dynamodb_resource(self):
        """Get or create DynamoDB resource"""
        if self._dynamodb_resource is None:
            import boto3
            kwargs = {'region_name': self.region}
            if self.dynamodb_endpoint:
                kwargs['endpoint_url'] = self.dynamodb_endpoint
            self._dynamodb_resource = boto3.resource('dynamodb', **kwargs)
        return self._dynamodb_resource
    
    def _get_sqs_client(self):
        """Get or create SQS client"""
        if self._sqs_client is None:
            import boto3
            kwargs = {'region_name': self.region}
            if self.sqs_endpoint:
                kwargs['endpoint_url'] = self.sqs_endpoint
            self._sqs_client = boto3.client('sqs', **kwargs)
        return self._sqs_client
    
    def get_table_definitions(self) -> List[TableDefinition]:
        """Get all table definitions"""
        try:
            from api.v2.config import (
                TABLE_PROJECTS, TABLE_STAGES, TABLE_AGENTS,
                TABLE_INVOCATIONS, TABLE_SESSIONS, TABLE_MESSAGES,
                TABLE_TASKS, TABLE_TOOLS
            )
        except ImportError:
            # Fallback to default names
            prefix = 'nexus_'
            TABLE_PROJECTS = f'{prefix}projects'
            TABLE_STAGES = f'{prefix}stages'
            TABLE_AGENTS = f'{prefix}agents'
            TABLE_INVOCATIONS = f'{prefix}invocations'
            TABLE_SESSIONS = f'{prefix}sessions'
            TABLE_MESSAGES = f'{prefix}messages'
            TABLE_TASKS = f'{prefix}tasks'
            TABLE_TOOLS = f'{prefix}tools'
        
        return [
            TableDefinition(
                table_name=TABLE_PROJECTS,
                key_schema=[{'AttributeName': 'project_id', 'KeyType': 'HASH'}],
                attribute_definitions=[{'AttributeName': 'project_id', 'AttributeType': 'S'}],
            ),
            TableDefinition(
                table_name=TABLE_STAGES,
                key_schema=[
                    {'AttributeName': 'project_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'stage_name', 'KeyType': 'RANGE'}
                ],
                attribute_definitions=[
                    {'AttributeName': 'project_id', 'AttributeType': 'S'},
                    {'AttributeName': 'stage_name', 'AttributeType': 'S'}
                ],
            ),
            TableDefinition(
                table_name=TABLE_AGENTS,
                key_schema=[{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
                attribute_definitions=[{'AttributeName': 'agent_id', 'AttributeType': 'S'}],
            ),
            TableDefinition(
                table_name=TABLE_INVOCATIONS,
                key_schema=[{'AttributeName': 'invocation_id', 'KeyType': 'HASH'}],
                attribute_definitions=[
                    {'AttributeName': 'invocation_id', 'AttributeType': 'S'},
                    {'AttributeName': 'agent_id', 'AttributeType': 'S'}
                ],
                global_secondary_indexes=[{
                    'IndexName': 'AgentIndex',
                    'KeySchema': [{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }],
            ),
            TableDefinition(
                table_name=TABLE_SESSIONS,
                key_schema=[{'AttributeName': 'session_id', 'KeyType': 'HASH'}],
                attribute_definitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    {'AttributeName': 'agent_id', 'AttributeType': 'S'}
                ],
                global_secondary_indexes=[{
                    'IndexName': 'AgentIndex',
                    'KeySchema': [{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }],
            ),
            TableDefinition(
                table_name=TABLE_MESSAGES,
                key_schema=[
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'message_id', 'KeyType': 'RANGE'}
                ],
                attribute_definitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'},
                    {'AttributeName': 'message_id', 'AttributeType': 'S'}
                ],
            ),
            TableDefinition(
                table_name=TABLE_TASKS,
                key_schema=[{'AttributeName': 'task_id', 'KeyType': 'HASH'}],
                attribute_definitions=[{'AttributeName': 'task_id', 'AttributeType': 'S'}],
            ),
            TableDefinition(
                table_name=TABLE_TOOLS,
                key_schema=[{'AttributeName': 'tool_id', 'KeyType': 'HASH'}],
                attribute_definitions=[{'AttributeName': 'tool_id', 'AttributeType': 'S'}],
            ),
        ]
    
    def get_queue_names(self) -> List[str]:
        """Get all queue names"""
        try:
            from api.v2.config import ALL_QUEUES
            return ALL_QUEUES
        except ImportError:
            return [
                'nexus-build-queue',
                'nexus-deploy-queue',
                'nexus-notification-queue',
                'nexus-build-dlq',
                'nexus-deploy-dlq',
            ]
    
    def get_queue_config(self) -> Dict[str, Any]:
        """Get queue configuration"""
        try:
            from api.v2.config import settings
            return {
                'message_retention_days': settings.MESSAGE_RETENTION_DAYS,
                'build_visibility_timeout': settings.BUILD_VISIBILITY_TIMEOUT,
                'deploy_visibility_timeout': settings.DEPLOY_VISIBILITY_TIMEOUT,
            }
        except ImportError:
            return {
                'message_retention_days': 7,
                'build_visibility_timeout': 3600,
                'deploy_visibility_timeout': 600,
            }
    
    def create_table(self, table_def: TableDefinition) -> Tuple[bool, str]:
        """
        Create a single DynamoDB table.
        
        Returns:
            Tuple of (created: bool, status: str)
            - (True, 'created') if table was created
            - (False, 'exists') if table already exists
            - (False, 'error: ...') if error occurred
        """
        from botocore.exceptions import ClientError
        
        client = self._get_dynamodb_client()
        
        try:
            client.describe_table(TableName=table_def.table_name)
            return (False, 'exists')
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                return (False, f'error: {e}')
        
        # Create table
        create_params = {
            'TableName': table_def.table_name,
            'KeySchema': table_def.key_schema,
            'AttributeDefinitions': table_def.attribute_definitions,
            'BillingMode': 'PAY_PER_REQUEST',
        }
        
        if table_def.global_secondary_indexes:
            create_params['GlobalSecondaryIndexes'] = table_def.global_secondary_indexes
        
        try:
            client.create_table(**create_params)
            return (True, 'created')
        except ClientError as e:
            return (False, f'error: {e}')
    
    def create_queue(self, queue_name: str) -> Tuple[bool, str]:
        """
        Create a single SQS queue.
        
        Returns:
            Tuple of (created: bool, status: str)
        """
        from botocore.exceptions import ClientError
        
        client = self._get_sqs_client()
        config = self.get_queue_config()
        
        try:
            client.get_queue_url(QueueName=queue_name)
            return (False, 'exists')
        except ClientError as e:
            if e.response['Error']['Code'] != 'AWS.SimpleQueueService.NonExistentQueue':
                return (False, f'error: {e}')
        
        # Create queue
        is_dlq = 'dlq' in queue_name.lower()
        attributes = {
            'MessageRetentionPeriod': str(config['message_retention_days'] * 24 * 3600),
        }
        
        if not is_dlq:
            if 'build' in queue_name:
                attributes['VisibilityTimeout'] = str(config['build_visibility_timeout'])
            else:
                attributes['VisibilityTimeout'] = str(config['deploy_visibility_timeout'])
        
        try:
            client.create_queue(QueueName=queue_name, Attributes=attributes)
            return (True, 'created')
        except ClientError as e:
            return (False, f'error: {e}')
    
    def clear_table(self, table_name: str) -> Tuple[int, str]:
        """
        Clear all data from a DynamoDB table.
        
        Returns:
            Tuple of (deleted_count: int, status: str)
        """
        from botocore.exceptions import ClientError
        
        dynamodb = self._get_dynamodb_resource()
        
        try:
            table = dynamodb.Table(table_name)
            key_schema = table.key_schema
            key_names = [key['AttributeName'] for key in key_schema]
            
            scan_kwargs = {}
            deleted_count = 0
            
            while True:
                response = table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                if not items:
                    break
                
                with table.batch_writer() as batch:
                    for item in items:
                        key = {k: item[k] for k in key_names}
                        batch.delete_item(Key=key)
                        deleted_count += 1
                
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            return (deleted_count, 'cleared')
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return (0, 'not_found')
            return (0, f'error: {e}')
    
    def purge_queue(self, queue_name: str) -> Tuple[bool, str]:
        """
        Purge all messages from an SQS queue.
        
        Returns:
            Tuple of (success: bool, status: str)
        """
        from botocore.exceptions import ClientError
        
        client = self._get_sqs_client()
        
        try:
            response = client.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            client.purge_queue(QueueUrl=queue_url)
            return (True, 'purged')
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AWS.SimpleQueueService.NonExistentQueue':
                return (False, 'not_found')
            elif error_code == 'AWS.SimpleQueueService.PurgeQueueInProgress':
                return (False, 'purge_in_progress')
            return (False, f'error: {e}')
    
    def delete_agent_data(self, agent_name: str) -> Dict[str, Any]:
        """
        Delete all data related to a specific agent.
        
        Args:
            agent_name: Name of the agent to delete data for
        
        Returns:
            Dict with deletion results for each table
        """
        from botocore.exceptions import ClientError
        from boto3.dynamodb.conditions import Key, Attr
        
        try:
            from api.v2.config import (
                TABLE_AGENTS, TABLE_INVOCATIONS,
                TABLE_SESSIONS, TABLE_MESSAGES
            )
        except ImportError:
            prefix = 'nexus_'
            TABLE_AGENTS = f'{prefix}agents'
            TABLE_INVOCATIONS = f'{prefix}invocations'
            TABLE_SESSIONS = f'{prefix}sessions'
            TABLE_MESSAGES = f'{prefix}messages'
        
        dynamodb = self._get_dynamodb_resource()
        results = {
            'agent_ids': [],
            'agents_deleted': 0,
            'invocations_deleted': 0,
            'sessions_deleted': 0,
            'messages_deleted': 0,
            'session_ids': [],
            'errors': []
        }
        
        # Find agent IDs
        try:
            agents_table = dynamodb.Table(TABLE_AGENTS)
            scan_kwargs = {
                'FilterExpression': (
                    Attr('agent_name').eq(agent_name) |
                    Attr('agent_id').contains(agent_name) |
                    Attr('project_id').eq(agent_name)
                )
            }
            
            while True:
                response = agents_table.scan(**scan_kwargs)
                for item in response.get('Items', []):
                    results['agent_ids'].append(item['agent_id'])
                
                if 'LastEvaluatedKey' not in response:
                    break
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            if not results['agent_ids']:
                results['agent_ids'].append(f'local_{agent_name}')
                
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                results['errors'].append(f'agents: {e}')
        
        # Delete from agents table
        for agent_id in results['agent_ids']:
            try:
                agents_table.delete_item(Key={'agent_id': agent_id})
                results['agents_deleted'] += 1
            except ClientError:
                pass
        
        # Delete from invocations table
        try:
            invocations_table = dynamodb.Table(TABLE_INVOCATIONS)
            for agent_id in results['agent_ids']:
                try:
                    response = invocations_table.query(
                        IndexName='AgentIndex',
                        KeyConditionExpression=Key('agent_id').eq(agent_id)
                    )
                    for item in response.get('Items', []):
                        invocations_table.delete_item(
                            Key={'invocation_id': item['invocation_id']}
                        )
                        results['invocations_deleted'] += 1
                except ClientError:
                    pass
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                results['errors'].append(f'invocations: {e}')
        
        # Delete from sessions table
        try:
            sessions_table = dynamodb.Table(TABLE_SESSIONS)
            for agent_id in results['agent_ids']:
                try:
                    response = sessions_table.query(
                        IndexName='AgentIndex',
                        KeyConditionExpression=Key('agent_id').eq(agent_id)
                    )
                    for item in response.get('Items', []):
                        results['session_ids'].append(item['session_id'])
                        sessions_table.delete_item(
                            Key={'session_id': item['session_id']}
                        )
                        results['sessions_deleted'] += 1
                except ClientError:
                    pass
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                results['errors'].append(f'sessions: {e}')
        
        # Delete from messages table
        if results['session_ids']:
            try:
                messages_table = dynamodb.Table(TABLE_MESSAGES)
                for session_id in results['session_ids']:
                    try:
                        response = messages_table.query(
                            KeyConditionExpression=Key('session_id').eq(session_id)
                        )
                        for item in response.get('Items', []):
                            messages_table.delete_item(
                                Key={
                                    'session_id': item['session_id'],
                                    'message_id': item['message_id']
                                }
                            )
                            results['messages_deleted'] += 1
                    except ClientError:
                        pass
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    results['errors'].append(f'messages: {e}')
        
        return results

    def validate_workflow_config(self, base_path: str = '.') -> WorkflowConfigValidationResult:
        """
        验证工作流配置是否正确。
        
        检查项目：
        - 配置文件存在性
        - 工作流阶段定义完整性
        - 提示词路径有效性
        - DynamoDB 表配置
        - SQS 队列配置
        
        Args:
            base_path: 项目根目录路径
        
        Returns:
            WorkflowConfigValidationResult: 验证结果
        """
        import yaml
        
        result = WorkflowConfigValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            stages_count=0,
            config_path=''
        )
        
        base = Path(base_path)
        config_path = base / 'config' / 'default_config.yaml'
        result.config_path = str(config_path)
        
        # 检查配置文件存在性
        if not config_path.exists():
            result.valid = False
            result.errors.append(f"配置文件不存在: {config_path}")
            return result
        
        # 加载配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            result.valid = False
            result.errors.append(f"配置文件解析失败: {e}")
            return result
        
        default_config = config.get('default-config', {})
        
        # 验证工作流配置
        workflow_config = default_config.get('workflow', {})
        if not workflow_config:
            result.warnings.append("未找到工作流配置 (workflow)，将使用默认值")
        else:
            # 验证阶段定义
            stages = workflow_config.get('stages', [])
            if not stages:
                result.warnings.append("未定义工作流阶段 (workflow.stages)")
            else:
                result.stages_count = len(stages)
                
                # 验证每个阶段
                required_fields = ['name', 'display_name', 'order', 'prerequisites', 'prompt_path']
                for i, stage in enumerate(stages):
                    stage_name = stage.get('name', f'stage_{i}')
                    
                    # 检查必需字段
                    for field in required_fields:
                        if field not in stage:
                            result.warnings.append(f"阶段 '{stage_name}' 缺少字段: {field}")
                    
                    # 验证提示词路径
                    prompt_path = stage.get('prompt_path', '')
                    if prompt_path:
                        prompts_dir = base / 'prompts'
                        full_prompt_path = prompts_dir / prompt_path
                        
                        # 检查目录或 YAML 文件
                        yaml_path = full_prompt_path.with_suffix('.yaml')
                        if not full_prompt_path.exists() and not yaml_path.exists():
                            if not full_prompt_path.is_dir():
                                result.warnings.append(
                                    f"阶段 '{stage_name}' 的提示词路径不存在: {prompt_path}"
                                )
            
            # 验证执行配置
            execution = workflow_config.get('execution', {})
            if not execution:
                result.warnings.append("未找到执行配置 (workflow.execution)")
            else:
                # 检查超时配置合理性
                stage_timeout = execution.get('stage_timeout_seconds', 3600)
                total_timeout = execution.get('total_timeout_seconds', 21600)
                if stage_timeout > total_timeout:
                    result.warnings.append(
                        f"阶段超时 ({stage_timeout}s) 大于总超时 ({total_timeout}s)"
                    )
            
            # 验证上下文配置
            context = workflow_config.get('context', {})
            if not context:
                result.warnings.append("未找到上下文配置 (workflow.context)")
            
            # 验证存储配置
            storage = workflow_config.get('storage', {})
            if not storage:
                result.warnings.append("未找到存储配置 (workflow.storage)")
        
        # 验证 DynamoDB 配置
        dynamodb_config = default_config.get('dynamodb', {})
        if not dynamodb_config:
            result.warnings.append("未找到 DynamoDB 配置 (dynamodb)")
        else:
            tables = dynamodb_config.get('tables', {})
            required_tables = ['projects', 'stages', 'tasks', 'agents']
            for table in required_tables:
                if table not in tables:
                    result.warnings.append(f"DynamoDB 配置缺少表定义: {table}")
        
        # 验证 SQS 配置
        sqs_config = default_config.get('sqs', {})
        if not sqs_config:
            result.warnings.append("未找到 SQS 配置 (sqs)")
        else:
            queues = sqs_config.get('queues', {})
            required_queues = ['build', 'deploy']
            for queue in required_queues:
                if queue not in queues:
                    result.warnings.append(f"SQS 配置缺少队列定义: {queue}")
        
        # 如果有错误，标记为无效
        if result.errors:
            result.valid = False
        
        return result
    
    def get_workflow_stages_from_config(self, base_path: str = '.') -> List[Dict[str, Any]]:
        """
        从配置文件获取工作流阶段定义。
        
        Args:
            base_path: 项目根目录路径
        
        Returns:
            List[Dict]: 阶段定义列表
        """
        import yaml
        
        config_path = Path(base_path) / 'config' / 'default_config.yaml'
        
        if not config_path.exists():
            return []
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return config.get('default-config', {}).get('workflow', {}).get('stages', [])
        except Exception:
            return []
    def list_tasks(self, status: Optional[str] = None, task_type: Optional[str] = None, 
                   limit: int = 50) -> Dict[str, Any]:
        """
        List tasks from the tasks table.
        
        Args:
            status: Filter by status (pending, running, completed, failed, cancelled)
            task_type: Filter by type (build_agent, deploy_agent, invoke_agent)
            limit: Maximum number of tasks to return
        
        Returns:
            Dict with tasks list and metadata
        """
        from botocore.exceptions import ClientError
        from boto3.dynamodb.conditions import Attr
        
        try:
            from api.v2.config import TABLE_TASKS
        except ImportError:
            TABLE_TASKS = 'nexus_tasks'
        
        dynamodb = self._get_dynamodb_resource()
        results = {
            'tasks': [],
            'count': 0,
            'errors': []
        }
        
        try:
            table = dynamodb.Table(TABLE_TASKS)
            scan_kwargs = {'Limit': limit}
            
            # Build filter expression
            filter_conditions = []
            if status:
                filter_conditions.append(Attr('status').eq(status))
            if task_type:
                filter_conditions.append(Attr('task_type').eq(task_type))
            
            if filter_conditions:
                filter_expr = filter_conditions[0]
                for cond in filter_conditions[1:]:
                    filter_expr = filter_expr & cond
                scan_kwargs['FilterExpression'] = filter_expr
            
            response = table.scan(**scan_kwargs)
            tasks = response.get('Items', [])
            
            # Sort by created_at descending
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            results['tasks'] = tasks[:limit]
            results['count'] = len(results['tasks'])
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                results['errors'].append('table_not_found')
            else:
                results['errors'].append(str(e))
        
        return results
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get a single task by ID.
        
        Args:
            task_id: The task ID to retrieve
        
        Returns:
            Dict with task data or error
        """
        from botocore.exceptions import ClientError
        
        try:
            from api.v2.config import TABLE_TASKS
        except ImportError:
            TABLE_TASKS = 'nexus_tasks'
        
        dynamodb = self._get_dynamodb_resource()
        result = {
            'task': None,
            'found': False,
            'error': None
        }
        
        try:
            table = dynamodb.Table(TABLE_TASKS)
            response = table.get_item(Key={'task_id': task_id})
            
            if 'Item' in response:
                result['task'] = response['Item']
                result['found'] = True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                result['error'] = 'table_not_found'
            else:
                result['error'] = str(e)
        
        return result
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all SQS queues.
        
        Returns:
            Dict with queue statistics
        """
        from botocore.exceptions import ClientError
        
        client = self._get_sqs_client()
        results = {
            'queues': [],
            'errors': []
        }
        
        for queue_name in self.get_queue_names():
            queue_info = {
                'name': queue_name,
                'messages_available': 0,
                'messages_in_flight': 0,
                'messages_delayed': 0,
                'exists': False
            }
            
            try:
                response = client.get_queue_url(QueueName=queue_name)
                queue_url = response['QueueUrl']
                queue_info['exists'] = True
                
                # Get queue attributes
                attrs = client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        'ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible',
                        'ApproximateNumberOfMessagesDelayed'
                    ]
                )
                
                queue_info['messages_available'] = int(attrs['Attributes'].get('ApproximateNumberOfMessages', 0))
                queue_info['messages_in_flight'] = int(attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
                queue_info['messages_delayed'] = int(attrs['Attributes'].get('ApproximateNumberOfMessagesDelayed', 0))
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'AWS.SimpleQueueService.NonExistentQueue':
                    results['errors'].append(f'{queue_name}: {e}')
            
            results['queues'].append(queue_info)
        
        return results
