# Docker 部署指南（AutoFlow）

本文面向"生产者/部署者"，总结本项目的 Docker/Compose 结构、敏感变量（secrets）规范，并给出常见部署场景与验证方式。

## 1. Compose 文件结构（仓库内约定）

```
docker/
├── docker-compose.base.yml     # 服务定义层：backend/mysql/redis、secrets、volumes
├── docker-compose.backend.yml  # 端口映射层：backend (3001 -> 3000)
├── docker-compose.frontend.yml # 前端服务层：frontend (8001 -> 8000)
└── docker-compose.full.yml     # 全栈入口：include 上述三层
docker-compose.yml              # 根目录全栈入口（include docker/ 下三层）
```

分层规则：

- 基础层（base）定义服务，不含端口映射，**不可单独使用**
- 端口层（backend/frontend）定义对外端口，必须与 base 叠加
- 全栈入口（full.yml / 根 docker-compose.yml）已 include 全部三层，可直接使用

### 1.1 推荐用法：统一脚本入口

所有启动操作请通过脚本，不要手写 compose 命令：

```bash
bash scripts/start.sh dev full     # 全栈 (前端+后端+MySQL+Redis)
bash scripts/start.sh dev backend  # 仅后端
bash scripts/start.sh dev frontend # 仅前端
bash scripts/start.sh prod full    # 生产模式（与 dev 同用 docker compose）
bash scripts/stop.sh dev           # 停止
```

脚本内部实际执行的等价命令：

```bash
docker compose -p autoflow \
  -f docker/docker-compose.base.yml \
  -f docker/docker-compose.backend.yml \
  -f docker/docker-compose.frontend.yml \
  up -d --build
```

### 1.2 手动使用 compose（与脚本等价）

```bash
# 全栈
docker compose -f docker/docker-compose.full.yml -p autoflow up -d --build

# 分层（前后端）
docker compose -f docker/docker-compose.base.yml \
  -f docker/docker-compose.backend.yml \
  -f docker/docker-compose.frontend.yml up -d --build

# 仅后端
docker compose -f docker/docker-compose.base.yml \
  -f docker/docker-compose.backend.yml up -d --build
```

### 1.3 端口约定（单一事实来源）

| 服务 | 对外端口 | 容器内端口 | 配置项 |
|------|---------|-----------|--------|
| 后端 API | 3001 | 3000 | `BACKEND_EXTERNAL_PORT` / `BACKEND_INTERNAL_PORT` |
| 前端 Web | 8001 | 8000 | `FRONTEND_EXTERNAL_PORT` / `FRONTEND_INTERNAL_PORT` |
| MySQL | 不暴露（默认） | 3306 | `EXPOSE_DB_PORT` / `DB_EXTERNAL_PORT` |
| Redis | 不暴露（默认） | 6379 | `EXPOSE_REDIS_PORT` / `REDIS_EXTERNAL_PORT` |

所有端口在根目录 `.env`（由 `.env.example` 复制）中配置。

### 1.4 DevContainer

`.devcontainer/devcontainer.json` 使用独立的 `.devcontainer/docker-compose.yml`（`network_mode: host`，不依赖 docker/ 分层），用于写代码/跑命令的开发容器。

## 2. 敏感变量与 Docker secrets（必须遵守）

### 2.1 规则

- 所有敏感项不允许写入 `.env` 或任何明文环境变量（例如 `DB_PASSWORD=...`）。
- 统一使用 Compose secrets（文件挂载到容器内 `/run/secrets/<name>`）+ `*_FILE` 环境变量注入。

当前 Compose 已使用的敏感项：

- `DB_PASSWORD_FILE=/run/secrets/db_password`
- `SECRET_KEY_FILE=/run/secrets/secret_key`
- `MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password`

后端在启动时通过 `env_secrets.py` 将 `*_FILE` 对应的文件内容写入环境变量（仅当对应普通变量未设置时，两者同时设置会报错）。

### 2.2 secrets 文件约定

- `secrets/<name>`：运行时给 Compose secrets 用的文件
- `secrets/<name>.key`：仅用于本地查看/编辑的明文对照文件（不入库、不随产物分发）

初始化：

```bash
bash scripts/init-secrets.sh   # 生成缺失的 secrets 文件
bash scripts/check-secrets.sh  # 校验 required/optional 文件是否存在且非空
```

### 2.3 生产落地建议

- 生产环境不要携带 `secrets/*.key`。
- secrets 文件权限建议 `chmod 600 secrets/*`。
- CI 中不要提交/生成 `.key`；运行时 secrets 应来自 CI Secret/密钥系统，在部署机侧落盘为 `secrets/<name>`。

## 3. 生产部署：后端 + MySQL + Redis（Linux）

1) 拷贝仓库（或仅拷贝 `docker/`、`secrets/`、根 `.env`）

2) 准备 secrets（只放无后缀文件）：

- `secrets/mysql_root_password`
- `secrets/db_password`
- `secrets/secret_key`

3) 配置 `.env`（从 `.env.example` 复制，修改 `BACKEND_EXTERNAL_PORT` 等）

4) 启动：

```bash
bash scripts/start.sh prod backend
```

5) 运维要点

- 健康检查：后端提供 `/health`，Compose 已配置 healthcheck
- 数据持久化：MySQL/Redis 使用 volume（不要 `docker compose down -v` 误删数据）
- 反向代理：建议用 Nginx/Caddy 暴露 80/443，把后端 3001 端口隐藏在内网

### 拓扑 B：仅后端容器（外部 MySQL/Redis）

当数据库/缓存由云服务提供时：

- 通过 `.env` 覆盖 `DB_HOST/DB_PORT/DB_USER/DB_NAME`、`REDIS_HOST/REDIS_PORT`
- 密码/密钥仍然只通过 secrets 注入（`DB_PASSWORD_FILE`、`SECRET_KEY_FILE`）

## 4. 生产部署：前端 + 后端（Linux）

本仓库的前端包含 Electron 桌面端形态，通常不建议"在 Docker 里运行桌面应用"。两种常见生产形态：

### 4.1 推荐：后端容器 + Web 静态站点（Nginx/Caddy）

- 后端：用 Compose 部署（同第 3 章）
- 前端：构建为静态资源并由 Nginx/Caddy 提供
  - Web 模式构建：`docker compose -f docker/docker-compose.frontend.yml build`（`target: web`）或本地 `npm run build`
  - 反向代理配置 `/api/` 转发到后端（容器内 `autoflow-backend:3000`）

### 4.2 备选：前端也用容器跑（仅适合内网演示/调试）

```bash
bash scripts/start.sh prod full
```

## 5. 部署：Android（后端 + 前端）

### 5.1 推荐路径（生产）

- 后端：部署在 Linux 服务器（同第 3/4 章）
- Android：作为客户端（使用 Web 前端 H5/WebView）

Android 端通常只需要配置 API Base URL；任何数据库密码/应用密钥都不应下发到客户端。

### 5.2 实验路径（不推荐生产）

在 Android 上长期稳定运行 Docker/Compose 通常不可行（内核/权限/存储/网络限制）。如必须实验，请把它当作 PoC，并准备好迁回 Linux 的计划。

## 6. Git CI/CD 如何用到 Docker

### 6.1 典型流水线阶段

1) Build：构建镜像（建议 buildx 支持 amd64/arm64）
2) Push：推送到镜像仓库（GHCR/Docker Hub/私有 registry）
3) Deploy：SSH 到 Linux 执行更新

### 6.2 secrets 在 CI/CD 中怎么处理

- 不要把 `secrets/*.key` 放入仓库，也不要在 CI 里产出 `.key`。
- 推荐方式：
  - CI 里仅保存"密钥内容"作为 CI Secrets（例如 `DB_PASSWORD`、`SECRET_KEY`）
  - Deploy 阶段通过 SSH 在部署机写入 `secrets/<name>`（注意 `umask 077`，避免日志输出）
  - 或者升级为 Swarm/K8s 等更成熟的 secrets 管理

### 6.3 GitHub Actions（示例骨架）

示例仅展示结构（按你的仓库/镜像命名调整）：

```yaml
name: build-and-deploy
on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: backend
          push: true
          tags: ghcr.io/<org>/<image>:${{ github.ref_name }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/autoflow
            docker compose pull
            docker compose up -d
```

### 6.4 生产者最小 CI secrets 清单（建议）

- 镜像仓库：`REGISTRY_USER`、`REGISTRY_PASSWORD`（或使用平台内置 token）
- 部署机 SSH：`SSH_HOST`、`SSH_USER`、`SSH_KEY`
- 运行时 secrets：`DB_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`SECRET_KEY`（用于部署机落盘）

## 7. 快速上手清单（给新人/协作者）

- 最短启动（开发）：
  - `bash scripts/init-secrets.sh`
  - `cp .env.example .env`（按需修改端口）
  - `bash scripts/start.sh dev full`
- 关键文件：
  - Compose：`docker/docker-compose.{base,backend,frontend,full}.yml`、根 `docker-compose.yml`
  - 脚本：`scripts/start.sh`、`scripts/stop.sh`、`scripts/init-secrets.sh`、`scripts/check-secrets.sh`
  - 配置：`.env.example`（→ `.env`）
  - DevContainer：`.devcontainer/devcontainer.json`
- 常见问题：
  - 端口冲突（3001/8001/3306/6379）
  - secrets 文件权限导致容器读不到 `/run/secrets/*`
  - 浏览器访问 API 地址不要写容器名（应使用域名或 localhost/网关地址）

## 8. 测试与验证

本章提供"可复制执行"的验证命令，用来确认 Docker 方式能否跑通。

### 8.1 通用准备

```bash
docker version
docker compose version
bash scripts/init-secrets.sh
```

注意：

- 不要提交 `.env`；敏感项通过 secrets + `*_FILE` 注入。

### 8.2 校验 compose 配置（无需构建）

```bash
docker compose config --quiet                                  # 根全栈入口
docker compose -f docker/docker-compose.full.yml config --quiet
docker compose -f docker/docker-compose.base.yml \
  -f docker/docker-compose.backend.yml \
  -f docker/docker-compose.frontend.yml config --quiet
```

### 8.3 测试后端（Backend + MySQL + Redis）

```bash
bash scripts/start.sh dev backend
curl -fsS http://localhost:3001/health
```

预期：`/health` 返回 `{"status":"healthy"}`

清理（保留数据卷）：

```bash
bash scripts/stop.sh dev
```

### 8.4 测试前端 + 后端（全栈）

```bash
bash scripts/start.sh dev full
curl -fsS http://localhost:3001/health
curl -I http://localhost:8001 | head -n 5
```

说明：

- 前端在容器内以 Web 模式运行（`DOCKER_WEB=true`，由 frontend 层环境变量控制），避免 Electron 相关依赖导致启动失败。
- 前端容器内 vite 将 `/api` 代理到 `autoflow-backend:3000`（`VITE_API_PROXY_URL`）。

清理（保留数据卷）：

```bash
bash scripts/stop.sh dev
```

### 8.5 测试开发环境（DevContainer）

VS Code 推荐路径：

- 命令面板：`Dev Containers: Reopen in Container`

命令行验证 dev-container 能否构建/启动（用于排障）：

```bash
docker compose -f .devcontainer/docker-compose.yml config > /dev/null
docker compose -f .devcontainer/docker-compose.yml up -d --build dev-container
docker exec autoflow-dev-1 bash -lc "docker --version && docker compose --version"
```
