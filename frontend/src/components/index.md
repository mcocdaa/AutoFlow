---
title: Components 组件目录
description: Vue 组件目录
keywords: [组件, component, Vue, 共享]
version: "1.0"
---

# Components 组件目录

本目录存放所有 Vue 组件。

## 📁 目录结构

```
components/
├── plugins/          # 插件管理相关组件
│   ├── PluginCard.vue
│   ├── StatsCard.vue
│   ├── ActionsSection.vue
│   ├── ChecksSection.vue
│   └── ErrorsSection.vue
├── run/              # 运行流相关组件
│   ├── YamlEditor.vue
│   └── ResultsPanel.vue
└── shared/           # 跨页面复用的通用组件
    └── README.md
```

## 📋 组件分类

- **业务组件**：按业务模块组织在子目录中（如 `plugins/`, `run/`）
- **通用组件**：跨页面复用的组件放在 `shared/` 目录

## 🎨 组件开发规范

参考 `shared/README.md` 了解共享组件开发规范。
