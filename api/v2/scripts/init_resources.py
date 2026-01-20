#!/usr/bin/env python3
"""
Nexus AI v2 资源初始化脚本

创建所有必需的 DynamoDB 表和 SQS 队列

使用方法:
    python -m api.v2.scripts.init_resources [--clean] [--tables-only] [--queues-only]

参数:
    --clean: 先删除现有资源再创建
    --tables-only: 只创建 DynamoDB 表
    --queues-only: 只创建 SQS 队列
    --endpoint-url: DynamoDB/SQS 端点 URL（用于本地开发）
"""
import argparse
import boto3
import sys
import time
import logging
from botocore.config import Config
from botocore.exceptions import ClientError

# 添加项目根目录到路径
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

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
    ALL_TABLES,
    ALL_QUEUES,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============== DynamoDB 表定义 ==============

DYNAMODB_TABLE_DEFINITIONS = {
    TABLE_PROJECTS: {
        'KeySchema': [
            {'AttributeName': 'project_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'UserIndex',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'StatusIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_STAGES: {
        'KeySchema': [
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'stage_name', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'stage_name', 'AttributeType': 'S'},
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_AGENTS: {
        'KeySchema': [
            {'AttributeName': 'agent_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'agent_id', 'AttributeType': 'S'},
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'category', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'ProjectIndex',
                'KeySchema': [
                    {'AttributeName': 'project_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'StatusIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'CategoryIndex',
                'KeySchema': [
                    {'AttributeName': 'category', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_INVOCATIONS: {
        'KeySchema': [
            {'AttributeName': 'invocation_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'invocation_id', 'AttributeType': 'S'},
            {'AttributeName': 'agent_id', 'AttributeType': 'S'},
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgentIndex',
                'KeySchema': [
                    {'AttributeName': 'agent_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'SessionIndex',
                'KeySchema': [
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_SESSIONS: {
        'KeySchema': [
            {'AttributeName': 'session_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'agent_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'last_active_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgentIndex',
                'KeySchema': [
                    {'AttributeName': 'agent_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'last_active_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'UserIndex',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'last_active_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_MESSAGES: {
        'KeySchema': [
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'message_id', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'message_id', 'AttributeType': 'S'},
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_TASKS: {
        'KeySchema': [
            {'AttributeName': 'task_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'task_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'StatusIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'ProjectIndex',
                'KeySchema': [
                    {'AttributeName': 'project_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    },
    
    TABLE_TOOLS: {
        'KeySchema': [
            {'AttributeName': 'tool_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'tool_id', 'AttributeType': 'S'},
            {'AttributeName': 'category', 'AttributeType': 'S'},
            {'AttributeName': 'source', 'AttributeType': 'S'},
            {'AttributeName': 'usage_count', 'AttributeType': 'N'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'CategoryIndex',
                'KeySchema': [
                    {'AttributeName': 'category', 'KeyType': 'HASH'},
                    {'AttributeName': 'usage_count', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'SourceIndex',
                'KeySchema': [
                    {'AttributeName': 'source', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST'
    }
}


# ============== SQS 队列定义 ==============

SQS_QUEUE_DEFINITIONS = {
    settings.SQS_BUILD_DLQ_NAME: {
        'Attributes': {
            'MessageRetentionPeriod': str(14 * 24 * 3600),  # 14 days
            'VisibilityTimeout': '300'
        }
    },
    settings.SQS_DEPLOY_DLQ_NAME: {
        'Attributes': {
            'MessageRetentionPeriod': str(14 * 24 * 3600),
            'VisibilityTimeout': '300'
        }
    },
    settings.SQS_BUILD_QUEUE_NAME: {
        'Attributes': {
            'MessageRetentionPeriod': str(settings.MESSAGE_RETENTION_DAYS * 24 * 3600),
            'VisibilityTimeout': str(settings.BUILD_VISIBILITY_TIMEOUT),
            # RedrivePolicy 将在创建后设置
        },
        'dlq': settings.SQS_BUILD_DLQ_NAME,
        'max_receive_count': settings.MAX_RETRY_COUNT
    },
    settings.SQS_DEPLOY_QUEUE_NAME: {
        'Attributes': {
            'MessageRetentionPeriod': str(3 * 24 * 3600),  # 3 days
            'VisibilityTimeout': str(settings.DEPLOY_VISIBILITY_TIMEOUT),
        },
        'dlq': settings.SQS_DEPLOY_DLQ_NAME,
        'max_receive_count': settings.MAX_RETRY_COUNT
    },
    settings.SQS_NOTIFICATION_QUEUE_NAME: {
        'Attributes': {
            'MessageRetentionPeriod': str(1 * 24 * 3600),  # 1 day
            'VisibilityTimeout': '30'
        }
    }
}


class ResourceInitializer:
    """资源初始化器"""
    
    def __init__(self, endpoint_url: str = None):
        self.endpoint_url = endpoint_url or settings.DYNAMODB_ENDPOINT_URL
        
        config = Config(
            region_name=settings.AWS_REGION,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        
        session_kwargs = {'region_name': settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
        
        session = boto3.Session(**session_kwargs)
        
        self.dynamodb = session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            config=config
        )
        
        self.sqs = session.client(
            'sqs',
            endpoint_url=settings.SQS_ENDPOINT_URL or self.endpoint_url,
            config=config
        )
    
    # ============== DynamoDB 操作 ==============
    
    def create_table(self, table_name: str, definition: dict) -> bool:
        """创建单个 DynamoDB 表"""
        try:
            # 检查表是否存在
            try:
                self.dynamodb.describe_table(TableName=table_name)
                logger.info(f"Table {table_name} already exists, skipping")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
            
            # 创建表
            create_params = {
                'TableName': table_name,
                'KeySchema': definition['KeySchema'],
                'AttributeDefinitions': definition['AttributeDefinitions'],
                'BillingMode': definition.get('BillingMode', 'PAY_PER_REQUEST')
            }
            
            if 'GlobalSecondaryIndexes' in definition:
                create_params['GlobalSecondaryIndexes'] = definition['GlobalSecondaryIndexes']
            
            self.dynamodb.create_table(**create_params)
            logger.info(f"Creating table {table_name}...")
            
            # 等待表创建完成
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
            
            logger.info(f"✅ Table {table_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create table {table_name}: {e}")
            return False
    
    def delete_table(self, table_name: str) -> bool:
        """删除单个 DynamoDB 表"""
        try:
            self.dynamodb.delete_table(TableName=table_name)
            logger.info(f"Deleting table {table_name}...")
            
            # 等待表删除完成
            waiter = self.dynamodb.get_waiter('table_not_exists')
            waiter.wait(TableName=table_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
            
            logger.info(f"✅ Table {table_name} deleted")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Table {table_name} does not exist, skipping")
                return True
            logger.error(f"❌ Failed to delete table {table_name}: {e}")
            return False
    
    def create_all_tables(self) -> bool:
        """创建所有 DynamoDB 表"""
        logger.info("=" * 50)
        logger.info("Creating DynamoDB tables...")
        logger.info("=" * 50)
        
        success = True
        for table_name, definition in DYNAMODB_TABLE_DEFINITIONS.items():
            if not self.create_table(table_name, definition):
                success = False
        
        return success
    
    def delete_all_tables(self) -> bool:
        """删除所有 DynamoDB 表"""
        logger.info("=" * 50)
        logger.info("Deleting DynamoDB tables...")
        logger.info("=" * 50)
        
        success = True
        for table_name in ALL_TABLES:
            if not self.delete_table(table_name):
                success = False
        
        return success
    
    # ============== SQS 操作 ==============
    
    def create_queue(self, queue_name: str, definition: dict) -> str:
        """创建单个 SQS 队列，返回队列 URL"""
        try:
            # 检查队列是否存在
            try:
                response = self.sqs.get_queue_url(QueueName=queue_name)
                logger.info(f"Queue {queue_name} already exists, skipping")
                return response['QueueUrl']
            except ClientError as e:
                if e.response['Error']['Code'] != 'AWS.SimpleQueueService.NonExistentQueue':
                    raise
            
            # 创建队列
            response = self.sqs.create_queue(
                QueueName=queue_name,
                Attributes=definition.get('Attributes', {})
            )
            
            queue_url = response['QueueUrl']
            logger.info(f"✅ Queue {queue_name} created: {queue_url}")
            return queue_url
            
        except Exception as e:
            logger.error(f"❌ Failed to create queue {queue_name}: {e}")
            return None
    
    def delete_queue(self, queue_name: str) -> bool:
        """删除单个 SQS 队列"""
        try:
            response = self.sqs.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            self.sqs.delete_queue(QueueUrl=queue_url)
            logger.info(f"✅ Queue {queue_name} deleted")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                logger.info(f"Queue {queue_name} does not exist, skipping")
                return True
            logger.error(f"❌ Failed to delete queue {queue_name}: {e}")
            return False
    
    def create_all_queues(self) -> bool:
        """创建所有 SQS 队列"""
        logger.info("=" * 50)
        logger.info("Creating SQS queues...")
        logger.info("=" * 50)
        
        queue_urls = {}
        success = True
        
        # 先创建死信队列
        for queue_name, definition in SQS_QUEUE_DEFINITIONS.items():
            if 'dlq' not in definition:  # 这是死信队列
                url = self.create_queue(queue_name, definition)
                if url:
                    queue_urls[queue_name] = url
                else:
                    success = False
        
        # 再创建主队列并配置死信队列
        for queue_name, definition in SQS_QUEUE_DEFINITIONS.items():
            if 'dlq' in definition:
                url = self.create_queue(queue_name, definition)
                if url:
                    queue_urls[queue_name] = url
                    # 配置死信队列
                    dlq_name = definition['dlq']
                    if dlq_name in queue_urls:
                        self._set_redrive_policy(
                            url,
                            queue_urls[dlq_name],
                            definition.get('max_receive_count', 3)
                        )
                else:
                    success = False
        
        return success
    
    def _set_redrive_policy(self, queue_url: str, dlq_url: str, max_receive_count: int):
        """设置队列的死信队列策略"""
        try:
            # 获取死信队列 ARN
            dlq_attrs = self.sqs.get_queue_attributes(
                QueueUrl=dlq_url,
                AttributeNames=['QueueArn']
            )
            dlq_arn = dlq_attrs['Attributes']['QueueArn']
            
            # 设置重试策略
            import json
            redrive_policy = json.dumps({
                'deadLetterTargetArn': dlq_arn,
                'maxReceiveCount': str(max_receive_count)
            })
            
            self.sqs.set_queue_attributes(
                QueueUrl=queue_url,
                Attributes={'RedrivePolicy': redrive_policy}
            )
            logger.info(f"  Configured DLQ for queue")
        except Exception as e:
            logger.warning(f"  Failed to set redrive policy: {e}")
    
    def delete_all_queues(self) -> bool:
        """删除所有 SQS 队列"""
        logger.info("=" * 50)
        logger.info("Deleting SQS queues...")
        logger.info("=" * 50)
        
        success = True
        for queue_name in ALL_QUEUES:
            if not self.delete_queue(queue_name):
                success = False
        
        return success
    
    # ============== 综合操作 ==============
    
    def init_all(self, clean: bool = False) -> bool:
        """初始化所有资源"""
        if clean:
            logger.info("Cleaning existing resources...")
            self.delete_all_tables()
            self.delete_all_queues()
            time.sleep(2)  # 等待资源完全删除
        
        tables_ok = self.create_all_tables()
        queues_ok = self.create_all_queues()
        
        logger.info("=" * 50)
        if tables_ok and queues_ok:
            logger.info("✅ All resources initialized successfully!")
        else:
            logger.error("❌ Some resources failed to initialize")
        logger.info("=" * 50)
        
        return tables_ok and queues_ok
    
    def list_resources(self):
        """列出所有资源状态"""
        logger.info("=" * 50)
        logger.info("Current Resources Status")
        logger.info("=" * 50)
        
        # 列出表
        logger.info("\nDynamoDB Tables:")
        try:
            response = self.dynamodb.list_tables()
            tables = response.get('TableNames', [])
            for table in ALL_TABLES:
                status = "✅ exists" if table in tables else "❌ missing"
                logger.info(f"  {table}: {status}")
        except Exception as e:
            logger.error(f"  Failed to list tables: {e}")
        
        # 列出队列
        logger.info("\nSQS Queues:")
        try:
            response = self.sqs.list_queues()
            queue_urls = response.get('QueueUrls', [])
            queue_names = [url.split('/')[-1] for url in queue_urls]
            for queue in ALL_QUEUES:
                status = "✅ exists" if queue in queue_names else "❌ missing"
                logger.info(f"  {queue}: {status}")
        except Exception as e:
            logger.error(f"  Failed to list queues: {e}")


def main():
    parser = argparse.ArgumentParser(description='Initialize Nexus AI v2 resources')
    parser.add_argument('--clean', action='store_true', help='Delete existing resources before creating')
    parser.add_argument('--tables-only', action='store_true', help='Only create DynamoDB tables')
    parser.add_argument('--queues-only', action='store_true', help='Only create SQS queues')
    parser.add_argument('--list', action='store_true', help='List current resources status')
    parser.add_argument('--delete', action='store_true', help='Delete all resources')
    parser.add_argument('--endpoint-url', type=str, help='Custom endpoint URL for local development')
    
    args = parser.parse_args()
    
    initializer = ResourceInitializer(endpoint_url=args.endpoint_url)
    
    if args.list:
        initializer.list_resources()
        return
    
    if args.delete:
        initializer.delete_all_tables()
        initializer.delete_all_queues()
        return
    
    if args.tables_only:
        if args.clean:
            initializer.delete_all_tables()
            time.sleep(2)
        initializer.create_all_tables()
    elif args.queues_only:
        if args.clean:
            initializer.delete_all_queues()
            time.sleep(2)
        initializer.create_all_queues()
    else:
        initializer.init_all(clean=args.clean)


if __name__ == '__main__':
    main()
