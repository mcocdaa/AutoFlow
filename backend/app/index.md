---
title: App 应用核心
description: 后端应用核心代码
keywords: [app, 应用, 核心, FastAPI]
version: "1.0"
---

# App 应用核心

本目录包含 AutoFlow 后端的核心应用代码。

## 📁 目录结构

```
app/
├── main.py           # FastAPI 应用入口
├── api/              # API 路由层
├── core/             # 核心模块
├── runtime/          # 运行时
├── plugin/           # 插件系统
├── artifacts/        # 运行产物
└── __init__.py
```

## 🎯 模块说明

### main.py
FastAPI 应用入口，负责：
- 创建 FastAPI 应用实例
- 配置 CORS
- 加载 API 路由
- 初始化插件系统

### api/
REST API 接口层，详见 [api/index.md](api/index.md)。

### core/
核心功能模块，详见 [core/index.md](core/index.md)。

### runtime/
Flow 运行时，详见 [runtime/index.md](runtime/index.md)。

### plugin/
插件系统，详见 [plugin/index.md](plugin/index.md)。

### artifacts/
运行产物存储目录（不提交到 Git）。
