# Fargate部署优化说明（中文版）

## 优化概述

根据您的本地部署方式（`uvicorn api.main:app --host 0.0.0.0 --port 8000`）和工作流执行需求，对Terraform配置进行了全面优化，使后端API能够在Fargate中高效运行Python异步工作流。

## 主要优化内容

### 1. ✅ CPU和内存配置优化

**问题**: 工作流通过Python ThreadPoolExecutor执行（最大5个工作线程），需要足够的CPU和内存资源支持并发任务。

**优化方案**:
- 默认CPU从 2 vCPU (2048) 提升到 **4 vCPU (4096)**
- 默认内存从 4GB (4096 MB) 提升到 **8GB (8192 MB)**
- 这可以支持5个并发工作流同时执行，避免资源冲突

**修改文件**: `variables.tf`

### 2. ✅ 工作流并发控制

**问题**: 需要可配置的工作流并发数，避免在高负载时资源冲突。

**优化方案**:
- 新增 `max_workflow_workers` 变量（默认值为5）
- 通过环境变量 `MAX_WORKFLOW_WORKERS` 传递给容器
- 后端代码可以通过此环境变量动态调整ThreadPoolExecutor的max_workers

**修改文件**: `variables.tf`, `05-compute-ecs.tf`

### 3. ✅ EFS共享存储配置

**问题**: Bastion和后端服务需要使用同一个repo和EFS目录来构建agent。

**优化方案**:
- EFS访问点改为根目录访问 (`/`)，所有服务共享整个EFS文件系统
- EFS挂载路径统一为 `/mnt/efs`
- Repo目录: `/mnt/efs/nexus-ai-repo`
- Projects目录: `/mnt/efs/nexus-ai-repo/projects`
- 确保Bastion和Fargate容器都访问同一个目录

**修改文件**: `02-storage-efs.tf`

### 4. ✅ 容器启动命令优化

**问题**: 容器需要访问EFS上的projects目录，但代码在容器镜像中。

**优化方案**:
- 添加启动脚本，在启动uvicorn前创建projects目录symlink
- 确保容器中的 `/app/projects` 指向EFS上的 `/mnt/efs/nexus-ai-repo/projects`
- 使用与本地部署完全相同的启动命令: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

**修改文件**: `05-compute-ecs.tf`

### 5. ✅ 环境变量配置

**新增环境变量**:
- `REPO_ROOT`: `/mnt/efs/nexus-ai-repo` - EFS上的repo根目录
- `PROJECTS_ROOT`: `/mnt/efs/nexus-ai-repo/projects` - 项目数据目录
- `MAX_WORKFLOW_WORKERS`: 工作流并发数（默认5）
- `EFS_MOUNT_PATH`: `/mnt/efs` - EFS挂载路径

这些环境变量可以让后端代码灵活地访问EFS上的资源。

**修改文件**: `05-compute-ecs.tf`

### 6. ✅ 健康检查优化

**优化**:
- 启动等待时间从60秒增加到90秒，给容器更多时间进行EFS挂载和初始化

**修改文件**: `05-compute-ecs.tf`

## 关于Fargate中运行异步工作流

### 是否适合在Fargate中运行？

**答案: 完全适合** ✅

1. **Python异步线程执行**: 工作流使用ThreadPoolExecutor在独立线程中执行，完全可以在Fargate容器中运行
2. **资源隔离**: 每个容器实例都有独立的CPU和内存资源
3. **无需Docker构建**: 您提到后端API不再涉及docker build，所以在Fargate中运行完全没有问题

### 资源冲突问题

**如果构建任务较多，是否会有资源冲突？**

**解决方案**:

1. **合理的资源配置**:
   - 4 vCPU + 8GB内存可以支持5个并发工作流
   - 如果任务较多，可以增加服务实例数 (`api_desired_count`)

2. **并发控制**:
   - 通过 `MAX_WORKFLOW_WORKERS` 环境变量控制单实例并发数
   - 默认值5可以根据实际情况调整

3. **水平扩展**:
   - 如果负载很高，可以增加 `api_desired_count` 来增加容器实例数
   - 多个实例可以并行处理更多任务

4. **建议的配置策略**:
   ```
   小型负载: 1-2个实例，每个实例3-5个工作流
   中型负载: 2-4个实例，每个实例5个工作流
   大型负载: 4+个实例，或考虑使用任务队列系统
   ```

## 优化前后对比

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| CPU | 2 vCPU (2048) | 4 vCPU (4096) |
| 内存 | 4GB (4096 MB) | 8GB (8192 MB) |
| 工作流并发控制 | 无 | 可配置（默认5） |
| EFS访问 | 限制在/app-data | 根目录访问，共享repo |
| 启动命令 | Docker镜像CMD | 与本地一致，支持EFS symlink |
| 健康检查等待 | 60秒 | 90秒 |

## 部署和使用

### 1. 更新配置（可选）

如果需要自定义配置，在 `terraform.tfvars` 中设置：

```hcl
# CPU和内存配置
api_cpu = 4096      # 4 vCPU
api_memory = 8192   # 8GB

# 工作流并发数
max_workflow_workers = 5

# 服务实例数
api_desired_count = 2
```

### 2. 应用配置

```bash
cd infrastructure
terraform plan
terraform apply
```

### 3. 验证部署

- 检查ECS服务状态
- 查看容器日志: CloudWatch Logs
- 测试API健康检查: `curl http://<alb-dns>/health`
- 验证EFS挂载: 检查容器日志中是否有EFS挂载错误

## 与Bastion的协同

### 共享Repo和EFS

1. **Repo克隆**: Bastion在初始化时会克隆repo到 `/mnt/efs/nexus-ai-repo`
2. **代码更新**: 在Bastion上执行 `git pull` 更新代码，所有服务都可以访问最新代码
3. **项目数据**: 所有服务共享 `/mnt/efs/nexus-ai-repo/projects` 目录

### 工作流程

```
1. Bastion: git clone/pull 到 EFS
2. Fargate容器: 通过EFS访问repo和projects
3. 构建Agent: 使用EFS上的repo和projects目录
4. 所有服务共享同一个数据源
```

## 注意事项

1. **EFS性能**: EFS使用bursting模式，对于高IO负载可能需要考虑provisioned throughput
2. **网络延迟**: 确保Fargate任务在私有子网中，与EFS挂载目标在同一可用区可以减少延迟
3. **成本优化**: 
   - Fargate按CPU和内存使用量计费
   - EFS按存储量计费
   - 合理配置资源可以节省成本

## 故障排查

### 容器无法启动
- 检查EFS挂载目标和安全组配置
- 查看CloudWatch Logs中的错误信息
- 验证IAM角色有EFS访问权限

### 工作流执行失败
- 检查EFS挂载状态（容器日志）
- 验证projects目录权限（uid/gid 1000）
- 查看工作流执行日志

### 性能问题
- 监控CloudWatch指标：CPUUtilization, MemoryUtilization
- 考虑增加资源或服务实例数
- 检查EFS性能指标（IOPS, Throughput）

## 后续优化建议

1. **监控告警**: 设置CloudWatch告警监控资源使用率
2. **自动扩展**: 配置基于CPU/内存的自动扩展策略
3. **任务队列**: 如果任务量很大，考虑使用SQS管理任务分发
4. **日志聚合**: 确保所有日志都发送到CloudWatch Logs便于排查

## 总结

✅ **所有优化已完成**:
- ECS Fargate配置优化（CPU/内存）
- 工作流并发控制
- EFS共享存储配置
- 容器启动命令优化
- 环境变量配置
- 健康检查优化

现在后端API可以在Fargate中高效运行异步工作流，与本地部署方式保持一致，并确保Bastion和所有服务共享同一个repo和EFS目录。

