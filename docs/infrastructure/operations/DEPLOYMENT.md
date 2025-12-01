# 部署指南

## 快速部署

```bash
cd infrastructure

# 1. 配置变量
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# 2. 初始化
terraform init

# 3. 部署
terraform apply -auto-approve
```

## 重新部署

```bash
# 完全重建
terraform destroy -auto-approve
terraform apply -auto-approve

# 仅更新API实例（零停机）
./scripts/refresh-api-instances.sh
```

## 常用命令

```bash
# 查看输出
terraform output

# 查看状态
terraform show

# 格式化代码
terraform fmt

# 验证配置
terraform validate
```

## 访问服务

```bash
# 获取ALB地址
terraform output alb_dns_name

# 测试API
curl http://<ALB_DNS>/api/v1/statistics/overview

# 测试前端
curl http://<ALB_DNS>/

# SSH到bastion
terraform output bastion_ssh_command
```

## 故障排查

参见 [troubleshooting/FIXES.md](../troubleshooting/FIXES.md)
