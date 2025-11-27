# Docker 镜像优化说明

## ✅ 已完成的优化

### 1. 后端 API Dockerfile 优化

**之前**：复制整个项目（`COPY . /app/`），包含所有文件

**现在**：只复制必要的目录：
```dockerfile
COPY api/ /app/api/
COPY nexus_utils/ /app/nexus_utils/
COPY agents/ /app/agents/
COPY tools/ /app/tools/
COPY config/ /app/config/
COPY prompts/ /app/prompts/
# Note: projects/ directory is mounted via EFS, not copied to image
```

**排除的内容**：
- ❌ `projects/` - 通过 EFS 挂载，不打包在镜像中（节省 ~3.1M，317个文件）
- ❌ `web/` - 前端代码
- ❌ `infrastructure/` - Terraform 配置
- ❌ `tests/`, `logs/`, `backup/` - 测试和日志文件
- ❌ 大的缓存文件（`embeddings_cache.json` 17MB）

### 2. 前端 Dockerfile

前端 Dockerfile 已经是多阶段构建，只打包前端文件，无需修改。

### 3. .dockerignore 优化

添加了 `projects/` 到排除列表，确保不会意外复制。

## 📊 镜像大小估算（优化后）

### 后端 API 镜像

```
基础镜像 (python:3.11-slim):     ~150MB
系统依赖 (gcc, curl, graphviz):  ~50MB
Python 依赖包:                   ~700-1000MB  (主要因素)
项目文件 (api/, nexus_utils/, etc): ~30MB
─────────────────────────────────────────
总计:                            ~930-1230MB
```

**相比之前减少**：
- 排除了 `projects/` 目录（~3.1M）
- 排除了大的缓存文件（~17M）
- 排除了测试文件和其他不必要文件（~10M）

**总计减少约 30MB**，但主要体积仍来自 Python 依赖包。

### 前端镜像

```
基础镜像 (node:18-alpine):       ~50MB
Next.js 构建产物:                ~100-150MB
─────────────────────────────────────────
总计:                            ~150-200MB
```

## 🔍 进一步优化建议

### 1. 精简 Python 依赖包（如果不需要某些功能）

如果某些功能在 API 服务中不需要，可以移除：

```txt
# 如果不需要可视化功能
# matplotlib  (~100MB)
# plotly      (~50MB)
# streamlit   (~100MB)

# 如果不需要 PDF 处理
# PyPDF2, pdfplumber, PyMuPDF  (~50MB)

# 如果不需要自然语言处理
# nltk  (~100MB+)
```

### 2. 使用多阶段构建（进一步减小镜像）

可以创建一个更小的运行时镜像：

```dockerfile
# 阶段 1: 构建依赖
FROM python:3.11-slim as builder
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段 2: 运行时
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY api/ /app/api/
COPY nexus_utils/ /app/nexus_utils/
# ... 其他目录
ENV PATH=/root/.local/bin:$PATH
```

## 📝 注意事项

1. **projects/ 目录**：现在通过 EFS 挂载访问，确保 ECS 任务定义中正确配置了 EFS 挂载点
2. **依赖包**：如果移除某些依赖包，需要确认代码中确实不使用
3. **构建时间**：优化后的构建时间应该会减少，因为复制的文件更少

## 🚀 重新构建

运行 `terraform apply` 会自动触发镜像重建：

```bash
cd infrastructure
terraform apply
```

镜像构建和推送应该会更快，因为：
1. 复制的文件更少
2. 镜像体积更小，推送更快

