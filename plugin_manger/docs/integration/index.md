---
title: Flow Plugin Runtime 集成索引
version: 1.0
keywords: [adapter, host, mapping, example, integration]
description: Python宿主集成资料入口
---

# 宿主集成

本目录说明通用 Runtime 如何接入具体 Python 应用，不改变 `flow-plugin/v1` 核心语义。

## 文件列表

- [adapters.md](adapters.md)：Host Adapter、Registrar、Command、Event、Hook 和 FastAPI 边界。
- [project-mapping.md](project-mapping.md)：AutoFlow、KnowFlow、HarvestFlow、MeetFlow 的现有能力映射。
- [example.md](example.md)：后端插件、声明式前端和依赖动态变化的端到端示例。

核心协议见 [../protocol/index.md](../protocol/index.md)。
