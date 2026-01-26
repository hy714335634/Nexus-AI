"""
DynamoDB Client for API v2

提供 DynamoDB 表操作的封装，包括：
- 连接池管理
- 重试机制
- CRUD 操作
- 表创建
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
import logging
import threading
import time
from functools import wraps
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from api.v2.config import (
    settings,
    TABLE_PROJECTS,
    TABLE_STAGES,
    TABLE_AGENTS,
    TABLE_INVOCATIONS,
    TABLE_SESSIONS,
    TABLE_MESSAGES,
    TABLE_TASKS,
    TABLE_TOOLS,
)

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """DynamoDB 操作重试装饰器"""
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
                    if isinstance(e, ClientError):
                        error_code = e.response.get('Error', {}).get('Code', '')
                        if error_code in ['ProvisionedThroughputExceededException',
                                          'ThrottlingException',
                                          'ServiceUnavailable',
                                          'InternalServerError']:
                            wait_time = delay * (backoff ** attempt)
                            logger.warning(f"Retryable error {error_code}, retrying in {wait_time}s")
                            time.sleep(wait_time)
                            continue
                    raise e
            raise last_exception
        return wrapper
    return decorator


class DynamoDBClient:
    """DynamoDB 客户端单例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        config = Config(
            region_name=settings.AWS_REGION,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=50,
            connect_timeout=10,
            read_timeout=30
        )
        
        session_kwargs = {'region_name': settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        session = boto3.Session(**session_kwargs)
        
        self.dynamodb = session.resource(
            'dynamodb',
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL,
            config=config
        )
        self.client = session.client(
            'dynamodb',
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL,
            config=config
        )
        
        # 表引用缓存
        self._tables: Dict[str, Any] = {}
        self._initialized = True
        logger.info("DynamoDB client initialized")
    
    def _get_table(self, table_name: str):
        """获取表引用（懒加载）"""
        if table_name not in self._tables:
            self._tables[table_name] = self.dynamodb.Table(table_name)
        return self._tables[table_name]
    
    @property
    def projects_table(self):
        return self._get_table(TABLE_PROJECTS)
    
    @property
    def stages_table(self):
        return self._get_table(TABLE_STAGES)
    
    @property
    def agents_table(self):
        return self._get_table(TABLE_AGENTS)
    
    @property
    def invocations_table(self):
        return self._get_table(TABLE_INVOCATIONS)
    
    @property
    def sessions_table(self):
        return self._get_table(TABLE_SESSIONS)
    
    @property
    def messages_table(self):
        return self._get_table(TABLE_MESSAGES)
    
    @property
    def tasks_table(self):
        return self._get_table(TABLE_TASKS)
    
    @property
    def tools_table(self):
        return self._get_table(TABLE_TOOLS)

    # ============== Projects ==============
    
    @retry_on_error()
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建项目"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        project_data['created_at'] = now
        project_data['updated_at'] = now
        self.projects_table.put_item(Item=self._to_dynamo(project_data))
        return project_data
    
    @retry_on_error()
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目"""
        response = self.projects_table.get_item(Key={'project_id': project_id})
        item = response.get('Item')
        return self._from_dynamo(item) if item else None
    
    @retry_on_error()
    def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新项目"""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": self._to_dynamo_value(v) for k, v in updates.items()}
        
        response = self.projects_table.update_item(
            Key={'project_id': project_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        return self._from_dynamo(response.get('Attributes', {}))
    
    @retry_on_error()
    def list_projects(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 20,
        last_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """列表项目"""
        scan_kwargs = {'Limit': limit}
        
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = {'project_id': last_key}
        
        filter_conditions = []
        expr_values = {}
        expr_names = {}
        
        if status:
            filter_conditions.append("#status = :status")
            expr_names["#status"] = "status"
            expr_values[":status"] = status
        
        if user_id:
            filter_conditions.append("user_id = :user_id")
            expr_values[":user_id"] = user_id
        
        if filter_conditions:
            scan_kwargs['FilterExpression'] = " AND ".join(filter_conditions)
            scan_kwargs['ExpressionAttributeValues'] = expr_values
            if expr_names:
                scan_kwargs['ExpressionAttributeNames'] = expr_names
        
        response = self.projects_table.scan(**scan_kwargs)
        
        items = [self._from_dynamo(item) for item in response.get('Items', [])]
        last_evaluated_key = response.get('LastEvaluatedKey', {}).get('project_id')
        
        return {
            'items': items,
            'last_key': last_evaluated_key,
            'count': len(items)
        }
    
    @retry_on_error()
    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        self.projects_table.delete_item(Key={'project_id': project_id})
        return True

    # ============== Stages ==============
    
    @retry_on_error()
    def create_stage(self, stage_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建阶段"""
        self.stages_table.put_item(Item=self._to_dynamo(stage_data))
        return stage_data
    
    @retry_on_error()
    def get_stage(self, project_id: str, stage_name: str) -> Optional[Dict[str, Any]]:
        """获取阶段"""
        response = self.stages_table.get_item(
            Key={'project_id': project_id, 'stage_name': stage_name}
        )
        item = response.get('Item')
        return self._from_dynamo(item) if item else None
    
    @retry_on_error()
    def update_stage(self, project_id: str, stage_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新阶段"""
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": self._to_dynamo_value(v) for k, v in updates.items()}
        
        response = self.stages_table.update_item(
            Key={'project_id': project_id, 'stage_name': stage_name},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        return self._from_dynamo(response.get('Attributes', {}))
    
    @retry_on_error()
    def list_stages(self, project_id: str) -> List[Dict[str, Any]]:
        """列表项目的所有阶段"""
        response = self.stages_table.query(
            KeyConditionExpression=Key('project_id').eq(project_id)
        )
        items = [self._from_dynamo(item) for item in response.get('Items', [])]
        return sorted(items, key=lambda x: x.get('stage_number', 0))
    
    @retry_on_error()
    def delete_stage(self, project_id: str, stage_name: str) -> bool:
        """删除阶段"""
        self.stages_table.delete_item(
            Key={'project_id': project_id, 'stage_name': stage_name}
        )
        return True

    # ============== Agents ==============
    
    @retry_on_error()
    def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建Agent"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        agent_data['created_at'] = now
        agent_data['updated_at'] = now
        self.agents_table.put_item(Item=self._to_dynamo(agent_data))
        return agent_data
    
    @retry_on_error()
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent"""
        response = self.agents_table.get_item(Key={'agent_id': agent_id})
        item = response.get('Item')
        return self._from_dynamo(item) if item else None
    
    @retry_on_error()
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新Agent"""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": self._to_dynamo_value(v) for k, v in updates.items()}
        
        response = self.agents_table.update_item(
            Key={'agent_id': agent_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        return self._from_dynamo(response.get('Attributes', {}))
    
    @retry_on_error()
    def list_agents(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        last_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """列表Agent"""
        scan_kwargs = {'Limit': limit}
        
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = {'agent_id': last_key}
        
        filter_conditions = []
        expr_values = {}
        expr_names = {}
        
        if status:
            filter_conditions.append("#status = :status")
            expr_names["#status"] = "status"
            expr_values[":status"] = status
        
        if category:
            filter_conditions.append("category = :category")
            expr_values[":category"] = category
        
        if filter_conditions:
            scan_kwargs['FilterExpression'] = " AND ".join(filter_conditions)
            scan_kwargs['ExpressionAttributeValues'] = expr_values
            if expr_names:
                scan_kwargs['ExpressionAttributeNames'] = expr_names
        
        response = self.agents_table.scan(**scan_kwargs)
        
        items = [self._from_dynamo(item) for item in response.get('Items', [])]
        last_evaluated_key = response.get('LastEvaluatedKey', {}).get('agent_id')
        
        return {
            'items': items,
            'last_key': last_evaluated_key,
            'count': len(items)
        }
    
    @retry_on_error()
    def delete_agent(self, agent_id: str) -> bool:
        """删除Agent"""
        self.agents_table.delete_item(Key={'agent_id': agent_id})
        return True

    # ============== Tasks ==============
    
    @retry_on_error()
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        task_data['created_at'] = now
        task_data['updated_at'] = now
        self.tasks_table.put_item(Item=self._to_dynamo(task_data))
        return task_data
    
    @retry_on_error()
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        response = self.tasks_table.get_item(Key={'task_id': task_id})
        item = response.get('Item')
        return self._from_dynamo(item) if item else None
    
    @retry_on_error()
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务"""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": self._to_dynamo_value(v) for k, v in updates.items()}
        
        response = self.tasks_table.update_item(
            Key={'task_id': task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        return self._from_dynamo(response.get('Attributes', {}))

    # ============== Sessions ==============
    
    @retry_on_error()
    def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建会话"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        session_data['created_at'] = now
        session_data['last_active_at'] = now
        self.sessions_table.put_item(Item=self._to_dynamo(session_data))
        return session_data
    
    @retry_on_error()
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        response = self.sessions_table.get_item(Key={'session_id': session_id})
        item = response.get('Item')
        return self._from_dynamo(item) if item else None
    
    @retry_on_error()
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新会话"""
        updates['last_active_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
        expr_names = {f"#{k}": k for k in updates.keys()}
        expr_values = {f":{k}": self._to_dynamo_value(v) for k, v in updates.items()}
        
        response = self.sessions_table.update_item(
            Key={'session_id': session_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        return self._from_dynamo(response.get('Attributes', {}))
    
    @retry_on_error()
    def list_sessions(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """列表Agent的会话"""
        response = self.sessions_table.query(
            IndexName='AgentIndex',
            KeyConditionExpression=Key('agent_id').eq(agent_id),
            Limit=limit,
            ScanIndexForward=False  # 按时间倒序
        )
        return [self._from_dynamo(item) for item in response.get('Items', [])]
    
    @retry_on_error()
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        self.sessions_table.delete_item(Key={'session_id': session_id})
        return True
    
    @retry_on_error()
    def delete_session_messages(self, session_id: str) -> int:
        """删除会话的所有消息"""
        # 先查询所有消息
        response = self.messages_table.query(
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        items = response.get('Items', [])
        
        # 批量删除
        deleted_count = 0
        with self.messages_table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={
                    'session_id': item['session_id'],
                    'message_id': item['message_id']
                })
                deleted_count += 1
        
        return deleted_count

    # ============== Messages ==============
    
    @retry_on_error()
    def create_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建消息"""
        self.messages_table.put_item(Item=self._to_dynamo(message_data))
        return message_data
    
    @retry_on_error()
    def list_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """列表会话消息"""
        response = self.messages_table.query(
            KeyConditionExpression=Key('session_id').eq(session_id),
            Limit=limit,
            ScanIndexForward=True  # 按时间正序
        )
        return [self._from_dynamo(item) for item in response.get('Items', [])]

    # ============== Tools ==============
    
    @retry_on_error()
    def list_tools(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """列表工具"""
        scan_kwargs = {'Limit': limit}
        
        filter_conditions = []
        expr_values = {}
        expr_names = {}
        
        if category:
            filter_conditions.append("category = :category")
            expr_values[":category"] = category
        
        if source:
            filter_conditions.append("#source = :source")
            expr_names["#source"] = "source"
            expr_values[":source"] = source
        
        if filter_conditions:
            scan_kwargs['FilterExpression'] = " AND ".join(filter_conditions)
            scan_kwargs['ExpressionAttributeValues'] = expr_values
            if expr_names:
                scan_kwargs['ExpressionAttributeNames'] = expr_names
        
        response = self.tools_table.scan(**scan_kwargs)
        return [self._from_dynamo(item) for item in response.get('Items', [])]

    # ============== Utility Methods ==============
    
    def _to_dynamo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换为 DynamoDB 格式"""
        return {k: self._to_dynamo_value(v) for k, v in data.items() if v is not None}
    
    def _to_dynamo_value(self, value: Any) -> Any:
        """转换单个值为 DynamoDB 格式"""
        if isinstance(value, dict):
            return {k: self._to_dynamo_value(v) for k, v in value.items() if v is not None}
        if isinstance(value, list):
            return [self._to_dynamo_value(item) for item in value if item is not None]
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, int) and not isinstance(value, bool):
            return Decimal(str(value))
        return value
    
    def _from_dynamo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从 DynamoDB 格式转换"""
        return {k: self._from_dynamo_value(v) for k, v in data.items()}
    
    def _from_dynamo_value(self, value: Any) -> Any:
        """转换单个值从 DynamoDB 格式"""
        if isinstance(value, dict):
            return {k: self._from_dynamo_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._from_dynamo_value(item) for item in value]
        if isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            return float(value)
        return value
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.list_tables(Limit=1)
            return True
        except Exception as e:
            logger.error(f"DynamoDB health check failed: {e}")
            return False


# 全局单例
db_client = DynamoDBClient()
