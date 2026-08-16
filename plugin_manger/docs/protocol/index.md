---
title: Flow Plugin Runtime 核心协议索引
version: 1.0
keywords: [manifest, context, component, lifecycle, protocol]
description: flow-plugin-v1协议入口
---

# 核心协议

本目录是 `flow-plugin/v1` 的约束性规范。

## 文件列表

- [manifest.md](manifest.md)：插件身份、入口、依赖、能力、配置和权限。
- [context.md](context.md)：Context 继承、服务隔离、intercept 和空间解析。
- [components.md](components.md)：父子组件声明、独立状态和递归所有权。
- [runtime.md](runtime.md)：状态机、reconcile、generation、effect 和 rollback。
- [hot-reload.md](hot-reload.md)：代码 generation 的 prepare、切换和补偿回滚。
- [frontend.md](frontend.md)：Python-only 插件的声明式 UI Descriptor。
- [assurance.md](assurance.md)：一致性、安全、诊断和验证标准。

宿主特定的注册器和领域类型不属于本目录，见 [../integration/index.md](../integration/index.md)。
