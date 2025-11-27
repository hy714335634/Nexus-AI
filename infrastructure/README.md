# NexusAI Infrastructure as Code

使用 Terraform 一键部署 NexusAI 所需的 AWS 基础设施。

## 📁 目录结构

```
infrastructure/
├── 核心配置
│   ├── versions.tf              # Terraform & Provider 版本
│   ├── main.tf                  # Provider 配置
│   ├── variables.tf             # 变量定义
│   └── outputs.tf               # 输出定义
│
├── 资源定义（按依赖层级）
│   ├── 02-storage-*.tf          # DynamoDB
│   └── 03-messaging-sqs.tf      # SQS 队列
│
└── docs/                        # 详细文档
    ├── ARCHITECTURE.md          # 架构设计
    └── ...
```

## 🏗️ 架构组件

- **DynamoDB**: 5个表用于存储项目、Agent、会话等数据
- **SQS**: 异步通知队列

## 🚀 快速开始

### 1. 配置参数

```bash
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

配置示例：
```hcl
# AWS 配置
aws_region     = "us-east-1"
aws_access_key = ""  # 留空使用 AWS profile
aws_secret_key = ""

# 项目配置
project_name = "nexus-ai"
environment  = "dev"
```

### 2. 初始化

```bash
terraform init
```

### 3. 预览变更

```bash
terraform plan
```

### 4. 部署

```bash
terraform apply
```

### 5. 查看输出

```bash
terraform output
```

## 📋 主要变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `aws_region` | AWS 区域 | us-east-1 |
| `project_name` | 项目名称前缀 | nexus-ai |
| `environment` | 环境 (dev/staging/prod) | dev |
| `enable_dynamodb` | 启用 DynamoDB | true |
| `enable_sqs` | 启用 SQS | true |

## 📊 DynamoDB 表结构

1. **AgentProjects**: 项目记录
   - 主键: project_id
   - GSI: UserIndex, StatusIndex

2. **AgentInstances**: Agent 实例
   - 主键: agent_id
   - GSI: ProjectIndex, StatusIndex, CategoryIndex

3. **AgentInvocations**: Agent 调用记录
   - 主键: invocation_id
   - GSI: AgentInvocationIndex

4. **AgentSessions**: Agent 会话
   - 主键: agent_id, session_id
   - GSI: LastActiveIndex

5. **AgentSessionMessages**: 会话消息
   - 主键: session_id, created_at

## 🔄 管理命令

```bash
# 查看状态
terraform show

# 查看输出
terraform output

# 更新基础设施
terraform apply

# 销毁资源
terraform destroy

# 格式化代码
terraform fmt

# 验证配置
terraform validate
```

## 💰 成本估算

使用默认配置的预估月成本（轻度使用）：
- DynamoDB (5 tables): ~$12
- SQS: ~$0-1

**总计**: ~$12-13/月

## 🔒 安全建议

1. **不要提交敏感信息**
   - `terraform.tfvars` 已在 `.gitignore` 中
   - 使用 AWS profile 而非硬编码密钥

2. **最小权限原则**
   - 所有资源遵循最小权限原则

3. **启用加密**
   - DynamoDB 默认加密

## 📚 详细文档

- [架构设计](docs/ARCHITECTURE.md) - 系统架构和依赖关系
- [最终结构](docs/FINAL_STRUCTURE.md) - 目录结构说明
- [改进记录](docs/IMPROVEMENTS.md) - 重组改进历史

## 🐛 故障排查

### Terraform 初始化失败
```bash
rm -rf .terraform
terraform init
```


## 📞 支持

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS DynamoDB](https://docs.aws.amazon.com/dynamodb/)
- [AWS SQS](https://docs.aws.amazon.com/sqs/)
