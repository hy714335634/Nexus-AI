# Redis 内存过度提交警告修复指南

## 问题描述

在 CloudWatch 日志中看到以下警告：
```
WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition.
```

## 问题原因

1. **ECS Fargate 限制**：在 ECS Fargate 容器环境中，无法直接修改主机的 `vm.overcommit_memory` sysctl 设置
2. **Redis 持久化需求**：Redis 在执行后台保存（RDB）或 AOF 重写时需要 fork 子进程，这需要内存过度提交支持
3. **容器环境特性**：容器环境默认可能没有启用内存过度提交

## 影响评估

### 当前状态
- ✅ Redis 服务正常运行
- ✅ 后台保存（RDB）成功完成
- ✅ AOF 持久化正常工作
- ⚠️ 警告信息存在，但不影响当前运行

### 潜在风险
- 在内存压力情况下，后台保存可能失败
- 如果内存不足，fork 操作可能失败
- 可能导致数据持久化失败

## 解决方案

### 方案 1：设置 maxmemory 限制（已实施）✅

**修改内容**：在 Redis 启动命令中添加 `--maxmemory` 参数

**优点**：
- 限制 Redis 使用的最大内存
- 避免 Redis 使用过多内存导致 fork 失败
- 配合 `allkeys-lru` 策略自动清理旧数据

**配置**：
```hcl
command = [
  "redis-server",
  "--appendonly", "yes",
  "--maxmemory-policy", "allkeys-lru",
  "--maxmemory", "3500mb",  # 设置为容器内存的 ~85%
  "--dir", "/tmp"
]
```

**内存计算**：
- 容器内存：4096 MB
- Redis maxmemory：3500 MB（约 85%）
- 预留空间：596 MB（用于系统、fork 操作等）

### 方案 2：禁用 RDB 快照（可选）

如果只需要 AOF 持久化，可以禁用 RDB 快照：

```hcl
command = [
  "redis-server",
  "--appendonly", "yes",
  "--save", "",  # 禁用 RDB 快照
  "--maxmemory-policy", "allkeys-lru",
  "--maxmemory", "3500mb",
  "--dir", "/tmp"
]
```

**注意**：禁用 RDB 后，只能通过 AOF 恢复数据。

### 方案 3：接受警告（如果系统运行正常）

如果：
- Redis 运行稳定
- 后台保存成功
- 没有内存压力
- 数据持久化正常

可以暂时接受警告，继续监控。

## 部署步骤

1. **应用 Terraform 更改**：
```bash
cd infrastructure
terraform plan  # 查看更改
terraform apply  # 应用更改
```

2. **验证修复**：
```bash
# 查看 Redis 日志
aws logs tail /ecs/nexus-ai-redis-prod --follow --region us-west-2

# 检查 Redis 配置
aws ecs execute-command \
  --cluster nexus-ai-cluster-prod \
  --task <task-id> \
  --container redis \
  --command "redis-cli CONFIG GET maxmemory" \
  --interactive
```

3. **监控指标**：
   - 检查 CloudWatch 日志中是否还有警告
   - 监控 Redis 内存使用情况
   - 确认后台保存仍然成功

## 验证命令

### 检查 Redis 配置
```bash
# 连接到 Redis 容器
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET maxmemory-policy
redis-cli INFO memory
```

### 检查内存使用
```bash
redis-cli INFO memory | grep -E "(used_memory_human|maxmemory_human|mem_fragmentation_ratio)"
```

### 测试持久化
```bash
# 设置测试数据
redis-cli SET test_key "test_value"

# 触发保存
redis-cli BGSAVE

# 检查保存状态
redis-cli LASTSAVE
```

## 监控建议

1. **CloudWatch 指标**：
   - `MemoryUtilization`：监控容器内存使用
   - `CPUUtilization`：监控 CPU 使用

2. **Redis 指标**：
   - `used_memory`：Redis 实际使用内存
   - `maxmemory`：Redis 最大内存限制
   - `mem_fragmentation_ratio`：内存碎片率

3. **告警设置**：
   - 内存使用率 > 90%
   - 后台保存失败
   - Redis 连接失败

## 相关资源

- [Redis 内存优化](https://redis.io/docs/management/optimization/memory-optimization/)
- [ECS Fargate 限制](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)
- [Redis 持久化](https://redis.io/docs/management/persistence/)

## 更新历史

- 2025-12-01：添加 `--maxmemory` 参数修复内存过度提交警告

