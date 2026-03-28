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
├── core/                     # 核心插件
│   └── dummy/                # 示例插件
│
├── ai/                       # AI 相关插件
│   └── ai_deepseek/          # DeepSeek AI 集成
│
├── integrations/             # 第三方集成插件
│   ├── zhihu_digest/         # 知乎摘要
│   └── desktop_checkin/      # 桌面签到
│
├── tools/                    # 工具类插件
│   └── openclaw/             # OpenClaw 自动化
│
└── examples/                 # 插件开发示例
    ├── hello_world.py
    └── dummy_echo.py
```

## 🔌 插件类型

### 1. 核心插件 (core/)
提供 AutoFlow 基础功能的插件。

### 2. AI 插件 (ai/)
AI 相关的功能集成，如 LLM 调用、文本生成等。

### 3. 集成插件 (integrations/)
与第三方服务或平台的集成。

### 4. 工具插件 (tools/)
实用工具类插件，如自动化、数据处理等。

### 5. 示例 (examples/)
插件开发示例代码，供开发者参考。

## 📋 插件标准结构

一个标准的插件结构：

```
my_plugin/
├── __init__.py       # 插件元数据和导出
├── hooks.py          # 钩子函数
├── backend.py        # 后端逻辑
├── plugin.yaml       # 插件配置
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

AutoFlow 从以下位置加载插件：

1. 仓库中的 `plugins/` 目录（默认）
2. `AUTOFLOW_PLUGIN_DIRS` 环境变量中列出的额外目录（路径分隔）

目录插件必须包含 `__init__.py` 并暴露一个 `register()` 函数，该函数返回包含 `name`、`version` 和 `actions` 映射的对象。

## 📖 开发指南

参考 `docs/zh/plugin-dev-guide.md` 了解完整的插件开发指南。
