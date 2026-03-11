# .devcontainer/Dockerfile
# 基础镜像：选通用的开发基础镜像
FROM mcr.microsoft.com/devcontainers/python:dev-3.12-bookworm

# 安装开发环境通用工具（所有开发者都需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    curl \
    nodejs \
    npm \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# 安装Python开发依赖（后端开发专属）
RUN pip install --no-cache-dir pytest debugpy black

# 配置环境变量（开发容器专属）
ENV EDITOR=vim

# 设置工作目录（挂载项目代码）
WORKDIR /workspace
