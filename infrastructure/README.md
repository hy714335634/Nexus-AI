# NexusAI Infrastructure as Code

使用 Terraform 一键部署 NexusAI 所需的 AWS 基础设施。

## 🚀 快速开始

```bash
# 1. 配置参数
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# 2. 初始化并部署
terraform init
terraform apply -auto-approve

# 3. 获取访问地址
terraform output alb_dns_name
```

## 📁 目录结构

```
infrastructure/
├── *.tf                    # Terraform配置文件
├── scripts/                # 部署脚本
│   ├── ec2-api-userdata.sh
│   ├── bastion-userdata.sh
│   └── *.sh               # 运维脚本
├── docs/                   # 文档
│   ├── operations/        # 运维文档
│   ├── troubleshooting/   # 故障排查
│   └── architecture/      # 架构设计
└── README.md
```

## 🏗️ 架构组件

- **VPC**: 2个公有子网 + 2个私有子网
- **ALB**: 应用负载均衡器
- **EC2**: API服务（Auto Scaling）
- **ECS Fargate**: 前端服务
- **EFS**: 共享存储（代码仓库 + 用户数据）
- **DynamoDB**: 5个表（项目、Agent、会话等）
- **SQS**: 异步通知队列
- **Bastion**: 跳板机

## 📋 主要变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `aws_region` | AWS区域 | us-west-2 |
| `project_name` | 项目名称 | nexus-ai |
| `environment` | 环境 | prod |
| `api_deploy_on_ec2` | API部署方式 | true |
| `alb_allowed_cidr_blocks` | ALB访问白名单 | VPC CIDR |

## 🔧 常用命令

```bash
# 查看输出
terraform output

# 更新基础设施
terraform apply

# 销毁资源
terraform destroy

# SSH到bastion
ssh -i ~/.ssh/Og_Normal.pem ec2-user@$(terraform output -raw bastion_public_ip)
```

## 📚 文档

- [部署指南](docs/operations/DEPLOYMENT.md)
- [故障排查](docs/troubleshooting/FIXES.md)
- [EFS存储架构](docs/architecture/EFS_STORAGE.md)

## 💰 成本估算

默认配置预估月成本（轻度使用）：
- EC2 (t3.xlarge × 2): ~$120
- ECS Fargate: ~$30
- DynamoDB: ~$12
- EFS: ~$5
- ALB: ~$20
- 其他: ~$10

**总计**: ~$200/月

## 🔒 安全

- 所有资源在VPC内
- 最小权限IAM策略
- DynamoDB加密
- IMDSv2强制启用
- 安全组严格限制

## 🐛 故障排查

常见问题参见 [docs/troubleshooting/FIXES.md](docs/troubleshooting/FIXES.md)

## 📞 支持

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Documentation](https://docs.aws.amazon.com/)
