#!/usr/bin/env python3
"""
清空所有 DynamoDB 表和 SQS 队列数据

用法:
    python scripts/clear_all_data.py [--tables-only] [--queues-only] [--yes]
"""
import argparse
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

from api.v2.config import settings, ALL_TABLES, ALL_QUEUES


def get_dynamodb_resource():
    """获取 DynamoDB 资源"""
    kwargs = {'region_name': settings.AWS_REGION}
    if settings.DYNAMODB_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.DYNAMODB_ENDPOINT_URL
    return boto3.resource('dynamodb', **kwargs)


def get_sqs_client():
    """获取 SQS 客户端"""
    kwargs = {'region_name': settings.AWS_REGION}
    if settings.SQS_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.SQS_ENDPOINT_URL
    return boto3.client('sqs', **kwargs)


def clear_table(dynamodb, table_name: str) -> int:
    """清空单个 DynamoDB 表"""
    try:
        table = dynamodb.Table(table_name)
        
        # 获取表的键模式
        key_schema = table.key_schema
        key_names = [key['AttributeName'] for key in key_schema]
        
        print(f"  清空表: {table_name} (主键: {key_names})")
        
        # 扫描并删除所有项
        scan_kwargs = {}
        deleted_count = 0
        
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
            
            # 批量删除
            with table.batch_writer() as batch:
                for item in items:
                    key = {k: item[k] for k in key_names}
                    batch.delete_item(Key=key)
                    deleted_count += 1
            
            # 检查是否还有更多数据
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        print(f"    ✓ 已删除 {deleted_count} 条记录")
        return deleted_count
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"    ⚠ 表不存在，跳过")
            return 0
        raise


def clear_queue(sqs, queue_name: str) -> int:
    """清空单个 SQS 队列"""
    try:
        # 获取队列 URL
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        print(f"  清空队列: {queue_name}")
        
        # 清空队列
        sqs.purge_queue(QueueUrl=queue_url)
        print(f"    ✓ 队列已清空")
        return 1
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AWS.SimpleQueueService.NonExistentQueue':
            print(f"    ⚠ 队列不存在，跳过")
            return 0
        elif error_code == 'AWS.SimpleQueueService.PurgeQueueInProgress':
            print(f"    ⚠ 队列正在清空中，跳过")
            return 0
        raise


def clear_tables():
    """清空所有 DynamoDB 表"""
    print("\n📦 清空 DynamoDB 表...")
    print(f"   Region: {settings.AWS_REGION}")
    if settings.DYNAMODB_ENDPOINT_URL:
        print(f"   Endpoint: {settings.DYNAMODB_ENDPOINT_URL}")
    
    dynamodb = get_dynamodb_resource()
    total_deleted = 0
    
    for table_name in ALL_TABLES:
        total_deleted += clear_table(dynamodb, table_name)
    
    print(f"\n   总计删除 {total_deleted} 条记录")
    return total_deleted


def clear_queues():
    """清空所有 SQS 队列"""
    print("\n📬 清空 SQS 队列...")
    print(f"   Region: {settings.AWS_REGION}")
    if settings.SQS_ENDPOINT_URL:
        print(f"   Endpoint: {settings.SQS_ENDPOINT_URL}")
    
    sqs = get_sqs_client()
    cleared_count = 0
    
    for queue_name in ALL_QUEUES:
        cleared_count += clear_queue(sqs, queue_name)
    
    print(f"\n   已清空 {cleared_count} 个队列")
    return cleared_count


def main():
    parser = argparse.ArgumentParser(description='清空 DynamoDB 表和 SQS 队列数据')
    parser.add_argument('--tables-only', action='store_true', help='仅清空 DynamoDB 表')
    parser.add_argument('--queues-only', action='store_true', help='仅清空 SQS 队列')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认提示')
    args = parser.parse_args()
    
    print("=" * 50)
    print("Nexus-AI 数据清理工具")
    print("=" * 50)
    
    # 确认操作
    if not args.yes:
        print("\n⚠️  警告: 此操作将删除所有数据，无法恢复！")
        confirm = input("\n确认要继续吗？(输入 'yes' 确认): ")
        if confirm.lower() != 'yes':
            print("操作已取消")
            sys.exit(0)
    
    try:
        if args.queues_only:
            clear_queues()
        elif args.tables_only:
            clear_tables()
        else:
            clear_tables()
            clear_queues()
        
        print("\n" + "=" * 50)
        print("✅ 数据清理完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
