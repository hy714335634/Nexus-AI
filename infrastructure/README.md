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
│   ├── 01-networking.tf         # VPC + 安全组
│   ├── 02-storage-*.tf          # DynamoDB + EFS
│   ├── 03-messaging-sqs.tf      # SQS 队列
│   ├── 04-compute-*.tf          # ECR + IAM + Lambda
│   └── 05-orchestration-sfn.tf  # Step Functions
│
├── modules/                     # 可复用模块
│   └── networking/vpc/          # VPC 模块
│
├── scripts/                     # 辅助脚本
│   ├── Makefile                 # 部署命令
│   └── Dockerfile               # Lambda 镜像
│
└── docs/                        # 详细文档
    ├── ARCHITECTURE.md          # 架构设计
    └── ...
```

## 🏗️ 架构组件

- **VPC**: 网络隔离和安全组
- **DynamoDB**: 5个表用于存储项目、Agent、会话等数据
- **EFS**: Lambda 持久化存储
- **SQS**: 异步通知队列
- **Lambda**: NexusAI Agent 函数（Docker 容器）
- **ECR**: Lambda 容器镜像仓库
- **Step Functions**: Agent 构建工作流（可选）

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

# VPC 配置（创建新 VPC）
create_vpc = true
vpc_cidr   = "10.0.0.0/16"

# 或使用现有 VPC
# create_vpc = false
# vpc_id     = "vpc-xxxxx"
# subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
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
| `enable_lambda` | 启用 Lambda | true |
| `enable_dynamodb` | 启用 DynamoDB | true |
| `enable_sqs` | 启用 SQS | true |
| `enable_stepfunctions` | 启用 Step Functions | false |
| `create_vpc` | 创建新 VPC | true |
| `vpc_cidr` | VPC CIDR 块 | 10.0.0.0/16 |
| `vpc_id` | 现有 VPC ID | "" |
| `subnet_ids` | 现有子网 IDs | [] |

## 🔧 VPC 配置

### 方式1: 自动创建新 VPC（推荐）

```hcl
create_vpc = true
vpc_cidr   = "10.0.0.0/16"
```

自动创建：
- 1 个 VPC
- 2 个私有子网（跨 2 个可用区）
- 1 个 Internet Gateway
- 路由表和关联

### 方式2: 使用现有 VPC

```hcl
create_vpc = false
vpc_id     = "vpc-xxxxx"
subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
```

要求：
- 至少 2 个子网在不同可用区
- 子网需要互联网连接
- 允许 EFS 挂载（端口 2049）

## 🐳 Lambda 部署

Lambda 使用 Docker 容器镜像部署。

### 1. 部署基础设施

```bash
terraform apply
```

### 2. 构建并推送镜像

```bash
cd scripts
make deploy-lambda

# 或分步执行
make docker-build  # 构建镜像
make docker-push   # 推送到 ECR 并更新 Lambda
```

### 3. 测试

```bash
terraform output lambda_function_url
curl $(terraform output -raw lambda_function_url)
```

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
- Lambda: ~$0-5
- EFS: ~$3-5
- SQS: ~$0-1
- VPC: 免费

**总计**: ~$15-25/月

## 🔒 安全建议

1. **不要提交敏感信息**
   - `terraform.tfvars` 已在 `.gitignore` 中
   - 使用 AWS profile 而非硬编码密钥

2. **最小权限原则**
   - Lambda IAM 角色仅授予必要权限
   - 使用 VPC 隔离

3. **启用加密**
   - DynamoDB 默认加密
   - EFS 启用加密

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

### Lambda 部署失败
检查 ECR 仓库和镜像：
```bash
aws ecr describe-repositories
aws ecr list-images --repository-name nexus-ai-lambda-dev
```

### VPC 配置错误
确保：
- 子网在不同可用区
- 子网有互联网连接
- 安全组允许 EFS 端口 2049

## 📞 支持

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS DynamoDB](https://docs.aws.amazon.com/dynamodb/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [AWS EFS](https://docs.aws.amazon.com/efs/)
