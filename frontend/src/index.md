---
title: 前端项目结构
description: AutoFlow 前端项目结构说明
keywords: [前端, frontend, 结构, Vue]
version: "1.0"
---

# AutoFlow 前端项目结构说明

## 📁 目录结构概览

```
src/
├── App.vue                    # 主应用组件（FDS 标准布局）
├── main.ts                    # 应用入口文件
│
├── api/                       # API 接口层
│   └── index.ts              # 所有 API 请求定义
│
├── assets/                    # 静态资源
│   ├── images/               # 图片资源
│   ├── fonts/                # 字体资源
│   └── README.md             # 资源使用说明
│
├── components/                # Vue 组件
│   ├── plugins/              # 插件管理相关组件
│   │   ├── PluginCard.vue
│   │   ├── StatsCard.vue
│   │   ├── ActionsSection.vue
│   │   ├── ChecksSection.vue
│   │   └── ErrorsSection.vue
│   ├── run/                  # 运行流相关组件
│   │   ├── YamlEditor.vue
│   │   └── ResultsPanel.vue
│   └── shared/               # 跨页面复用的通用组件
│       └── README.md         # 共享组件开发规范
│
├── composables/               # 可复用组合式函数
│   ├── useClipboard.ts       # 剪贴板功能
│   └── useMobile.ts          # 移动端检测
│
├── constants/                 # 常量定义
│   ├── plugins.ts            # 插件相关常量
│   └── flow-examples.ts      # 流程示例
│
├── layouts/                   # 布局组件
│   └── README.md
│
├── router/                    # 路由配置
│   └── index.ts
│
├── stores/                    # Pinia 状态管理
│   ├── plugins.ts            # 插件状态
│   └── runs.ts               # 运行流状态
│
├── theme/                     # Flow Design System 主题
│   └── flow-design-theme.ts  # FDS v1.0 完整主题配置
│
├── types/                     # TypeScript 类型定义
│   ├── plugins.ts
│   └── runs.ts
│
├── utils/                     # 工具函数
│   ├── index.ts              # 统一导出入口
│   ├── format.ts             # 格式化工具
│   ├── storage.ts            # 本地存储工具
│   └── README.md             # 工具函数开发规范
│
└── views/                     # 页面视图
    ├── PluginsView.vue       # 插件管理页面
    └── RunFlowView.vue       # 运行流页面
```

---

## 🎯 快速上手

### 1. 添加新页面

1. 在 `views/` 目录创建新的页面组件
2. 在 `router/index.ts` 中添加路由配置
3. 在 `App.vue` 的侧边栏菜单中添加菜单项

### 2. 添加新组件

- **业务组件**：放在 `components/{业务模块}/` 目录
- **通用组件**：放在 `components/shared/` 目录

### 3. 添加新 API

在 `api/index.ts` 中添加新的 API 请求函数。

### 4. 使用 FDS 主题

所有样式都通过主题配置自动应用，无需手动编写样式。如需自定义，请使用 CSS 变量：

```css
/* 使用 FDS 设计令牌 */
color: var(--flow-color-primary);
background: var(--flow-bg-card);
border-radius: var(--flow-border-radius-lg);
```

---

## 📐 FDS 设计规范

本项目严格遵循 **Flow Design System (FDS) v1.0** 设计规范：

- **品牌色**：蓝绿渐变 `linear-gradient(135deg, #2563EB 0%, #10B981 100%)`
- **布局**：Header 64px + Sidebar 240px + Main Content
- **圆角**：6px（按钮）/ 8px（标签）/ 12px（卡片）
- **间距**：基础单位 4px，通用间距 8px/16px/24px/32px

详见 `theme/flow-design-theme.ts`。

---

## 🔧 技术栈

- **框架**：Vue 3 + TypeScript
- **组件库**：Ant Design Vue 4.x
- **状态管理**：Pinia
- **路由**：Vue Router
- **构建工具**：Vite
- **桌面端**：Electron

---

## 📝 开发规范

### 文件命名

- 组件文件：`PascalCase.vue`
- 工具函数：`camelCase.ts`
- 类型定义：`camelCase.ts`

### 代码风格

- 使用 `<script setup>` 语法
- 使用 TypeScript 类型定义
- 样式使用 `<style scoped>` 避免污染
