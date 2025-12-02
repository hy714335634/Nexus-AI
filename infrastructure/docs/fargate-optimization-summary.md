# Fargate部署优化总结

## 优化概述

根据本地部署方式和工作流执行需求，对Terraform配置进行了全面优化，使后端API能够在Fargate中高效运行异步工作流。

## 主要优化点

### 1. CPU和内存配置优化

**问题**: 工作流通过ThreadPoolExecutor执行，最大5个工作线程，需要足够的CPU和内存资源。

**优化**:
- 默认CPU从2 vCPU (2048) 提升到 **4 vCPU (4096)**
- 默认内存从4GB (4096 MB) 提升到 **8GB (8192 MB)**
- 支持高并发工作流执行，避免资源冲突

**配置文件**: `variables.tf`
```hcl
variable "api_cpu" {
  description = "CPU units for API service (1024 = 1 vCPU). For workflows with async threads, recommend at least 4096 (4 vCPU)"
  default     = 4096
}

variable "api_memory" {
  description = "Memory for API service in MB. For workflows with async threads, recommend at least 8192 MB"
  default     = 8192
}
```

### 2. 工作流并发控制

**问题**: 工作流并发数需要可配置，避免资源冲突。

**优化**:
- 添加 `max_workflow_workers` 变量（默认5）
- 通过环境变量 `MAX_WORKFLOW_WORKERS` 传递给容器
- 后端代码可以通过此环境变量动态调整ThreadPoolExecutor的max_workers

**配置文件**: `variables.tf`
```hcl
variable "max_workflow_workers" {
  description = "Maximum number of concurrent workflow workers (ThreadPoolExecutor max_workers)"
  default     = 5
}
```

### 3. EFS共享存储优化

**问题**: Bastion和后端服务需要使用同一个repo和EFS目录来构建agent。

**优化**:
- EFS访问点改为根目录访问 (`/`)，所有服务共享整个EFS文件系统
- EFS挂载路径统一为 `/mnt/efs`
- Repo目录统一为 `/mnt/efs/nexus-ai-repo`
- Projects目录统一为 `/mnt/efs/nexus-ai-repo/projects`

**配置文件**: `02-storage-efs.tf`
```hcl
resource "aws_efs_access_point" "app_data" {
  # 使用根目录 "/" 允许访问所有路径
  root_directory {
    path = "/"
    ...
  }
}
```

### 4. 容器启动命令优化

**问题**: 容器需要访问EFS上的projects目录，但代码在容器镜像中。

**优化**:
- 添加启动脚本，在启动uvicorn前创建projects目录symlink
- 确保容器中的 `/app/projects` 指向EFS上的 `/mnt/efs/nexus-ai-repo/projects`
- 使用与本地部署相同的启动命令: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

**配置文件**: `05-compute-ecs.tf`
```hcl
command = [
  "sh",
  "-c",
  <<-EOT
    # Create projects directory symlink to EFS
    if [ ! -d /app/projects ] && [ -d /mnt/efs/nexus-ai-repo/projects ]; then
      ln -sf /mnt/efs/nexus-ai-repo/projects /app/projects || true
    fi
    mkdir -p /app/projects
    exec uvicorn api.main:app --host 0.0.0.0 --port 8000
  EOT
]
```

### 5. 环境变量配置

**新增环境变量**:
- `REPO_ROOT`: `/mnt/efs/nexus-ai-repo` - EFS上的repo根目录
- `PROJECTS_ROOT`: `/mnt/efs/nexus-ai-repo/projects` - 项目数据目录
- `MAX_WORKFLOW_WORKERS`: 工作流并发数（默认5）
- `EFS_MOUNT_PATH`: `/mnt/efs` - EFS挂载路径

这些环境变量可以让后端代码灵活地访问EFS上的资源。

### 6. 健康检查优化

**优化**:
- 启动等待时间从60秒增加到90秒，给容器更多时间进行初始化和EFS挂载

## Fargate vs EC2 考虑

### Fargate的优势

1. **无需管理服务器**: 完全托管的容器服务
2. **自动扩展**: 根据负载自动扩展
3. **安全性**: 每个任务都有独立的网络命名空间

### Fargate中的工作流执行

**异步线程执行**:
- 工作流通过Python的ThreadPoolExecutor执行
- 在Fargate中运行完全可行
- 线程在容器内执行，共享容器的CPU和内存资源

**资源冲突处理**:
- 通过 `MAX_WORKFLOW_WORKERS` 环境变量控制并发数
- 合理的CPU和内存配置（4 vCPU, 8GB）可以支持5个并发工作流
- 如果构建任务较多，可以通过以下方式优化：
  - 增加 `api_desired_count` 来增加服务实例数
  - 调整 `max_workflow_workers` 来控制单实例并发数
  - 使用队列系统（如SQS）来管理任务分发

### 建议配置

**小型部署** (开发/测试环境):
- CPU: 4096 (4 vCPU)
- Memory: 8192 MB (8GB)
- Desired Count: 1-2
- Max Workers: 3-5

**生产环境** (中等负载):
- CPU: 4096 (4 vCPU) 或 8192 (8 vCPU)
- Memory: 8192 MB (8GB) 或 16384 MB (16GB)
- Desired Count: 2-4
- Max Workers: 5-10

**高负载环境**:
- 考虑使用多个服务实例 + 任务队列
- 或使用EC2部署以获得更多控制权

## 与本地部署的一致性

| 项目 | 本地部署 | Fargate部署 |
|------|---------|------------|
| 启动命令 | `uvicorn api.main:app --host 0.0.0.0 --port 8000` | 相同 |
| 工作目录 | 项目根目录 | `/app` (容器内) |
| 代码路径 | 本地文件系统 | 容器镜像 (已复制) |
| Projects目录 | `./projects` | `/app/projects` -> `/mnt/efs/nexus-ai-repo/projects` |
| 工作流执行 | ThreadPoolExecutor | 相同 |

## 部署步骤

1. **更新Terraform变量** (如需要):
   ```bash
   # 在 terraform.tfvars 中设置
   api_cpu = 4096
   api_memory = 8192
   max_workflow_workers = 5
   ```

2. **应用Terraform配置**:
   ```bash
   terraform plan
   terraform apply
   ```

3. **验证部署**:
   - 检查ECS服务状态
   - 验证容器日志
   - 测试API健康检查端点
   - 验证EFS挂载

## 注意事项

1. **EFS挂载**: 确保EFS挂载目标和安全组配置正确
2. **IAM权限**: 确保任务执行角色有EFS访问权限
3. **网络配置**: 确保Fargate任务在私有子网中，可以访问EFS挂载目标
4. **成本优化**: Fargate按使用量计费，合理配置CPU和内存可以节省成本

## 后续优化建议

1. **监控和告警**: 设置CloudWatch告警监控CPU和内存使用率
2. **自动扩展**: 配置基于CPU/内存使用率的自动扩展
3. **任务队列**: 如果任务量很大，考虑使用SQS队列来管理任务分发
4. **日志聚合**: 确保所有日志都发送到CloudWatch Logs

## 问题排查

### 容器无法启动
- 检查EFS挂载目标和安全组
- 查看CloudWatch Logs中的错误信息
- 验证IAM角色权限

### 工作流执行失败
- 检查EFS挂载状态
- 验证projects目录权限
- 查看工作流日志

### 性能问题
- 监控CPU和内存使用率
- 考虑增加资源或服务实例数
- 检查EFS性能指标

