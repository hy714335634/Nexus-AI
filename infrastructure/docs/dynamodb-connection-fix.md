# DynamoDB连接问题修复

## 问题描述

API服务返回500错误：
```
Failed to get statistics overview: Failed to get statistics overview: Failed to list agents: Failed to establish DynamoDB connection
```

## 原因分析

1. **IAM权限问题**：`ListTables`权限需要独立的权限语句，Resource必须是`"*"`，因为它是一个列表操作，不是针对特定表的操作。

2. **健康检查失败**：API代码中的DynamoDB健康检查使用`list_tables()`方法验证连接，如果该权限不正确配置，会导致连接失败。

## 修复内容

### 1. 修复IAM策略

更新了`04-compute-iam.tf`中的DynamoDB IAM策略，将`ListTables`权限分离为独立的语句：

```hcl
Statement = [
  {
    # 表操作权限（针对特定表）
    Effect = "Allow"
    Action = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:DescribeTable",
      "dynamodb:CreateTable"
    ]
    Resource = [
      # 具体表的ARN...
    ]
  },
  {
    # ListTables权限（需要Resource = "*"）
    Effect = "Allow"
    Action = [
      "dynamodb:ListTables"
    ]
    Resource = "*"
  }
]
```

## 验证步骤

### 1. 应用Terraform更改

```bash
cd infrastructure
terraform plan   # 查看更改
terraform apply  # 应用修复
```

### 2. 验证IAM策略

```bash
# 获取Task Role ARN
TASK_ROLE_ARN=$(aws iam list-roles \
  --query 'Roles[?RoleName==`nexus-ai-ecs-task-prod`].Arn' \
  --output text \
  --region us-west-2)

# 检查策略
aws iam list-role-policies \
  --role-name nexus-ai-ecs-task-prod \
  --region us-west-2

# 查看DynamoDB策略详情
aws iam get-role-policy \
  --role-name nexus-ai-ecs-task-prod \
  --policy-name nexus-ai-ecs-dynamodb-prod \
  --region us-west-2
```

### 3. 验证DynamoDB表存在

```bash
# 列出所有DynamoDB表
aws dynamodb list-tables --region us-west-2

# 验证每个表存在
TABLES=(
  "nexus-ai-agent-projects-prod"
  "nexus-ai-agent-instances-prod"
  "nexus-ai-agent-invocations-prod"
  "nexus-ai-agent-sessions-prod"
  "nexus-ai-agent-session-messages-prod"
)

for TABLE in "${TABLES[@]}"; do
  echo "Checking table: $TABLE"
  aws dynamodb describe-table \
    --table-name "$TABLE" \
    --region us-west-2 \
    --query 'Table.TableStatus' \
    --output text
done
```

### 4. 测试API连接

```bash
# 测试统计接口
curl -X 'GET' \
  'http://nexus-ai-alb-prod-1976436081.us-west-2.elb.amazonaws.com/api/v1/statistics/overview' \
  -H 'accept: application/json'

# 应该返回200 OK，而不是500错误
```

### 5. 查看ECS任务日志

如果问题仍然存在，查看API容器的日志：

```bash
# 获取日志流
aws logs tail /ecs/nexus-ai-api-prod \
  --follow \
  --region us-west-2 \
  --format short
```

查找DynamoDB相关的错误信息。

## 其他可能的问题

如果修复后仍然无法连接，检查以下项目：

### 1. DynamoDB表是否已创建

```bash
cd infrastructure
terraform output dynamodb_tables
```

### 2. ECS任务是否使用了正确的Task Role

```bash
# 获取Task Definition
TASK_DEF=$(aws ecs describe-task-definition \
  --task-definition nexus-ai-api-prod \
  --region us-west-2 \
  --query 'taskDefinition.taskRoleArn' \
  --output text)

echo "Task Role ARN: $TASK_DEF"
# 应该显示: arn:aws:iam::<account>:role/nexus-ai-ecs-task-prod
```

### 3. 网络连接问题

检查ECS任务是否能访问DynamoDB服务端点：

```bash
# 在ECS任务中执行（需要exec权限）
aws ecs execute-command \
  --cluster nexus-ai-cluster-prod \
  --task <task-id> \
  --container api \
  --command "curl -I https://dynamodb.us-west-2.amazonaws.com" \
  --interactive \
  --region us-west-2
```

### 4. 区域配置

确认API服务的`DYNAMODB_REGION`环境变量设置正确：

```bash
# 检查Task Definition中的环境变量
aws ecs describe-task-definition \
  --task-definition nexus-ai-api-prod \
  --region us-west-2 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`DYNAMODB_REGION`]' \
  --output table
```

## 故障排查步骤总结

1. ✅ 应用IAM策略修复：`terraform apply`
2. ✅ 验证DynamoDB表存在：`aws dynamodb list-tables`
3. ✅ 验证Task Role正确配置
4. ✅ 测试API接口：`curl /api/v1/statistics/overview`
5. ✅ 查看日志：`aws logs tail /ecs/nexus-ai-api-prod`

## 相关文件

- IAM策略配置：`infrastructure/04-compute-iam.tf`
- DynamoDB表定义：`infrastructure/02-storage-dynamodb.tf`
- API DynamoDB客户端：`api/database/dynamodb_client.py`

