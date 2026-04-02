---
title: 后端项目
description: AutoFlow 后端核心服务
keywords: [后端, backend, FastAPI, Python]
version: "1.0"
---

# AutoFlow 后端

AutoFlow 后端核心服务，基于 FastAPI + Python 3.10+。

## 📁 目录结构

```
backend/
├── app/                  # 应用核心代码
│   ├── main.py           # FastAPI 应用入口
│   ├── api/              # API 路由层
│   │   └── v1/           # API v1 版本
│   │       ├── runs.py   # 运行流 API
│   │       ├── plugins.py # 插件 API
│   │       ├── common.py # 通用 API
│   │       └── __init__.py
│   │
│   ├── core/             # 核心模块
│   │   ├── registry.py       # 注册中心
│   │   ├── plugin_manager.py # 插件管理器
│   │   ├── hook_manager.py   # 钩子管理器
│   │   ├── setting_manager.py # 配置管理器
│   │   ├── env_secrets.py    # 环境变量和密钥
│   │   ├── router_loader.py  # 路由加载器
│   │   └── __init__.py
│   │
│   ├── runtime/          # 运行时
│   │   ├── runner/       # 运行器
│   │   │   └── runner.py
│   │   ├── actions/      # 动作执行
│   │   │   └── builtins.py
│   │   ├── loaders/      # 加载器
│   │   │   └── flow_loader.py
│   │   ├── models/       # 数据模型
│   │   │   └── models.py
│   │   ├── storage/      # 存储
│   │   │   └── store.py
│   │   ├── utils/        # 工具函数
│   │   │   ├── template.py
│   │   │   ├── condition.py
│   │   │   └── output_externalizer.py
│   │   └── __init__.py
│   │
│   ├── plugin/           # 插件系统
│   │   ├── models.py     # 插件模型
│   │   └── __init__.py
│   │
│   ├── artifacts/        # 运行产物（不提交）
│   │   └── ...
│   │
│   └── __init__.py
│
├── tests/                # 测试
│   ├── test_hooks.py
│   ├── test_control_flow.py
│   ├── test_variable_resolution.py
│   ├── test_condition.py
│   ├── test_foreach.py
│   ├── test_minimal_loop.py
│   └── test_output_externalizer.py
│
├── Dockerfile            # Docker 镜像
├── docker-compose.yml    # Docker Compose 配置
├── pyproject.toml        # 项目依赖配置
├── .gitignore
└── .env                  # 环境变量（不提交）
```

## 🚀 快速开始

### 安装依赖

```bash
cd backend
pip install -e .
```

### 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001

# 使用 Docker Compose
docker-compose up -d
```

### 访问 API

- API 文档: http://localhost:3001/docs
- ReDoc: http://localhost:3001/redoc

## 📋 核心模块说明

### API 层 (api/)

REST API 接口，分为 v1 版本。

### 核心层 (core/)

- **registry**: 动作、触发器、校验器的注册中心
- **plugin_manager**: 插件加载和管理
- **hook_manager**: 钩子函数管理
- **setting_manager**: 配置管理
- **env_secrets**: 环境变量和密钥管理
- **router_loader**: 自动加载 API 路由

### 运行时 (runtime/)

- **runner**: Flow 运行器，负责执行整个流程
- **actions**: 内置动作实现
- **loaders**: Flow 配置加载器
- **models**: 数据模型定义
- **storage**: 运行时状态存储
- **utils**: 工具函数（模板渲染、条件判断、输出处理等）

### 插件系统 (plugin/)

插件模型定义和插件接口。

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 🔧 配置

通过环境变量或 `.env` 文件配置：

```env
# 服务配置
HOST=0.0.0.0
PORT=3001

# 数据库配置
DATABASE_URL=sqlite:///./autoflow.db

# 插件目录
AUTOFLOW_PLUGIN_DIRS=../plugins
```
