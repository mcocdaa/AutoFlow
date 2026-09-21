# ============================================
# AutoFlow 全栈镜像（前端静态文件 + 后端 API）
# 构建上下文为仓库根目录:
#   docker build -f backend/Dockerfile -t autoflow .
# 内部端口: 3000
# ============================================

# ---------- 构建前端静态文件 ----------
FROM node:26-alpine AS frontend-builder

WORKDIR /build/frontend
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
COPY docs/examples /build/docs/examples
RUN npm run build:web

# ---------- 运行镜像 ----------
FROM python:3.14-slim

ENV PORT=3000 \
    SERVE_STATIC_FILES=true \
    STATIC_FILES_DIR=/app/static \
    PYTHONPATH=/app/backend:/app \
    PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 3000

WORKDIR /app/backend

# curl 供 HEALTHCHECK 使用
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv (直接从官方镜像复制，极速零依赖)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 依赖层缓存: 先装依赖,后拷源码
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 源码 + 内置插件 + 前端静态文件
COPY backend/ ./
COPY plugins/ /app/plugins/
COPY flows/ /app/flows/
COPY --from=frontend-builder /build/frontend/dist /app/static

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:3000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000} --workers ${UVICORN_WORKERS:-4}"]
