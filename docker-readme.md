# Docker 部署与 CI/CD 指南（AutoFlow）

本文面向“生产者/部署者”，总结本项目的 Docker/Compose 结构、敏感变量（secrets）规范，并给出常见部署场景与 CI/CD 落地方式。

## 1. Compose 文件结构（仓库内约定）

- 基础编排入口：`docker-compose.base.yml`
  - 通过 include 聚合 `backend/docker-compose.base.yml` 与 `frontend/docker-compose.base.yml`
- 开发覆写：`docker-compose.dev.yml`
  - 作为 override 文件，需要与 base 叠加使用
- DevContainer：`.devcontainer/devcontainer.json`
  - 会叠加 base + dev + `.devcontainer/docker-compose.yml`，提供一个“只用来写代码/跑命令”的开发容器

推荐用法：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d --build
```

### 1.1 开发者视角：用 VS Code 启动 Dev Container（推荐）

目标：用 VS Code 一键进入“容器化开发环境”，并让本机（浏览器/调试器）能直接访问容器内服务。

前置条件：

- 本机已安装 Docker（Linux: Docker Engine；Windows/macOS: Docker Desktop）
- VS Code 已安装扩展 Dev Containers（Microsoft）

启动步骤：

1) 用 VS Code 打开仓库根目录（AutoFlow）
2) 打开命令面板，执行：

```text
Dev Containers: Reopen in Container
```

3) VS Code 会使用 `.devcontainer/devcontainer.json` 进行启动，会叠加：

- `docker-compose.base.yml`（基础编排）
- `docker-compose.dev.yml`（开发覆写）
- `.devcontainer/docker-compose.yml`（dev-container 本体）

容器启动后建议做的第一件事（同步本地 `.key` 到运行用 secrets）：

```bash
bash ./build.sh dev
```

常用开发动作（在 VS Code 的容器终端中执行）：

- 启动/重建服务：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d --build
```

- 查看日志：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml logs -f backend
```

访问方式说明：

- Dev Container 配置了 `network_mode: host`，因此通常可以直接用宿主机 `http://localhost:8000` 访问后端、`http://localhost:3000` 访问前端（取决于你是否启动了对应服务）。

## 2. 敏感变量与 Docker secrets（必须遵守）

### 2.1 规则

- 所有敏感项不允许写入 `.env` 或任何明文环境变量（例如 `DB_PASSWORD=...`）。
- 统一使用 Compose secrets（文件挂载到容器内 `/run/secrets/<name>`）+ `*_FILE` 环境变量注入。

当前后端 Compose 已使用的敏感项（示例）：

- `DB_PASSWORD_FILE=/run/secrets/db_password`
- `SECRET_KEY_FILE=/run/secrets/secret_key`
- `MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password`

### 2.2 `.key` 双文件约定（本地可读对照）

- `secrets/<name>`：运行时真正给 Compose secrets 用的文件（生产只需要这个）
- `secrets/<name>.key`：仅用于本地查看/编辑的明文对照文件（生产产物不应包含）

同步脚本：

```bash
# 开发：从 *.key 同步生成无后缀 secrets
bash ./build.sh dev

# 生产打包/部署前：同步并清理 *.key（保证产物不携带 .key）
bash ./build.sh prod
```

### 2.3 生产落地建议

- 生产环境不要携带 `secrets/*.key`。
- secrets 文件建议权限：`chmod 600 secrets/*`，并确保部署机上该目录不被备份到不可信位置。
- CI 中不要提交/生成 `.key`；运行时 secrets 应来自 CI Secret/密钥系统，在部署机侧落盘为 `secrets/<name>`。

## 3. 生产部署：Linux（仅后端）

目标：在 Linux 上部署 API（通常也包含 MySQL/Redis，或对接外部 MySQL/Redis）。

### 3.1 拓扑 A：后端 + MySQL + Redis（最简单）

1) 准备目录（示例）

- 放置 compose 文件（可直接使用仓库内文件，或拷贝到部署目录）
- 准备 secrets（只放无后缀文件）

2) 需要的 secrets（示例清单）

- `secrets/mysql_root_password`
- `secrets/db_password`
- `secrets/secret_key`

3) 启动（示例）

```bash
docker compose --env-file .env -f backend/docker-compose.base.yml up -d --build
```

4) 运维要点

- 健康检查：后端提供 `/health`。
- 数据持久化：MySQL/Redis 使用 volume（确保不要 `docker compose down -v` 误删数据）。
- 反向代理：建议用 Nginx/Caddy 暴露 80/443，把后端 8000 端口隐藏在内网。

### 3.2 拓扑 B：仅后端容器（外部 MySQL/Redis）

当数据库/缓存由云服务提供时：

- `DB_HOST/DB_PORT/DB_USER/DB_NAME`、`REDIS_HOST/REDIS_PORT` 通过环境变量覆盖
- 密码/密钥仍然只通过 secrets 注入（`DB_PASSWORD_FILE`、`SECRET_KEY_FILE`）

建议做法：在服务器准备一个 override 文件（不必提交到仓库），只写非敏感项覆盖与端口暴露策略。

## 4. 生产部署：Linux（前端 + 后端）

本仓库的前端包含 Electron 桌面端形态，通常不建议“在 Docker 里运行桌面应用”。因此这里按两种更常见的生产形态说明：

### 4.1 推荐：后端容器 + Web 静态站点（Nginx/Caddy）

- 后端：用 Docker/Compose 部署（同第 3 章）
- 前端：构建为静态资源并由 Nginx/Caddy 提供
  - 运行时只需要 `VITE_API_URL` 指向后端域名（例如 `https://api.example.com`）

### 4.2 备选：前端也用容器跑（仅适合内网演示/调试）

适用于快速演示（不作为长期生产建议）：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d --build
```

## 5. 部署：Android（后端 + 前端）

### 5.1 推荐路径（生产）

- 后端：部署在 Linux 服务器（同第 3/4 章）
- Android：作为客户端
  - `mobile/`（UniApp）打包为 Android App，或
  - 使用 Web 前端（H5/WebView）

Android 端通常只需要配置 API Base URL；任何数据库密码/应用密钥都不应下发到客户端。

### 5.2 实验路径（不推荐生产）

在 Android 上长期稳定运行 Docker/Compose 通常不可行或成本极高（内核/权限/存储/网络限制）。如必须实验，请把它当作 PoC，并准备好迁回 Linux 的计划。

## 6. Git CI/CD 如何用到 Docker

目标：每次发布自动化产出镜像 → 推送到镜像仓库 → 服务器自动更新。

### 6.1 典型流水线阶段

1) Build：构建镜像（建议 buildx 支持 amd64/arm64）
2) Push：推送到镜像仓库（GHCR/Docker Hub/私有 registry）
3) Deploy：SSH 到 Linux 执行更新

### 6.2 secrets 在 CI/CD 中怎么处理

- 不要把 `secrets/*.key` 放入仓库，也不要在 CI 里产出 `.key`。
- 推荐方式：
  - CI 里仅保存“密钥内容”作为 CI Secrets（例如 `DB_PASSWORD`、`SECRET_KEY`）
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
          context: .
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

## 7. 快速上手清单（给新人/外包/协作者）

- 最短启动（开发）：
  - `bash ./build.sh dev`
  - `docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d --build`
- 关键文件：
  - Compose：`docker-compose.base.yml`、`docker-compose.dev.yml`、`backend/docker-compose.base.yml`
  - secrets：`tools/secrets/README.md`、`tools/secrets/sync.sh`、`build.sh`
  - DevContainer：`.devcontainer/devcontainer.json`
- 常见问题：
  - 端口冲突（8000/3306/6379/3000）
  - secrets 文件权限导致容器读不到 `/run/secrets/*`
  - 浏览器访问 API 地址不要写容器名（应使用域名或 localhost/网关地址）

## 8. 测试与验证（后端/前端/开发）

本章提供“可复制执行”的验证命令，用来确认 Docker 方式能否跑通。

### 8.1 通用准备

```bash
docker version
docker compose version
bash ./build.sh dev
```

注意：

- 不要提交/依赖 `backend/.env` 这类明文敏感配置文件；本仓库后端敏感项通过 secrets + `*_FILE` 注入。
- `backend/docker-compose.base.yml` 单独使用时，建议显式指定 `--env-file .env`（否则 `CONTAINER_PREFIX` 等变量可能取不到）。

### 8.2 测试后端（Backend + MySQL + Redis）

```bash
docker compose --env-file .env -f backend/docker-compose.base.yml config > /dev/null
docker compose --env-file .env -f backend/docker-compose.base.yml up -d --build
curl -fsS http://localhost:8000/health
```

预期：

- `/health` 返回 `{\"status\":\"ok\"}`

清理（保留数据卷）：

```bash
docker compose --env-file .env -f backend/docker-compose.base.yml down
```

### 8.3 测试前端 + 后端（base + dev 联动）

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml config > /dev/null
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up -d --build
curl -fsS http://localhost:8000/health
curl -I http://localhost:3000 | head -n 5
```

说明：

- 由于前端默认是 Electron 桌面工程，本仓库在容器运行 Vite 时会启用 Web 模式（`DOCKER_WEB=true`），避免 Electron 相关依赖导致启动失败。

清理（保留数据卷）：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml down
```

### 8.4 测试开发环境（DevContainer）

VS Code 推荐路径：

- 命令面板：`Dev Containers: Reopen in Container`

如果需要在命令行验证 dev-container 能否构建/启动（用于排障）：

```bash
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml -f .devcontainer/docker-compose.yml config > /dev/null
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml -f .devcontainer/docker-compose.yml up -d --build dev-container
docker exec autoflow-dev-container-1 bash -lc "docker --version && docker-compose --version"
```
