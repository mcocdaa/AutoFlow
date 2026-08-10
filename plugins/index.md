---
title: 插件系统
description: AutoFlow 插件系统文档
keywords: [插件, plugin, 系统, 扩展]
version: "1.0"
---

# AutoFlow 插件系统

本目录包含 AutoFlow 的所有插件。插件是扩展核心引擎功能的 Python 模块。

## 📁 目录结构

```
plugins/
├── plugins.yaml              # 插件注册表（启用/禁用控制）
├── index.md                  # 本文件
│
├── dummy/                    # 示例插件
├── ai_deepseek/              # DeepSeek AI 集成
├── zhihu_digest/             # 知乎摘要
├── desktop_checkin/          # 桌面签到
├── openclaw/                 # OpenClaw 自动化 (含 openclaw_plugin 子模块)
│
└── examples/                 # 插件开发示例
    ├── hello_world.py
    └── dummy_echo.py
```

## 📋 插件标准结构

一个标准的插件结构：

```
my_plugin/
├── __init__.py       # 包入口（导出 register）
├── hooks.py          # register(registry) 注册函数（推荐放这里）
├── backend.py        # 后端逻辑实现
├── plugin.yaml       # 插件元信息与配置 schema
├── config.yaml       # 用户配置
├── tests/            # 测试目录
│   └── test_my_plugin.py
└── README.md         # 插件文档
```

## ⚙️ 插件注册表

在 `plugins.yaml` 中控制插件的启用状态：

```yaml
plugins:
  dummy:
    enabled: true
  ai_deepseek:
    enabled: true
  # ...
```

## 🚀 插件加载

AutoFlow 通过 `backend/app/runtime/plugin_loader.py` 统一加载插件：

1. 读取 `plugins/plugins.yaml` 中启用的插件
2. 导入对应包（要求包含 `__init__.py`）
3. 调用包暴露的 `register(registry)` 函数完成注册

插件约定（**唯一**注册入口）：

```python
from app.core.registry import Registry

def register(registry: Registry) -> None:
    registry.register_plugin(name="my-plugin", version="0.1.0")
    registry.register_action("my.action", handler)
    registry.register_check("my.check", handler)
```

单个插件加载失败不影响其他插件，错误会记录到 Registry 的 `list_plugin_errors()`。

## 📖 开发指南

参考 `docs/zh/plugin-dev-guide.md` 了解完整的插件开发指南。
