# ============================================
# Nexus-AI Base Image
# ============================================
# 共享的 Python 基础镜像，包含所有公共依赖
# 用于 API 和 Worker 服务

FROM python:3.13-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    curl \
    git \
    # 编译依赖（部分 Python 包需要）
    gcc \
    g++ \
    # PDF 处理依赖
    libpoppler-cpp-dev \
    poppler-utils \
    # 图像处理依赖
    libjpeg-dev \
    libpng-dev \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install uv

# 创建非 root 用户
RUN groupadd --gid 1000 nexus \
    && useradd --uid 1000 --gid nexus --shell /bin/bash --create-home nexus

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN uv pip install --system -r requirements.txt

# 复制核心模块（这些模块被 API 和 Worker 共享）
COPY nexus_utils/ ./nexus_utils/
COPY agents/ ./agents/
COPY tools/ ./tools/
COPY prompts/ ./prompts/
COPY config/ ./config/
COPY mcp/ ./mcp/

# 设置 Python 路径
ENV PYTHONPATH=/app

# 默认用户
USER nexus

# 健康检查占位（子镜像覆盖）
HEALTHCHECK NONE

# 标签
LABEL maintainer="Nexus-AI Team" \
      version="2.0.0" \
      description="Nexus-AI Base Image with Python 3.13"
