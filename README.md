# AutoFlow

**AutoFlow** 是一款多端适配、所见即所得（WYSIWYG）、高可扩展的重复性劳动自动化（RPA）框架。

它旨在帮助用户通过简单的可视化录制与编排，生成跨平台（Windows/macOS/Android/iOS）的自动化执行脚本，解放双手，提升效率。

## 🚀 核心特性

*   **所见即所得**：支持桌面端与移动端的操作录制，无需编写代码即可生成自动化流程。
*   **多端适配**：一次配置，多端执行。支持 Windows/macOS 桌面应用及 Android/iOS 移动应用。
*   **双模式执行**：
    *   **当前窗口模式**：独占设备控制权，适合调试与可视化执行。
    *   **后端无头模式**：后台静默执行，不干扰用户正常工作。
*   **高可扩展性**：基于插件化架构设计，支持自定义动作、设备适配及第三方服务集成。
*   **企业级管理**：内置任务调度、日志审计、权限管理及容错保障机制。

## 📂 项目结构

本项目采用 Monorepo（单体仓库）结构，统一管理前后端与插件代码：

```
AutoFlow/
├── backend/               # 🐍 后端核心 (FastAPI + Python 3.10+)
│   ├── app/               # 业务逻辑与 API
│   └── tests/             # 单元测试
├── frontend/              # 🖥️ 桌面客户端 (Electron + Vue3 + TypeScript)
│   ├── electron/          # Electron 主进程
│   └── src/               # Vue3 渲染进程
├── mobile/                # 📱 移动端 (UniApp)
├── plugins/               # 🔌 插件系统 (标准插件示例与文档)
├── docs/                  # 📚 项目文档
└── docker-compose.yml     # 🐳 基础服务编排 (MySQL, Redis, InfluxDB, MinIO)
```

## 🛠️ 快速开始

### 前置要求

*   **Python**: 3.10+
*   **Node.js**: 16+
*   **Docker**: (可选，用于快速启动数据库等依赖)

### 1. 启动基础服务

使用 Docker Compose 一键启动 MySQL, Redis, InfluxDB 和 MinIO：

```bash
docker-compose up -d
```

### 2. 运行后端 (Backend)

```bash
cd backend

# 安装依赖
pip install -e .

# 启动 API 服务
uvicorn app.main:app --reload
```
后端服务将运行在: `http://localhost:8000`

### 3. 运行桌面端 (Frontend)

```bash
cd frontend

# 安装依赖
npm install

# 启动开发模式 (同时启动 Vue 和 Electron)
npm run dev
```

## 📝 开发指南

*   **插件开发**: 请参考 [plugins/README.md](plugins/README.md)
*   **架构文档**: 详见 [docs/architecture/README.md](docs/architecture/README.md)

## 📄 License

[LICENSE](LICENSE)
