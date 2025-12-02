# Terraform 网络问题排查指南

## 常见错误

### 1. DNS 解析失败
```
Error: dial tcp: lookup dynamodb.us-west-2.amazonaws.com: no such host
```

### 2. Docker 推送 EOF 错误
```
EOF
The push refers to repository [...]
```

## 解决方案

### 方案 1: 检查网络连接

```bash
# 检查 DNS 解析
nslookup dynamodb.us-west-2.amazonaws.com

# 检查 AWS 连接
aws sts get-caller-identity

# 检查网络连接（AWS 服务通常不允许 ping，但可以测试 HTTPS）
curl -I https://dynamodb.us-west-2.amazonaws.com
```

### 方案 2: 重试 Terraform 操作

网络问题通常是临时的，直接重试：

```bash
cd infrastructure
terraform apply
```

### 方案 3: 跳过 Docker 构建（如果镜像已存在）

如果只是网络问题导致 Docker 推送失败，但镜像已经构建好：

```bash
# 设置环境变量跳过 Docker 构建
export TF_VAR_skip_docker_build=true
terraform apply
```

### 方案 4: 分步执行

如果网络不稳定，可以分步执行：

```bash
# 1. 先创建基础设施（跳过 Docker 构建）
export TF_VAR_skip_docker_build=true
terraform apply -target=aws_ecr_repository.api -target=aws_ecr_repository.frontend

# 2. 手动构建和推送镜像
cd ..
./infrastructure/scripts/build-and-push.sh

# 3. 继续部署
unset TF_VAR_skip_docker_build
terraform apply
```

### 方案 5: 使用 VPN 或代理

如果在中国大陆，可能需要使用 VPN 或代理：

```bash
# 设置代理（如果需要）
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# 然后运行 Terraform
terraform apply
```

### 方案 6: 检查防火墙设置

确保以下端口未被阻止：
- HTTPS (443) - AWS API 调用
- Docker registry 端口（ECR 使用 HTTPS）

## 已添加的改进

### 1. Terraform Provider 重试配置
- 已添加 `max_retries = 5` 到 AWS provider
- 自动重试失败的 API 调用

### 2. Docker 推送重试机制
- 已添加重试逻辑到 Docker 推送命令
- 最多重试 3 次，每次间隔 10 秒

## 预防措施

1. **使用稳定的网络连接**
   - 避免在弱网络环境下部署
   - 考虑使用 AWS CloudShell 或 EC2 实例执行 Terraform

2. **分批部署**
   - 先创建基础设施
   - 再构建和推送镜像
   - 最后部署服务

3. **监控网络状态**
   - 在部署前检查网络连接
   - 使用 `aws ecr describe-repositories` 测试 ECR 连接

## 如果问题持续

1. **检查 AWS 服务状态**
   - 访问 https://status.aws.amazon.com/
   - 确认 DynamoDB 和 ECR 服务正常

2. **检查 AWS 凭证**
   ```bash
   aws configure list
   aws sts get-caller-identity
   ```

3. **查看详细日志**
   ```bash
   # 启用 Terraform 详细日志
   export TF_LOG=DEBUG
   terraform apply 2>&1 | tee terraform.log
   ```

4. **联系支持**
   - 收集错误日志
   - 记录发生时间
   - 提供网络环境信息

