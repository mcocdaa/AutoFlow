---
title: 前端总览
description: 页面能力与调试/回放现状
keywords: [前端, frontend, Vue, 调试]
version: "2.0"
---

# 前端总览

前端提供插件查看、Flow 运行、单步调试与运行历史四类页面，页面逻辑对齐后端 API 能力。

## 页面

| 路由 | 页面 | 能力 |
|---|---|---|
| `/` | 插件管理 | 已加载插件、注册的 Action/Check（搜索/点击复制）、加载错误；统计（插件/Action/Check） |
| `/run` | 运行流程 | CodeMirror YAML 编辑、示例加载、input/vars JSON 参数、模拟执行（`dry_run`）、结果面板（步骤/检查/迭代/产物/Hooks） |
| `/debug` | 单步调试 | 创建调试会话；单步/继续（到断点）/运行到底/停止；步骤状态与详情（输出/检查/迭代/产物）；断点为本地语义；`?session=<id>` 刷新恢复 |
| `/runs` | 运行历史 | 运行列表（状态/时间/耗时/步骤数）、详情抽屉、回放（重放请求生成新运行）、删除（含产物） |

## 与后端的对应

- `GET /api/v1/plugins` → 插件管理
- `POST /api/v1/runs/execute`、`GET /runs`、`GET /runs/{id}`、`DELETE /runs/{id}`、`GET /runs/{id}/artifacts/{path}`、`POST /runs/{id}/replay` → 运行流程 / 历史
- `POST /debug/sessions` 等 5 个端点 → 单步调试
- 大输出以 `__artifact__` 索引返回，前端递归识别（含 for_each 迭代与 hooks）并生成下载链接

## 交互约定

- 全站中文；图标均为 SVG（`@ant-design/icons-vue` + 内联 SVG logo/favicon）
- 浅色主题与设计令牌集中在 `src/theme/flow-design-theme.ts`；共享组件：`PageHeader`、`CodeEditor`、`FlowParamsEditor`、`ResultsPanel`
- input/vars 为 JSON 编辑器，执行前校验；错误以消息提示

## 待补齐（文档愿景）

- 录制：捕获鼠标/键盘/窗口/元素信息（Electron preload/IPC 未实现）
- 可视化编排：Step/Action/Check 图形化编辑
- 移动端（UniApp）：任务查看与状态跟踪
