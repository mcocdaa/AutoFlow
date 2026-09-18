# ============================================
# DevContainer Dockerfile
# 纯开发环境，与生产无关
# ============================================

FROM mcr.microsoft.com/devcontainers/python:3.14

# 安装 Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs

# 安装开发工具
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 工具
RUN pip install poetry pre-commit

WORKDIR /workspace

CMD ["sleep", "infinity"]
