#!/usr/bin/env python3
"""
初始化 DynamoDB 表、SQS 队列和 S3 存储桶

用法:
    python scripts/init_infrastructure.py [--tables-only] [--queues-only] [--s3-only]
"""
import argparse
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

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
    ALL_QUEUES,
)

from nexus_utils.config_loader import get_config


def get_dynamodb_client():
    """获取 DynamoDB 客户端"""
    kwargs = {'region_name': settings.AWS_REGION}
    if settings.DYNAMODB_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.DYNAMODB_ENDPOINT_URL
    return boto3.client('dynamodb', **kwargs)


def get_sqs_client():
    """获取 SQS 客户端"""
    kwargs = {'region_name': settings.AWS_REGION}
    if settings.SQS_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.SQS_ENDPOINT_URL
    return boto3.client('sqs', **kwargs)


def get_s3_client():
    """获取 S3 客户端"""
    return boto3.client('s3', region_name=settings.AWS_REGION)


# 获取配置
_config = get_config()
ARTIFACTS_S3_BUCKET = _config.get_nested('nexus_ai', 'artifacts_s3_bucket', default='nexus-ai-artifacts')
TABLE_ARTIFACTS = f"{settings.DYNAMODB_TABLE_PREFIX}artifacts"


# 表定义
TABLE_DEFINITIONS = [
    {
        'TableName': TABLE_PROJECTS,
        'KeySchema': [{'AttributeName': 'project_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'project_id', 'AttributeType': 'S'}],
    },
    {
        'TableName': TABLE_STAGES,
        'KeySchema': [
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'stage_name', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'stage_name', 'AttributeType': 'S'}
        ],
    },
    {
        'TableName': TABLE_AGENTS,
        'KeySchema': [{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'agent_id', 'AttributeType': 'S'}],
    },
    {
        'TableName': TABLE_INVOCATIONS,
        'KeySchema': [{'AttributeName': 'invocation_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'invocation_id', 'AttributeType': 'S'},
            {'AttributeName': 'agent_id', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgentIndex',
                'KeySchema': [{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': TABLE_SESSIONS,
        'KeySchema': [{'AttributeName': 'session_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'agent_id', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgentIndex',
                'KeySchema': [{'AttributeName': 'agent_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': TABLE_MESSAGES,
        'KeySchema': [
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'message_id', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'message_id', 'AttributeType': 'S'}
        ],
    },
    {
        'TableName': TABLE_TASKS,
        'KeySchema': [{'AttributeName': 'task_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'task_id', 'AttributeType': 'S'}],
    },
    {
        'TableName': TABLE_TOOLS,
        'KeySchema': [{'AttributeName': 'tool_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'tool_id', 'AttributeType': 'S'}],
    },
    # Artifacts表 - 存储Agent版本和S3同步信息
    {
        'TableName': TABLE_ARTIFACTS,
        'KeySchema': [
            {'AttributeName': 'agent_name', 'KeyType': 'HASH'},
            {'AttributeName': 'version_uuid', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'agent_name', 'AttributeType': 'S'},
            {'AttributeName': 'version_uuid', 'AttributeType': 'S'},
            {'AttributeName': 'workspace_uuid', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'WorkspaceIndex',
                'KeySchema': [
                    {'AttributeName': 'workspace_uuid', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
]


def create_table(client, table_def: dict) -> bool:
    """创建单个 DynamoDB 表"""
    table_name = table_def['TableName']
    
    try:
        # 检查表是否存在
        client.describe_table(TableName=table_name)
        print(f"  ⚠ 表已存在: {table_name}")
        return False
        
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            raise
    
    # 创建表
    create_params = {
        'TableName': table_name,
        'KeySchema': table_def['KeySchema'],
        'AttributeDefinitions': table_def['AttributeDefinitions'],
        'BillingMode': 'PAY_PER_REQUEST',
    }
    
    if 'GlobalSecondaryIndexes' in table_def:
        gsis = []
        for gsi in table_def['GlobalSecondaryIndexes']:
            gsis.append({
                'IndexName': gsi['IndexName'],
                'KeySchema': gsi['KeySchema'],
                'Projection': gsi['Projection'],
            })
        create_params['GlobalSecondaryIndexes'] = gsis
    
    client.create_table(**create_params)
    print(f"  ✓ 创建表: {table_name}")
    return True


def create_queue(client, queue_name: str, is_dlq: bool = False) -> bool:
    """创建单个 SQS 队列"""
    try:
        # 检查队列是否存在
        client.get_queue_url(QueueName=queue_name)
        print(f"  ⚠ 队列已存在: {queue_name}")
        return False
        
    except ClientError as e:
        if e.response['Error']['Code'] != 'AWS.SimpleQueueService.NonExistentQueue':
            raise
    
    # 创建队列
    attributes = {
        'MessageRetentionPeriod': str(settings.MESSAGE_RETENTION_DAYS * 24 * 3600),
    }
    
    if not is_dlq:
        if 'build' in queue_name:
            attributes['VisibilityTimeout'] = str(settings.BUILD_VISIBILITY_TIMEOUT)
        else:
            attributes['VisibilityTimeout'] = str(settings.DEPLOY_VISIBILITY_TIMEOUT)
    
    client.create_queue(QueueName=queue_name, Attributes=attributes)
    print(f"  ✓ 创建队列: {queue_name}")
    return True


def create_s3_bucket(client, bucket_name: str, region: str) -> bool:
    """创建 S3 存储桶"""
    try:
        # 检查桶是否存在
        client.head_bucket(Bucket=bucket_name)
        print(f"  ⚠ S3桶已存在: {bucket_name}")
        return False
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            # 桶不存在，创建
            try:
                if region == 'us-east-1':
                    client.create_bucket(Bucket=bucket_name)
                else:
                    client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                print(f"  ✓ 创建S3桶: {bucket_name}")
                
                # 启用版本控制
                client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                print(f"  ✓ 启用版本控制: {bucket_name}")
                
                return True
            except ClientError as create_error:
                print(f"  ✗ 创建S3桶失败: {create_error}")
                return False
        elif error_code == '403':
            print(f"  ⚠ S3桶存在但无访问权限: {bucket_name}")
            return False
        else:
            print(f"  ✗ 检查S3桶失败: {e}")
            return False


def init_tables():
    """初始化所有 DynamoDB 表"""
    print("\n📦 初始化 DynamoDB 表...")
    print(f"   Region: {settings.AWS_REGION}")
    if settings.DYNAMODB_ENDPOINT_URL:
        print(f"   Endpoint: {settings.DYNAMODB_ENDPOINT_URL}")
    
    client = get_dynamodb_client()
    created_count = 0
    
    for table_def in TABLE_DEFINITIONS:
        if create_table(client, table_def):
            created_count += 1
    
    print(f"\n   新建 {created_count} 个表")
    return created_count


def init_queues():
    """初始化所有 SQS 队列"""
    print("\n📬 初始化 SQS 队列...")
    print(f"   Region: {settings.AWS_REGION}")
    if settings.SQS_ENDPOINT_URL:
        print(f"   Endpoint: {settings.SQS_ENDPOINT_URL}")
    
    client = get_sqs_client()
    created_count = 0
    
    for queue_name in ALL_QUEUES:
        is_dlq = 'dlq' in queue_name.lower()
        if create_queue(client, queue_name, is_dlq):
            created_count += 1
    
    print(f"\n   新建 {created_count} 个队列")
    return created_count


def init_s3():
    """初始化 S3 存储桶"""
    print("\n🪣 初始化 S3 存储桶...")
    print(f"   Region: {settings.AWS_REGION}")
    print(f"   Bucket: {ARTIFACTS_S3_BUCKET}")
    
    client = get_s3_client()
    created_count = 0
    
    if create_s3_bucket(client, ARTIFACTS_S3_BUCKET, settings.AWS_REGION):
        created_count += 1
    
    print(f"\n   新建 {created_count} 个S3桶")
    return created_count


def main():
    parser = argparse.ArgumentParser(description='初始化 DynamoDB 表、SQS 队列和 S3 存储桶')
    parser.add_argument('--tables-only', action='store_true', help='仅初始化 DynamoDB 表')
    parser.add_argument('--queues-only', action='store_true', help='仅初始化 SQS 队列')
    parser.add_argument('--s3-only', action='store_true', help='仅初始化 S3 存储桶')
    args = parser.parse_args()
    
    print("=" * 50)
    print("Nexus-AI 基础设施初始化")
    print("=" * 50)
    
    try:
        if args.queues_only:
            init_queues()
        elif args.tables_only:
            init_tables()
        elif args.s3_only:
            init_s3()
        else:
            init_tables()
            init_queues()
            init_s3()
        
        print("\n" + "=" * 50)
        print("✅ 初始化完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
