# ============================================
# AutoFlow 后端 Dockerfile
# 内部端口: 3000
# ============================================

FROM python:3.10-slim

ENV PORT=3000
EXPOSE 3000

WORKDIR /app/backend

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install poetry

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./

# 配置 Poetry
RUN poetry config virtualenvs.create false

# 安装依赖（区分环境）
ARG BUILD_ENV=dev
RUN if [ "$BUILD_ENV" = "prod" ]; then \
        poetry install --only main --no-interaction --no-ansi --no-root; \
    else \
        poetry install --no-interaction --no-ansi --no-root; \
    fi

# 复制源码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:3000/health || exit 1

# 启动
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000} --workers 4"]
