---
title: 前端总览
description: 可视化 DAG 编排画布、流程市场、调试回放与中英双语前端架构
keywords: [前端, frontend, Vue, VueFlow, 调试, i18n]
version: "2.1"
---

# 前端总览

AutoFlow 前端基于 **Vue 3.5 + Vite + Ant Design Vue 4 + VueFlow + CodeMirror 6** 构建，提供可视化 DAG 编排画布、Flow Hub 流程市场、运行流程、单步调试、运行历史、凭据保密柜与插件管理七大核心视图，并支持 **`zh-CN` / `en-US` 中英双语实时无损切换**。

## 路由与页面能力

| 路由 | 页面 | 核心能力 |
|---|---|---|
| `/canvas`（默认 `/` 重定向） | 可视化编排 (`FlowCanvasView`) | 基于 `@vue-flow/core` 的三栏式 Studio：左侧组件库（搜索与拖拽添加节点）、中间 DAG 交互画布（节点状态光效、连线依赖 `depends_on`、自动排版、执行耗时甘特图 `ExecutionTimeline`）、右侧属性面板（步骤参数/Check 断言、YAML 双向实时同步、Cron 定时触发预测、Webhook 触发网关配置） |
| `/hub` | 流程市场 (`FlowHubView`) | 精选生产级自动化工作流模板（SRE 运维自愈、智能采集研报、质量门禁、桌面 RPA），支持按分类筛选、关键词搜索、YAML 源码预览、一键安装至本地 `flows/` 或直接载入编排画布 |
| `/run` | 运行流程 (`RunFlowView`) | CodeMirror 6 YAML 编辑器、已保存流程与预设示例加载、`input` / `vars` JSON 参数配置、模拟执行（`dry_run`）、结果面板（步骤、Check 断言、循环迭代、外置产物、Hooks 与时间旅行分叉） |
| `/debug` | 单步调试 (`DebugView`) | 创建交互式调试会话；单步执行、继续到断点、运行到底、停止；查看每步输出、Check 结果、迭代与产物；本地前置断点；支持 `?session=<id>` 刷新恢复及从历史运行分叉（`forked_from`） |
| `/runs` | 运行历史 (`RunsView`) | 历史运行列表（状态、开始时间、耗时、步骤数）、详情抽屉、一键回放、删除（含产物清理）；支持从任意步骤分叉调试，以及勾选 2 条运行进行全字段差分对比（`RunDiffPanel`） |
| `/secrets` | 凭据保密柜 (`SecretsView`) | 本地 AES-256-GCM 加密凭据管理（新增、更新、删除、搜索），提供 `{{secrets.KEY}}` 模板引用复制与全链路日志/产物脱敏预览 |
| `/plugins` | 插件管理 (`PluginsView`) | 展示已加载插件、已注册 Action / Check 列表（支持搜索与点击复制类型名）、统计卡片及插件加载错误诊断 |

## 与后端 API 的对应关系

- `GET /api/v1/flows`、`POST /api/v1/flows`、`GET /api/v1/cron/predict`、`POST /api/v1/webhooks/{flow}/{token}` → 可视化编排画布 & 触发器配置
- `GET /api/v1/hub/flows`、`GET /api/v1/hub/flows/{id}/yaml`、`POST /api/v1/hub/flows/{id}/install` → 流程市场 (`FlowHubView`)
- `POST /api/v1/runs/execute`、`GET /api/v1/runs`、`GET /api/v1/runs/{id}`、`DELETE /api/v1/runs/{id}`、`GET /api/v1/runs/{id}/artifacts/{path}`、`POST /api/v1/runs/{id}/replay`、`GET /api/v1/runs/{id}/diff/{other}` → 运行流程与运行历史
- `POST /api/v1/debug/sessions`、`POST /api/v1/debug/sessions/fork` 等调试端点 → 单步调试与时间旅行分叉
- `GET /api/v1/secrets`、`POST /api/v1/secrets`、`DELETE /api/v1/secrets/{key}` → 凭据保密柜
- `GET /api/v1/plugins`、`GET /api/v1/plugins/catalog` → 插件管理与画布组件库动态加载

## 国际化与交互约定

- **中英双语 (`zh-CN` / `en-US`)**：状态持久化于 `localStorage('autoflow_lang')`，通过顶部导航栏语言切换按钮（`[data-testid="lang-toggle"]`）实时切换 UI 文案、组件库元数据、示例/已保存 Flow YAML 注释与步骤名，以及 Ant Design Vue `ConfigProvider` 语言包。
- **主题与设计令牌**：集中在 `src/theme/flow-design-theme.ts` 与 `src/theme/styles.css`；共享组件包括 `PageHeader`、`CodeEditor`、`FlowParamsEditor`、`ResultsPanel`、`RunDiffPanel`。
- **响应式布局**：支持 `1440px` 桌面宽屏与 `1024px` 分屏视口自适应。
