# ============================================
# Nexus-AI API 服务镜像
# ============================================
# 基于 nexus-base 构建的 FastAPI 后端服务

# 构建阶段：使用基础镜像
FROM nexus-base:latest AS base

# 生产阶段
FROM python:3.13-slim AS production

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONPATH=/app \
    # API 服务配置
    APP_NAME="Nexus-AI API" \
    APP_VERSION="2.0.0" \
    # 默认端口
    PORT=8000

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd --gid 1000 nexus \
    && useradd --uid 1000 --gid nexus --shell /bin/bash --create-home nexus

# 设置工作目录
WORKDIR /app

# 从基础镜像复制已安装的 Python 包
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# 复制核心模块
COPY --from=base /app/nexus_utils ./nexus_utils
COPY --from=base /app/agents ./agents
COPY --from=base /app/tools ./tools
COPY --from=base /app/prompts ./prompts
COPY --from=base /app/config ./config
COPY --from=base /app/mcp ./mcp

# 复制 API 服务代码
COPY api/ ./api/

# 创建日志目录
RUN mkdir -p /app/logs && chown -R nexus:nexus /app

# 切换到非 root 用户
USER nexus

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "api.v2.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 标签
LABEL maintainer="Nexus-AI Team" \
      version="2.0.0" \
      description="Nexus-AI API Service" \
      service="api"
