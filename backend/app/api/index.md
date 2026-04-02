---
title: API 路由层
description: REST API 接口层
keywords: [API, api, 路由, REST]
version: "1.0"
---

# API 路由层

本目录包含所有 REST API 接口。

## 📁 目录结构

```
api/
├── __init__.py
└── v1/               # API v1 版本
    ├── __init__.py
    ├── common.py     # 通用 API
    ├── runs.py       # 运行流 API
    └── plugins.py    # 插件 API
```

## 🔌 API 端点

### 通用 API (common.py)

- `GET /health` - 健康检查
- `GET /version` - 版本信息

### 运行流 API (runs.py)

- `POST /api/v1/runs` - 创建新的运行
- `GET /api/v1/runs/{run_id}` - 获取运行详情
- `GET /api/v1/runs` - 获取运行列表
- `POST /api/v1/runs/{run_id}/cancel` - 取消运行

### 插件 API (plugins.py)

- `GET /api/v1/plugins` - 获取插件列表
- `GET /api/v1/plugins/{plugin_id}` - 获取插件详情
- `POST /api/v1/plugins/{plugin_id}/enable` - 启用插件
- `POST /api/v1/plugins/{plugin_id}/disable` - 禁用插件

## 📋 添加新 API

1. 在 `api/v1/` 下创建新文件（如 `something.py`）
2. 创建 APIRouter 实例
3. 在 `api/v1/__init__.py` 中注册路由
4. 路由会被 `core/router_loader.py` 自动加载

示例：

```python
# api/v1/something.py
from fastapi import APIRouter

router = APIRouter(prefix="/something", tags=["something"])

@router.get("/")
async def get_something():
    return {"message": "Something"}
```

```python
# api/v1/__init__.py
from . import common, runs, plugins, something

__all__ = ["common", "runs", "plugins", "something"]
```
