"""
SQS Client for API v2

提供 SQS 队列操作的封装，包括：
- 消息发送
- 消息接收
- 消息删除
- 队列创建
"""
import boto3
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from botocore.config import Config

from api.v2.config import settings

logger = logging.getLogger(__name__)


class SQSClient:
    """SQS 客户端单例"""
    
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
            connect_timeout=10,
            read_timeout=30
        )
        
        session_kwargs = {'region_name': settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        session = boto3.Session(**session_kwargs)
        
        self.client = session.client(
            'sqs',
            endpoint_url=settings.SQS_ENDPOINT_URL,
            config=config
        )
        
        # 队列 URL 缓存
        self._queue_urls: Dict[str, str] = {}
        self._initialized = True
        logger.info("SQS client initialized")
    
    def _get_queue_url(self, queue_name: str) -> str:
        """获取队列 URL（带缓存）"""
        if queue_name not in self._queue_urls:
            try:
                response = self.client.get_queue_url(QueueName=queue_name)
                self._queue_urls[queue_name] = response['QueueUrl']
            except self.client.exceptions.QueueDoesNotExist:
                logger.error(f"Queue {queue_name} does not exist")
                raise
        return self._queue_urls[queue_name]
    
    def send_message(
        self,
        queue_name: str,
        message_body: Dict[str, Any],
        delay_seconds: int = 0,
        message_attributes: Optional[Dict[str, Any]] = None,
        message_group_id: Optional[str] = None,
        message_deduplication_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送消息到队列
        
        Args:
            queue_name: 队列名称
            message_body: 消息体（字典，会被序列化为 JSON）
            delay_seconds: 延迟发送秒数
            message_attributes: 消息属性
            message_group_id: FIFO 队列的消息组 ID
            message_deduplication_id: FIFO 队列的去重 ID
        
        Returns:
            发送结果，包含 MessageId
        """
        queue_url = self._get_queue_url(queue_name)
        
        send_kwargs = {
            'QueueUrl': queue_url,
            'MessageBody': json.dumps(message_body, ensure_ascii=False, default=str),
            'DelaySeconds': delay_seconds
        }
        
        if message_attributes:
            send_kwargs['MessageAttributes'] = self._format_message_attributes(message_attributes)
        
        if message_group_id:
            send_kwargs['MessageGroupId'] = message_group_id
        
        if message_deduplication_id:
            send_kwargs['MessageDeduplicationId'] = message_deduplication_id
        
        response = self.client.send_message(**send_kwargs)
        
        logger.info(f"Sent message to {queue_name}: {response['MessageId']}")
        
        return {
            'message_id': response['MessageId'],
            'sequence_number': response.get('SequenceNumber')
        }
    
    def send_build_task(
        self,
        task_id: str,
        project_id: str,
        requirement: str,
        user_id: Optional[str] = None,
        priority: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送构建任务到构建队列
        
        Args:
            task_id: 任务 ID
            project_id: 项目 ID
            requirement: 需求描述
            user_id: 用户 ID
            priority: 优先级
            metadata: 额外元数据
        
        Returns:
            发送结果
        """
        message_body = {
            'task_id': task_id,
            'project_id': project_id,
            'requirement': requirement,
            'user_id': user_id,
            'priority': priority,
            'metadata': metadata or {}
        }
        
        return self.send_message(
            queue_name=settings.SQS_BUILD_QUEUE_NAME,
            message_body=message_body,
            message_attributes={
                'task_type': 'build_agent',
                'priority': str(priority)
            }
        )
    
    def send_deploy_task(
        self,
        task_id: str,
        project_id: str,
        agent_id: str,
        deployment_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送部署任务到部署队列
        
        Args:
            task_id: 任务 ID
            project_id: 项目 ID
            agent_id: Agent ID
            deployment_config: 部署配置
        
        Returns:
            发送结果
        """
        message_body = {
            'task_id': task_id,
            'project_id': project_id,
            'agent_id': agent_id,
            'deployment_config': deployment_config or {}
        }
        
        return self.send_message(
            queue_name=settings.SQS_DEPLOY_QUEUE_NAME,
            message_body=message_body,
            message_attributes={
                'task_type': 'deploy_agent'
            }
        )
    
    def receive_messages(
        self,
        queue_name: str,
        max_messages: int = 1,
        wait_time_seconds: int = 20,
        visibility_timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        从队列接收消息
        
        Args:
            queue_name: 队列名称
            max_messages: 最大消息数 (1-10)
            wait_time_seconds: 长轮询等待时间
            visibility_timeout: 可见性超时
        
        Returns:
            消息列表
        """
        queue_url = self._get_queue_url(queue_name)
        
        receive_kwargs = {
            'QueueUrl': queue_url,
            'MaxNumberOfMessages': min(max_messages, 10),
            'WaitTimeSeconds': wait_time_seconds,
            'MessageAttributeNames': ['All'],
            'AttributeNames': ['All']
        }
        
        if visibility_timeout:
            receive_kwargs['VisibilityTimeout'] = visibility_timeout
        
        response = self.client.receive_message(**receive_kwargs)
        
        messages = []
        for msg in response.get('Messages', []):
            try:
                body = json.loads(msg['Body'])
            except json.JSONDecodeError:
                body = msg['Body']
            
            messages.append({
                'message_id': msg['MessageId'],
                'receipt_handle': msg['ReceiptHandle'],
                'body': body,
                'attributes': msg.get('Attributes', {}),
                'message_attributes': self._parse_message_attributes(
                    msg.get('MessageAttributes', {})
                )
            })
        
        return messages
    
    def delete_message(self, queue_name: str, receipt_handle: str) -> bool:
        """
        删除消息（确认处理完成）
        
        Args:
            queue_name: 队列名称
            receipt_handle: 消息接收句柄
        
        Returns:
            是否成功
        """
        queue_url = self._get_queue_url(queue_name)
        
        try:
            self.client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def change_message_visibility(
        self,
        queue_name: str,
        receipt_handle: str,
        visibility_timeout: int
    ) -> bool:
        """
        修改消息可见性超时
        
        Args:
            queue_name: 队列名称
            receipt_handle: 消息接收句柄
            visibility_timeout: 新的可见性超时（秒）
        
        Returns:
            是否成功
        """
        queue_url = self._get_queue_url(queue_name)
        
        try:
            self.client.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout
            )
            return True
        except Exception as e:
            logger.error(f"Failed to change message visibility: {e}")
            return False
    
    def get_queue_attributes(self, queue_name: str) -> Dict[str, Any]:
        """
        获取队列属性
        
        Args:
            queue_name: 队列名称
        
        Returns:
            队列属性
        """
        queue_url = self._get_queue_url(queue_name)
        
        response = self.client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['All']
        )
        
        attrs = response.get('Attributes', {})
        return {
            'approximate_messages': int(attrs.get('ApproximateNumberOfMessages', 0)),
            'approximate_messages_not_visible': int(attrs.get('ApproximateNumberOfMessagesNotVisible', 0)),
            'approximate_messages_delayed': int(attrs.get('ApproximateNumberOfMessagesDelayed', 0)),
            'visibility_timeout': int(attrs.get('VisibilityTimeout', 30)),
            'message_retention_period': int(attrs.get('MessageRetentionPeriod', 345600)),
            'created_timestamp': attrs.get('CreatedTimestamp'),
            'last_modified_timestamp': attrs.get('LastModifiedTimestamp')
        }
    
    def _format_message_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """格式化消息属性"""
        formatted = {}
        for key, value in attributes.items():
            if isinstance(value, str):
                formatted[key] = {'DataType': 'String', 'StringValue': value}
            elif isinstance(value, (int, float)):
                formatted[key] = {'DataType': 'Number', 'StringValue': str(value)}
            elif isinstance(value, bytes):
                formatted[key] = {'DataType': 'Binary', 'BinaryValue': value}
        return formatted
    
    def _parse_message_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """解析消息属性"""
        parsed = {}
        for key, value in attributes.items():
            data_type = value.get('DataType', 'String')
            if data_type == 'String':
                parsed[key] = value.get('StringValue')
            elif data_type == 'Number':
                str_value = value.get('StringValue', '0')
                parsed[key] = float(str_value) if '.' in str_value else int(str_value)
            elif data_type == 'Binary':
                parsed[key] = value.get('BinaryValue')
        return parsed
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.list_queues(MaxResults=1)
            return True
        except Exception as e:
            logger.error(f"SQS health check failed: {e}")
            return False


# 全局单例
sqs_client = SQSClient()
