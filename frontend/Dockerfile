# Frontend Dockerfile (适配Electron+Vue桌面应用)
# Context: Project Root
FROM node:18-alpine

ENV PORT=3000
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1
EXPOSE 3000

WORKDIR /app/frontend

# 2. 安装Electron依赖（alpine镜像必需）
# electron-builder需要libc6-compat、python等构建工具
RUN apk add --no-cache curl git libc6-compat python3 make g++

# 3. 安装依赖（区分环境）
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then \
        if [ "$BUILD_ENV" = "prod" ]; then npm ci --omit=dev; else npm ci; fi; \
    else \
        npm install; \
    fi

# 4. 复制源码
COPY frontend/ .

# 5. 构建逻辑（适配Electron）
# 开发环境：无需提前构建，运行时Vite实时编译
# 生产环境：执行完整构建（生成Electron应用包）
RUN if [ "$BUILD_ENV" = "prod" ]; then \
        npm run build; \
    fi

# 6. 启动命令（适配Electron）
CMD if [ "$BUILD_ENV" = "prod" ]; then \
        # 生产环境：运行Electron打包后的应用（或主进程）
        # 注意：Electron桌面应用通常不在Docker内运行（Docker是容器，Electron是桌面）
        # 这里仅演示逻辑，实际生产环境一般是构建出安装包后导出，而非运行
        electron .; \
    else \
        # 开发环境：启动Vite+Electron开发模式（需调整package.json的dev脚本）
        npm run dev -- --host 0.0.0.0 --port ${PORT}; \
    fi
