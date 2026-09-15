# ============================================
# AutoFlow 全栈镜像（前端静态文件 + 后端 API）
# 构建上下文为仓库根目录:
#   docker build -f backend/Dockerfile -t autoflow .
# 内部端口: 3000
# ============================================

# ---------- 构建前端静态文件 ----------
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
COPY docs/examples /build/docs/examples
RUN npm run build:web

# ---------- 运行镜像 ----------
FROM python:3.12-slim

ENV PORT=3000 \
    SERVE_STATIC_FILES=true \
    STATIC_FILES_DIR=/app/static \
    PYTHONPATH=/app/backend:/app
EXPOSE 3000

WORKDIR /app/backend

# curl 供 HEALTHCHECK 使用
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry (版本与 backend/poetry.lock 生成环境保持一致)
RUN pip install --no-cache-dir poetry==2.3.3

# 依赖层缓存: 先装依赖,后拷源码
COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

# 源码 + 内置插件 + 前端静态文件
COPY backend/ ./
COPY plugins/ /app/plugins/
COPY --from=frontend-builder /build/frontend/dist /app/static

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:3000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000} --workers ${UVICORN_WORKERS:-4}"]
