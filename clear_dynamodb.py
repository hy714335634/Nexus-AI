#!/usr/bin/env python3
import boto3

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# 表名列表
tables = [
    'AgentInstances',
    'AgentInvocations', 
    'AgentProjects',
    'AgentSessionMessages',
    'AgentSessions'
]

for table_name in tables:
    table = dynamodb.Table(table_name)
    
    # 获取表的键模式
    key_schema = table.key_schema
    key_names = [key['AttributeName'] for key in key_schema]
    
    print(f"清空表: {table_name}")
    print(f"主键: {key_names}")
    
    # 扫描并删除所有项
    scan_kwargs = {}
    deleted_count = 0
    
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
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
    
    print(f"已删除 {deleted_count} 条记录\n")

print("所有表已清空完成！")
