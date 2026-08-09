# 架构总览

本文档给出 AutoFlow 的框架级架构视图：核心概念、模块边界与关键数据流。更细的格式/约定请以规范文档为准：

- Flow：[`../specs/flow.md`](../specs/flow.md)
- TriggerDoc：[`../specs/trigger-doc.md`](../specs/trigger-doc.md)
- Plugin SDK：[`../specs/plugin-sdk.md`](../specs/plugin-sdk.md)

## 分层与边界

AutoFlow 按“框架运行时 + 多端客户端 + 插件扩展”拆分，核心目标是把自动化任务稳定地跑起来，并让领域能力以插件方式接入。

- **Trigger 层**：决定何时启动某个 Flow（定时/事件/文档触发等）。
- **Flow 层**：描述要执行的步骤序列（Step），每步包含 Action，可选 Check。
- **Runner 层**：负责加载 TriggerDoc/Flow，执行步骤，管理状态机、重试、幂等与产物。
- **Adapter/Driver 层**：对接桌面/移动等多端能力（点击、输入、抓取、OCR 等），屏蔽平台差异。
- **Plugin 层**：扩展 TriggerType/Action/Check 与配置 UI；插件只描述领域能力，不侵入框架核心。

## 核心数据流

1. 用户通过 UI 或文件生成 TriggerDoc/Flow（可版本化）。
2. Trigger 触发后，Runner 装载配置，生成一次执行实例（Run）。
3. Runner 按 Step 顺序执行 Action，并按配置决定是否执行 Check。
4. Runner 产生日志与产物（截图/HTML/JSON），并更新执行状态（成功/失败/暂停/重跑）。
5. 可选：通过后端持久化执行记录与产物索引，供前端查询与回放。

## 可靠性与可观测性（框架约定）

- **可选校验**：每步可配置 Check；未配置时默认不校验（先跑通，再加严）。
- **失败策略**：按错误类型区分“可重试/不可重试”；支持指数退避与最大次数。
- **幂等与去重**：建议以 TriggerDoc/Flow 版本 + 业务主键生成幂等键，避免重复执行。
- **产物落盘**：关键步骤建议落盘截图/页面快照/原始响应，便于复现与追责。

## 历史设计文档

以下为早期的总体设计说明书（偏“大而全”），后续将逐步把可落地的“规范/约定”拆分到 `docs/zh/specs/` 与 `docs/zh/modules/`：

- 旧版总体设计：[`../../architecture/README.md`](../../architecture/README.md)
