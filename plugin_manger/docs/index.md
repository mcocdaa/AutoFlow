---
title: Flow Plugin Runtime 文档索引
version: 1.0
keywords: [plugin, runtime, protocol, integration, index]
description: 独立插件仓库文档入口
---

# 文档索引

## 总体设计

- [architecture.md](architecture.md)：设计目标、分层边界、Python 包边界及 Cordis 语义映射。

## 核心协议

- [protocol/index.md](protocol/index.md)：`flow-plugin/v1` 核心协议索引。

## 宿主集成

- [integration/index.md](integration/index.md)：Python Host Adapter、四项目映射及参考示例。

## 阅读顺序

首次评审建议依次阅读：

1. [architecture.md](architecture.md)
2. [protocol/manifest.md](protocol/manifest.md)
3. [protocol/runtime.md](protocol/runtime.md)
4. [integration/adapters.md](integration/adapters.md)
5. [protocol/frontend.md](protocol/frontend.md)
6. [integration/example.md](integration/example.md)
7. [protocol/assurance.md](protocol/assurance.md)

已有项目接入时，再阅读 [integration/project-mapping.md](integration/project-mapping.md)。
