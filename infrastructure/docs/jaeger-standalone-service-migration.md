# Jaeger 独立服务迁移完成

## 概述

已将 Jaeger 从 Sidecar 模式迁移到独立的 ECS Service 模式。所有 API 任务现在共享同一个 Jaeger 服务实例。

## 架构变化

### 之前：Sidecar 模式 ❌
```
每个 API Task (2个实例)
├── API容器
└── Jaeger容器 (每个任务独立)
```

### 现在：独立服务模式 ✅
```
API Tasks (2个实例)
└── API容器 → 指向共享的 Jaeger 服务

独立 Jaeger Service (1个实例)
└── Jaeger容器 (所有 API 共享)
```

## 已完成的修改

### 1. ✅ 添加了 Jaeger CloudWatch Log Group
**文件**: `infrastructure/05-compute-ecs.tf`
- 创建了 `/ecs/${project_name}-jaeger-${environment}` Log Group
- 日志保留 7 天

### 2. ✅ 创建了独立的 Jaeger Task Definition
**文件**: `infrastructure/05-compute-ecs.tf`
- Task Definition 名称: `${project_name}-jaeger-${environment}`
- 使用 `jaegertracing/all-in-one:latest` 镜像
- 配置了三个端口：
  - 16686: Jaeger UI
  - 4317: OTLP gRPC
  - 4318: OTLP HTTP
- 添加了健康检查

### 3. ✅ 创建了独立的 Jaeger ECS Service
**文件**: `infrastructure/07-services.tf`
- Service 名称: `${project_name}-jaeger-${environment}`
- `desired_count` 默认为 1（可配置）
- 注册到 Jaeger Target Group (端口 16686)
- 使用 Service Discovery 提供 DNS 名称

### 4. ✅ 添加了 Jaeger Service Discovery
**文件**: `infrastructure/07-services.tf`
- DNS 名称: `jaeger.${project_name}.local`
- 使用现有的 Service Discovery Namespace
- MULTIVALUE 路由策略

### 5. ✅ 更新了 API 环境变量
**文件**: `infrastructure/05-compute-ecs.tf`
- 从 `http://localhost:4318` 改为 `http://jaeger.${project_name}.local:4318`
- 所有 API 实例现在指向共享的 Jaeger 服务

### 6. ✅ 移除了 API Service 中的 Jaeger sidecar 配置
**文件**: `infrastructure/07-services.tf`
- 移除了 API Service 中的 Jaeger sidecar `load_balancer` 块
- API Service 现在只注册 API 容器到 API Target Group

### 7. ✅ 添加了 Jaeger 配置变量
**文件**: `infrastructure/variables.tf`
- `jaeger_cpu`: Jaeger 服务的 CPU 单位（默认: 1024 = 1 vCPU）
- `jaeger_memory`: Jaeger 服务的内存（默认: 2048 MB）
- `jaeger_desired_count`: Jaeger 服务实例数量（默认: 1）
- 更新了 `enable_jaeger` 的描述

## 配置变量

在 `terraform.tfvars` 中可以配置：

```hcl
enable_jaeger        = true
jaeger_cpu          = 1024      # 1 vCPU
jaeger_memory       = 2048      # 2 GB
jaeger_desired_count = 1        # 单实例运行
```

## 部署步骤

1. **更新 Terraform 配置**
   ```bash
   cd infrastructure
   terraform init
   terraform plan
   ```

2. **应用配置**
   ```bash
   terraform apply
   ```

3. **验证部署**
   ```bash
   # 检查 Jaeger Service 状态
   aws ecs describe-services \
     --cluster ${project_name}-cluster-${environment} \
     --services ${project_name}-jaeger-${environment} \
     --region ${region}
   
   # 检查 Jaeger Task 是否运行
   aws ecs list-tasks \
     --cluster ${project_name}-cluster-${environment} \
     --service-name ${project_name}-jaeger-${environment} \
     --region ${region}
   ```

4. **访问 Jaeger UI**
   ```bash
   ALB_DNS=$(terraform output -raw alb_dns_name)
   echo "Jaeger UI: http://${ALB_DNS}/jaeger/"
   ```

## 优势

✅ **数据聚合**: 所有 API 实例的追踪数据都发送到同一个 Jaeger 实例  
✅ **资源效率**: 只需运行 1 个 Jaeger 实例，而不是每个 API 任务一个  
✅ **统一视图**: 在 Jaeger UI 中可以查看完整的、聚合的追踪数据  
✅ **更好的可扩展性**: Jaeger 服务可以独立扩展和配置  
✅ **易于维护**: Jaeger 服务独立管理，不影响 API 服务

## 注意事项

1. **Service Discovery DNS**
   - API 容器通过 `jaeger.${project_name}.local:4318` 访问 Jaeger
   - 确保 Service Discovery Namespace 已正确配置

2. **网络配置**
   - Jaeger Service 和 API Service 在同一个 VPC 和子网中
   - 使用相同的安全组，允许容器间通信

3. **健康检查**
   - Jaeger Target Group 的健康检查路径是 `/`
   - 如果健康检查失败，检查 Jaeger 容器日志

4. **从 Sidecar 模式迁移**
   - 如果您之前使用过 Sidecar 模式，需要：
     1. 移除 API Task Definition 中的 Jaeger sidecar 容器
     2. 更新 API Service 以使用新的 Task Definition
     3. 应用 Terraform 配置以创建独立的 Jaeger Service

## 故障排查

### Jaeger Service 无法启动
```bash
# 检查日志
aws logs tail /ecs/${project_name}-jaeger-${environment} --follow
```

### API 无法连接到 Jaeger
```bash
# 验证 Service Discovery DNS
aws servicediscovery list-services \
  --filters Name=NAMESPACE_ID,Values=$(terraform output -raw service_discovery_namespace_id)
```

### Target Group 没有健康的目标
```bash
# 检查 Target Group 健康状态
TG_ARN=$(terraform output -raw jaeger_target_group_arn)
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

## 相关文件

- `infrastructure/05-compute-ecs.tf` - Jaeger Task Definition 和 Log Group
- `infrastructure/07-services.tf` - Jaeger Service 和 Service Discovery
- `infrastructure/variables.tf` - Jaeger 配置变量
- `infrastructure/06-loadbalancer.tf` - Jaeger Target Group 和路由规则

