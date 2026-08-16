---
title: Flow Plugin Runtime 核心协议索引
version: 1.0
keywords: [manifest, lifecycle, frontend, assurance, protocol]
description: flow-plugin-v1协议入口
---

# 核心协议

本目录是 `flow-plugin/v1` 的约束性规范。

## 文件列表

- [manifest.md](manifest.md)：插件身份、入口、依赖、能力、配置和权限。
- [runtime.md](runtime.md)：状态机、reconcile、generation、effect 和 rollback。
- [frontend.md](frontend.md)：Python-only 插件的声明式 UI Descriptor。
- [assurance.md](assurance.md)：一致性、安全、诊断和验证标准。

宿主特定的注册器和领域类型不属于本目录，见 [../integration/index.md](../integration/index.md)。
