# Docker 镜像大小分析

## 🔍 镜像变大的主要原因

### 1. Python 依赖包（主要因素）

以下 Python 包通常很大（每个可能 50-200MB+）：

- **pandas** (~200MB): 数据处理库，包含大量 C 扩展和依赖
- **matplotlib** (~100MB): 可视化库，包含字体文件和示例
- **plotly** (~50MB): 交互式可视化库
- **nltk** (~100MB+): 自然语言处理，包含数据文件（需要下载）
- **Pillow** (~50MB): 图像处理库
- **PyPDF2, pdfplumber, PyMuPDF** (~50MB): PDF 处理库
- **streamlit** (~100MB): Web 应用框架
- **networkx** (~30MB): 图分析库
- **graphviz** Python 绑定 (~20MB)

**总计**: 这些包加起来可能达到 **700MB - 1GB+**

### 2. 项目文件大小

从项目目录分析：

```
tools/          23M  (最大，包含大量工具代码)
projects/        3.1M (317个文件，主要是 JSON/YAML 配置)
agents/          2.8M (Agent 代码)
nexus_utils/     1.3M (工具包)
```

**总计**: 约 **30MB** 的项目文件

### 3. 其他因素

- **Python 基础镜像** (`python:3.11-slim`): ~150MB
- **系统依赖** (gcc, curl, graphviz): ~50MB
- **Python 标准库**: ~50MB
- **其他依赖包**: ~200MB

## 📊 镜像大小估算

```
基础镜像:            ~150MB
系统依赖:            ~50MB
Python 依赖包:       ~700-1000MB  (主要因素)
项目文件:            ~30MB
其他:                ~100MB
─────────────────────────────────
总计:                ~1-1.3GB
```

## ✅ 优化建议

### 方案 1: 优化 .dockerignore（推荐）

排除更多不必要的文件：

```dockerignore
# 排除 projects/ 目录（如果不需要在容器中）
# 注意：如果代码需要读取 projects/，则不能排除
projects/

# 排除大的测试文件
tests/html2ppt/
tests/*.pptx
tests/*.png

# 排除缓存文件
*.cache
*.json.cache
embeddings_cache.json

# 排除工具生成的代码（如果不需要）
tools/generated_tools/tooluniverse/embedding/embeddings_cache.json
```

### 方案 2: 精简依赖包（如果不需要）

如果某些功能在容器中不需要，可以移除：

```txt
# 如果不需要可视化功能
# matplotlib
# plotly
# streamlit

# 如果不需要 PDF 处理
# PyPDF2
# pdfplumber
# PyMuPDF

# 如果不需要自然语言处理
# nltk
```

### 方案 3: 使用多阶段构建

```dockerfile
# 阶段 1: 构建阶段
FROM python:3.11-slim as builder
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段 2: 运行阶段
FROM python:3.11-slim
WORKDIR /app
# 只复制已安装的包
COPY --from=builder /root/.local /root/.local
# 复制项目文件
COPY . /app/
ENV PATH=/root/.local/bin:$PATH
```

### 方案 4: 排除 projects/ 目录（如果不需要）

如果容器运行时不需要读取 `projects/` 目录（例如，项目数据存储在 DynamoDB 或 EFS），可以排除：

```dockerignore
# 排除项目数据（如果存储在外部）
projects/
```

## 🎯 推荐优化方案

### 立即优化 .dockerignore

更新 `api/.dockerignore`，添加：

```dockerignore
# 排除大的缓存文件
*.cache
embeddings_cache.json
tools/generated_tools/tooluniverse/embedding/embeddings_cache.json

# 排除测试文件
tests/html2ppt/
tests/*.pptx
tests/*.png
tests/*.ipynb

# 如果 projects/ 不需要在容器中（数据存储在 EFS/DynamoDB）
# projects/
```

### 评估依赖包

检查 `api/requirements.txt`，确认哪些包是必需的：

- ✅ **必需**: strands-agents, fastapi, uvicorn, boto3, celery, redis
- ❓ **可能不需要**: streamlit（如果只是 API 服务）
- ❓ **可能不需要**: matplotlib, plotly（如果不需要生成图表）
- ❓ **可能不需要**: nltk（如果不需要 NLP 功能）

## 📝 当前镜像大小检查

检查当前镜像大小：

```bash
# 查看 ECR 中的镜像大小
REGION=$(terraform output -raw region)
aws ecr describe-images \
  --repository-name nexus-ai-api-prod \
  --region $REGION \
  --query 'imageDetails[0].{Size:imageSizeInBytes,Pushed:imagePushedAt}' \
  --output json
```

## ⚠️ 注意事项

1. **projects/ 目录**: 如果代码需要读取 `projects/` 目录中的配置，则不能排除
2. **工具代码**: `tools/` 目录虽然大（23M），但可能被代码动态导入，需要保留
3. **依赖包**: 移除依赖包前，需要确认代码中是否使用

## 🔧 快速优化

最简单的优化是更新 `.dockerignore`，排除不必要的文件：

```bash
# 编辑 .dockerignore
vim api/.dockerignore

# 添加以下内容：
*.cache
embeddings_cache.json
tests/html2ppt/
tests/*.pptx
```

然后重新构建镜像。

