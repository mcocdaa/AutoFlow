# ============================================
# AutoFlow 前端 Dockerfile
# 支持模式: web | build-only
# 内部端口: 8000
# ============================================

FROM node:18-alpine AS base

WORKDIR /app/frontend

# 安装基础依赖
RUN apk add --no-cache curl git libc6-compat python3 make g++

# 复制依赖文件
COPY package.json package-lock.json* ./

# ---------------- Web 模式 ----------------
FROM base AS web
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1
ENV DOCKER_WEB=true
ENV PORT=8000
EXPOSE 8000

RUN npm ci
COPY . .

CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port 8000"]

# ---------------- Build-Only 模式 ----------------
FROM base AS build-only
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1
ENV DOCKER_WEB=true

RUN npm ci
COPY . .

RUN npm run build

# 输出到 /app/dist
VOLUME ["/app/dist"]
CMD ["cp", "-r", "dist", "/app/dist"]
