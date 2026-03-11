# Backend Dockerfile
# Context: Project Root
FROM python:3.10-slim

ENV PORT=8000

WORKDIR /app/backend

# 1. 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装Poetry
RUN pip install poetry

# 3. 安装Python依赖（根据环境区分）
COPY backend/pyproject.toml backend/poetry.lock* ./

# 配置Poetry不创建虚拟环境（Docker容器内无需额外虚拟环境）
RUN poetry config virtualenvs.create false

# 生产环境：仅安装主依赖；开发环境：安装主依赖+开发依赖
RUN if [ "$BUILD_ENV" = "prod" ]; then \
        poetry install --only main --no-interaction --no-ansi --no-root; \
    else \
        poetry install --no-interaction --no-ansi --no-root; \
    fi

# 4. 复制应用代码
COPY backend/ .

# 5. 启动应用（根据环境设置不同参数）
# 开发环境：开启热重载(--reload)；生产环境：优化运行参数
CMD if [ "$BUILD_ENV" = "prod" ]; then \
        uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4; \
    else \
        uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --reload; \
    fi