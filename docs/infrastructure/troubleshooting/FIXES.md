# 故障修复记录

## 1. API DynamoDB连接失败

**问题**: API返回 "Failed to establish DynamoDB connection"

**原因**:
- Docker容器无法访问EC2 IAM角色凭证
- 缺少 `dynamodb:ListTables` 权限

**解决方案**:
- 添加 `network_mode: host` 到docker-compose.yml
- 添加 `AWS_REGION` 和 `AWS_DEFAULT_REGION` 环境变量
- 添加 `dynamodb:ListTables` IAM权限

**文件修改**:
- `scripts/ec2-api-userdata.sh`
- `05-compute-ec2-iam.tf`

## 2. Bastion EFS挂载失败

**问题**: Bastion启动脚本报错 "syntax error near unexpected token `('"

**原因**: Terraform templatefile会解析bash算术展开 `$((...))`

**解决方案**: 使用 `$(expr ...)` 代替 `$((...))`

**文件修改**:
- `scripts/bastion-userdata.sh`

## 3. 前端容器健康检查失败

**问题**: ECS容器不断重启，健康检查失败

**原因**: 容器内缺少curl/wget工具，健康检查命令无法执行

**解决方案**: 移除容器级健康检查，只依赖ALB健康检查

**文件修改**:
- `05-compute-ecs.tf`

## 验证

```bash
# API测试
curl http://<ALB_DNS>/api/v1/statistics/overview

# Bastion EFS
ssh ec2-user@<BASTION_IP>
df -h /mnt/efs

# 前端测试
curl http://<ALB_DNS>/
```
