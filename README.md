# AutoFlow

> 面向 Agent 团队的确定性自动化执行引擎（Trigger → Action → Check）。

[![Family: *Flow](https://img.shields.io/badge/family-*Flow-8A2BE2.svg)](https://github.com/mcocdaa)
[![CI](https://github.com/mcocdaa/AutoFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/mcocdaa/AutoFlow/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mcocdaa/AutoFlow?display_name=tag&sort=semver)](https://github.com/mcocdaa/AutoFlow/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)

**AutoFlow** 是面向 Agent 团队的自动化（RPA）执行引擎——**Agent 的确定性执行层**：AI 负责提议，引擎负责可验证、可回放、可审计地执行。用统一的流程描述（Flow）把触发（Trigger）→ 执行（Action）→ 校验（Check）串起来，并通过插件化机制接入具体业务。

- **可观测执行**：步骤 / 检查 / 迭代 / 产物 / Hooks 全量记录，大输出自动外置为产物
- **单步调试**：创建调试会话，单步 / 继续（到断点）/ 停止；会话落盘，刷新可恢复
- **运行回放**：执行请求随运行落盘，一键重放生成新运行，历史即回归样本
- **Agent 接入（MCP）**：`/mcp` 暴露 Flow 工具（发现 / 执行 / 查询 / 回放 / 产物），Claude Code、Cursor 等可直接调用
- **OpenClaw 双向调用**：Flow 驱动 Agent、Agent 触达 AutoFlow（反向 Agent-step 在路线图中）

前端、后端、API 文档打包在**同一个镜像**中，部署一条命令即可。

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone --recurse-submodules https://github.com/mcocdaa/AutoFlow.git
cd AutoFlow

cp .env.example .env
vim .env                      # 可选：填入 DEEPSEEK_API_KEY / ZHIHU_COOKIE 等

docker compose up -d --build  # 或 bash scripts/start.sh
```

打开 <http://localhost:3001> —— 前端页面、REST API、Swagger（`/docs`）同端口。

使用已发布镜像（免本地构建）：

```bash
docker compose pull && docker compose up -d
```

停止：`bash scripts/stop.sh`

### 方式二：docker run 单容器

```bash
cp .env.example .env && vim .env

docker run -d --name autoflow -p 3001:3000 --env-file .env \
  ghcr.io/mcocdaa/autoflow:latest
```

从源码构建的等价方式：

```bash
docker build -f backend/Dockerfile -t autoflow .
docker run -d --name autoflow -p 3001:3000 --env-file .env \
  -v "$PWD/plugins:/app/plugins:ro" autoflow
```

### 方式三：本地开发（不经 Docker）

```bash
bash scripts/start.sh local          # 后端 3001 + 前端 5180，Ctrl+C 退出
bash scripts/start.sh local backend  # 仅后端
bash scripts/start.sh local frontend # 仅前端（代理到 3001）
```

桌面端（Electron）：

```bash
cd frontend
npm install
npm run dev
```

## ⚙️ 配置

所有配置集中在根目录 `.env`（由 `.env.example` 复制），关键项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BACKEND_EXTERNAL_PORT` | `3001` | 宿主机访问端口（容器内固定 3000） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `CORS_ORIGINS` | `*` | 允许的来源，逗号分隔 |
| `VITE_API_PROXY_URL` | `http://localhost:3001` | 本地前端代理目标 |
| `DEEPSEEK_API_KEY` | 空 | AI 总结插件密钥（留空则不可用） |
| `ZHIHU_COOKIE` | 空 | 知乎抓取 Cookie |
| `KNOWFLOW_BASE_URL` | 空 | KnowFlow 服务地址 |
| `MCP_ENABLED` | `true` | 是否挂载 `/mcp`（MCP Server） |
| `MCP_TOKEN` | 空 | `/mcp` 的 Bearer token，留空不鉴权 |
| `AUTOFLOW_AI_DRY_RUN` 等 | 空 | 插件空跑开关（`1/true/on`） |

## 🧪 运行与测试

```bash
# 执行一个示例 Flow
curl -s http://localhost:3001/api/v1/runs/execute \
  -H 'Content-Type: application/json' \
  --data "$(jq -n --rawfile f docs/examples/engine/01_basic_actions.flow.yaml '{flow_yaml:$f}')"

# 单元测试（152 项）
backend/.venv/bin/python -m pytest -q

# API 回归（69 项，需后端运行在 3001）
./tools/test/feature-checks/run-checks.sh
```

## 🧩 核心概念

- **Flow（流程）**：由一系列 Step 组成，每个 Step 至少包含 Action，可选 Check
- **Trigger（触发器）**：决定何时启动某个 Flow
- **Action（动作）**：执行具体操作（HTTP、抓取、点击、输入等）
- **Check（校验）**：Action 后对结果做断言，不配置则默认不校验
- **Runner（运行器）**：加载并执行 Flow，产出日志与产物
- **Plugin（插件）**：封装领域能力，注册 Action/Check/UI 配置

## 📂 项目结构

```
AutoFlow/
├── backend/            # FastAPI + 执行引擎（Dockerfile 在此，多阶段构建全栈镜像）
├── frontend/           # Electron + Vue3（Web 构建产物由后端同端口托管）
├── plugins/            # 插件：dummy / openclaw / ai-deepseek / zhihu / desktop
├── docs/examples/      # 示例 Flow（docs/examples/engine/ 覆盖全部引擎能力）
├── scripts/start.sh    # 统一启动入口
└── docker-compose.yml  # 单服务全栈编排
```

## 📚 文档

- [文档中心](docs/index.md)
- [MCP 模块](docs/zh/modules/mcp.md)
- [插件开发指南](plugin_manger/docs/index.md)
- [示例 Flow](docs/examples/index.md)
- [架构说明](docs/architecture/index.md)
- [路线图](docs/roadmap.md)

## ⚠️ 安全提示

当前版本 API 未内置认证。`/api/v1/runs/execute` 可执行任意 Flow（插件动作如 `openclaw.exec` 可执行系统命令），请勿将服务直接暴露到公网；生产部署请置于内网或网关（反向代理 + 认证）之后。

## 📄 License

[LICENSE](LICENSE)
