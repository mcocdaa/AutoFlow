<div align="center">

# AutoFlow

**面向 Agent 团队的确定性 DAG 自动化编排与时间旅行单步调试引擎（Trigger → Action → Check）。**

[![Family: *Flow](https://img.shields.io/badge/family-*Flow-8A2BE2.svg)](https://github.com/mcocdaa)
[![CI](https://github.com/mcocdaa/AutoFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/mcocdaa/AutoFlow/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mcocdaa/AutoFlow?display_name=tag&sort=semver)](https://github.com/mcocdaa/AutoFlow/releases)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-blue.svg)](docker-compose.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) · [简体中文](README_CN.md)

<img src="docs/assets/demo_autoflow.gif" alt="AutoFlow Demo" width="840">

</div>

**AutoFlow** 是面向 Agent 团队的确定性自动化（RPA/DAG）执行层——**AI 负责提议与编排，引擎负责可验证、可单步调试、可回放、可审计地执行**。前端画布、REST API 与 MCP 服务打包在同一个容器镜像中，开箱即用。

## ✨ 核心特性

- **确定性 `Trigger → Action → Check` DAG 引擎**：支持声明式 YAML 流程编排、失败重试、条件分支（`when`）、循环迭代（`for_each`）以及动作后置断言（`Check`）。
- **交互式时间旅行单步调试与重放**：支持创建持久化调试会话，进行单步执行（Step）、断点续跑（Continue）、上下文观测，以及历史运行一键重放（Replay）。
- **统一的流程图 CRUD 与动态插件目录**：通过 `/api/v1/flows` 服务端存储与 `/api/v1/plugins/catalog` 动态参数 Schema，实现可视化 DAG 画布与 AI Agent 的双向实时同步。
- **原生 MCP Server（`/mcp`）与 OpenClaw 双向集成**：向 Claude Code、Cursor 及 OpenClaw 直接暴露流程发现、执行、状态查询、回放与产物读取工具。
- **AES-256-GCM 密钥保险箱（Secrets Vault）**：通过 `/api/v1/secrets` 加密托管敏感凭据，在流程中以 `{{secrets.NAME}}` 安全注入，杜绝 YAML 与日志明文泄露。
- **全链路可观测性与产物外置**：完整记录步骤、校验、循环迭代与 Hooks 事件，超大输出自动外置为结构化产物（Artifacts）。

## 🚀 快速开始

### 方式一：Docker Compose（推荐 — 一条命令启动）

```bash
cp .env.example .env && docker compose up -d --build
```

浏览器打开 **<http://localhost:3001>**（Web 画布、REST API 与 Swagger `/docs` 同端口托管）。

### 方式二：预构建 GHCR 镜像

```bash
docker run -d --name autoflow -p 3001:3000 ghcr.io/mcocdaa/autoflow:latest
```

### 方式三：本地开发

```bash
bash scripts/start.sh local          # 后端 :3001 + 前端 :5180，Ctrl+C 退出
bash scripts/start.sh local backend  # 仅启动后端 (:3001)
bash scripts/start.sh local frontend # 仅启动前端 (:5180，自动代理至 :3001)
```

## 🤖 AI 与 API 调用

通过 REST API 创建并执行流程，或将 MCP 客户端直接连接至 `/mcp`：

```bash
# 1. 保存流程图至服务端（Web 画布刷新即可见并支持直接拖拽编辑）
curl -X PUT http://localhost:3001/api/v1/flows/hello-agent \
  -H "Content-Type: application/json" \
  -d '{
    "flow_yaml": "name: hello-agent\nsteps:\n  - id: greet\n    action: log\n    params:\n      message: \"Hello from AutoFlow!\"\n    check:\n      type: always_pass\n"
  }'

# 2. 触发执行 Flow（支持直接传入 flow_yaml 或读取已保存流程）
curl -X POST http://localhost:3001/api/v1/runs/execute \
  -H "Content-Type: application/json" \
  --data "$(jq -n --rawfile f flows/hello-agent.flow.yaml '{flow_yaml:$f}')"

# 3. 查询动态插件目录（获取所有已注册 Action / Check / Trigger 及其参数 Schema）
curl -s http://localhost:3001/api/v1/plugins/catalog | jq .

# 4. 原生 MCP Server 接入点（支持 Claude Code / Cursor / OpenClaw Streamable HTTP）
# 接入地址: http://localhost:3001/mcp
```

## ⚙️ 配置与文档

所有运行配置集中在根目录 `.env`（由 `.env.example` 复制生成）：

<details>
<summary>Environment Variables（环境变量说明）</summary>

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BACKEND_EXTERNAL_PORT` | `3001` | 宿主机访问端口（容器内固定为 `3000`） |
| `LOG_LEVEL` | `INFO` | 日志级别（`DEBUG`, `INFO`, `WARNING`, `ERROR`） |
| `CORS_ORIGINS` | `*` | 允许的跨域来源，多个以逗号分隔 |
| `VITE_API_PROXY_URL` | `http://localhost:3001` | 本地前端开发服务器 API 代理目标 |
| `AUTOFLOW_SECRETS_KEY` | *(自动生成)* | AES-256-GCM 密钥保险箱主密钥 |
| `DEEPSEEK_API_KEY` | *(空)* | `ai-deepseek` 总结插件 API 密钥 |
| `ZHIHU_COOKIE` | *(空)* | `zhihu` 抓取插件 Cookie |
| `KNOWFLOW_BASE_URL` | *(空)* | KnowFlow 知识库服务地址 |
| `MCP_ENABLED` | `true` | 是否挂载 `/mcp`（MCP Server） |
| `MCP_TOKEN` | *(空)* | `/mcp` 的 Bearer 鉴权 Token，留空则不鉴权 |
| `AUTOFLOW_AI_DRY_RUN` | *(空)* | 插件空跑测试开关（`1`/`true`/`on`） |

</details>

### 文档导航

- 📚 [文档中心](docs/index.md) · [架构说明](docs/architecture/index.md) · [路线图](docs/roadmap.md)
- 🔌 [MCP 模块指南](docs/zh/modules/mcp.md) · [插件开发指南](plugin_manger/docs/index.md)
- 🧪 [示例 Flow 集合](docs/examples/index.md)（`docs/examples/engine/` 覆盖全部引擎能力）

> **安全提示**：`/api/v1/runs/execute` 可执行任意已注册插件动作（如 `openclaw.exec` 系统命令）。请勿将未配置鉴权的服务直接暴露到公网；生产部署请置于内网或带认证的反向代理网关之后。

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。
