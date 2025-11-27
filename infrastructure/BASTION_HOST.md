# Bastion Host (代理主机) 配置说明

## 📋 概述

Bastion Host 是一个轻量级的 EC2 实例，用于作为代理服务器访问部署在私有网络中的应用。

## 🔧 配置

### 特性

- **实例类型**: `t4g.nano` (1 vCPU, 1 GB RAM, ARM 架构)
- **操作系统**: Amazon Linux 2023 (ARM64)
- **网络位置**: 公有子网（第一个公有子网）
- **存储**: 8GB GP3 加密卷
- **弹性 IP**: 自动分配，确保 IP 地址不变
- **SSH 访问**: 允许从 `0.0.0.0/0` SSH 访问（可根据需要限制）

### 配置变量

在 `terraform.tfvars` 中配置：

```hcl
# 启用 Bastion Host
enable_bastion = true

# AWS Key Pair 名称（必须在 AWS 中已存在）
bastion_key_name = "your-existing-key-pair-name"
```

### 前置条件

1. **Key Pair 必须在 AWS 中存在**
   ```bash
   # 列出现有的 Key Pairs
   aws ec2 describe-key-pairs --region us-west-2
   ```

2. **如果 Key Pair 不存在，需要先创建**
   ```bash
   # 创建新的 Key Pair
   aws ec2 create-key-pair \
     --key-name my-bastion-key \
     --region us-west-2 \
     --query 'KeyMaterial' \
     --output text > ~/.ssh/my-bastion-key.pem
   
   chmod 400 ~/.ssh/my-bastion-key.pem
   ```

## 🚀 部署

### 1. 配置变量

编辑 `terraform.tfvars`：

```hcl
enable_bastion = true
bastion_key_name = "your-key-name"
```

### 2. 应用配置

```bash
cd infrastructure
terraform apply
```

### 3. 获取连接信息

```bash
# 获取 Bastion Host 公网 IP
terraform output bastion_public_ip

# 获取 SSH 连接命令
terraform output bastion_ssh_command
```

## 🔐 SSH 连接

### 使用 Terraform 输出的命令

```bash
# Terraform 会输出完整的 SSH 命令
ssh -i ~/.ssh/your-key-name.pem ec2-user@<PUBLIC_IP>
```

### 手动连接

```bash
# 替换 <PUBLIC_IP> 和 <KEY_NAME> 为实际值
ssh -i ~/.ssh/<KEY_NAME>.pem ec2-user@<PUBLIC_IP>
```

## 📊 成本估算

- **t4g.nano 实例**: 约 $0.0034/小时（按需定价）
- **Elastic IP**: 免费（当关联到运行中的实例时）
- **存储 (8GB GP3)**: 约 $0.08/月
- **数据传输**: 根据实际使用

**月成本估算**: 约 $2.5 - $3/月（如果 24/7 运行）

## 🛡️ 安全建议

### 1. 限制 SSH 访问（可选）

默认允许从 `0.0.0.0/0` SSH 访问。如果需要限制，修改 `09-bastion-host.tf`：

```terraform
ingress {
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = ["YOUR_IP/32"]  # 替换为你的 IP 地址
  description = "SSH access from specific IP"
}
```

### 2. 使用 SSH 密钥认证

确保：
- Key Pair 的私钥文件权限正确：`chmod 400 ~/.ssh/key-name.pem`
- 不要将私钥提交到版本控制

### 3. 定期更新

定期更新系统包：

```bash
sudo yum update -y
```

## 🔍 使用场景

### 1. 访问 ALB（如果限制为 VPC 内部访问）

```bash
# 通过 Bastion Host 访问 ALB
ssh -i ~/.ssh/key.pem ec2-user@<BASTION_IP>
curl http://<ALB_DNS_NAME>
```

### 2. 访问 ECS 服务（如果需要）

```bash
# SSH 到 Bastion Host
ssh -i ~/.ssh/key.pem ec2-user@<BASTION_IP>

# 安装 AWS CLI（如果未安装）
sudo yum install aws-cli -y

# 配置 AWS 凭证或使用 IAM 角色
aws configure

# 查看 ECS 服务状态
aws ecs list-services --cluster nexus-ai-ecs-prod
```

### 3. 端口转发

```bash
# 通过 Bastion Host 转发端口访问内部服务
ssh -i ~/.ssh/key.pem \
    -L 8000:<INTERNAL_HOST>:8000 \
    ec2-user@<BASTION_IP>

# 然后在本地访问
curl http://localhost:8000
```

## 🗑️ 删除

如果需要删除 Bastion Host：

```hcl
# 在 terraform.tfvars 中设置
enable_bastion = false
```

然后运行：

```bash
terraform apply
```

## 📝 注意事项

1. **Key Pair 必须预先存在**: Terraform 不会创建 Key Pair，只会引用现有的
2. **Elastic IP**: 当实例停止时，Elastic IP 仍然会保留（除非手动释放）
3. **成本**: 即使实例停止，Elastic IP 可能会产生费用（如果未关联到运行中的实例）
4. **ARM 架构**: t4g 实例使用 ARM 架构，确保兼容性

## 🔄 输出值

Terraform 会输出以下信息：

- `bastion_public_ip`: Bastion Host 的公网 IP 地址
- `bastion_instance_id`: EC2 实例 ID
- `bastion_ssh_command`: 完整的 SSH 连接命令

查看所有输出：

```bash
terraform output
```

