---
title: 路线图
description: 框架能力与插件落地的待办清单
keywords: [roadmap, 路线图, 计划]
version: "1.0"
---

# 路线图

按"框架能力"与"插件落地"拆分，逐步交付可用闭环。

## 0. 框架必备能力（优先级从高到低）

- **Trigger 运行时**：定时/事件/文档触发的统一调度入口；支持启停、并发限制、失败重试、幂等标识
- **Flow 规范与解析**：定义 Flow/Step/Action/Check 的数据结构与校验；提供版本号与向后兼容策略
- **Action/Check 基础库**：最小可用集合（HTTP、抓取、点击/输入、等待、截图、文本匹配等）
- **运行产物与可观测性**：结构化日志、执行记录、产物存储（截图/HTML/JSON）、任务追踪 ID
- **安全与密钥管理**：统一管理第三方 Cookie/Token/API Key；避免写入明文；权限隔离与审计
- **插件 SDK 与边界**：插件注册机制、配置 schema、权限声明、沙箱/能力限制、升级兼容策略

## 1. 插件：知乎自动总结 + 文档撰写

目标：针对某个问题，读取高质量回答与评论，沉淀可追溯的原始材料，并调用 AI API 产出总结/改写内容，最终发布到知乎。

当前进展（MVP）：

- 已提供动作：`zhihu.fetch_answer` / `ai.deepseek_summarize` / `zhihu.post_answer_draft`（发布不做结果验证）
- 示例 Flow：`docs/examples/zhihu_digest.flow.yaml`（可配合 `vars: { dry_run: true }` 先验证链路与产物落盘）
- AI Provider 已拆分为独立插件（`ai-deepseek`），密钥通过 `DEEPSEEK_API_KEY` 环境变量提供

待办：

- **触发类型设计**：`zhihu.question` + `mode=link` / `mode=cron-random`
- **数据采集与存档**：抓取回答、评论、作者、时间、赞同数等元数据；按问题维度落盘成文档
- **反爬与登录策略**：Cookie/登录态管理；速率限制；失败退避
- **AI 生成链路**：可控 Prompt/模板；多模型配置；输出格式约束（标题/要点/引用来源）
- **发布链路**：发布接口/自动化发布；草稿、预览与人工确认开关
- **合规与风控**：引用标注、敏感词检查、内容重复度检测、发布频率控制、可追责日志

## 2. 插件：桌面自动打卡

目标：按触发逻辑执行一系列桌面操作（点击、双击、拖拽、输入等），并在每步结束后按需校验结果；默认不校验。

当前进展（MVP）：

- 基础动作原语：`desktop.activate_window` / `desktop.click` / `desktop.double_click` / `desktop.drag` / `desktop.type_text` / `desktop.hotkey` / `desktop.wait` / `desktop.screenshot`
- 基础校验：`desktop.image_exists` / `desktop.window_title_contains`
- 示例 Flow：`docs/examples/desktop_checkin.flow.yaml`（可配合 `vars: { dry_run: true }` 无桌面环境验证）

待办：

- **动作原语定义**：统一接口与参数（坐标、窗口、元素定位）
- **定位与鲁棒性**：窗口匹配、图像/模板匹配、OCR 文本定位；"找不到目标"的降级策略
- **结果检查机制**：为 Step 绑定可选 Check；默认关闭
- **录制与回放闭环**：录制输出 Flow；回放实时状态；失败回溯重跑
- **环境适配**：多分辨率/DPI、主题差异、偏移校正与校准向导
- **安全与权限**：本地执行权限、敏感输入保护、日志脱敏、最小权限

## 3. 独特性方向（v1.2 起）

定位：**Agent 的确定性执行层**——AI 负责提议，引擎负责可验证、可回放、可审计地执行。按优先级排序，先形成「AI 提议 → 单步验证 → 可回放分叉 → 回归对比」闭环。

- **MCP / Agent 双向桥**：✅ 第一期已交付（`/mcp` Streamable HTTP，工具：发现/执行/查询/回放/产物，见 [MCP 模块](zh/modules/mcp.md)）；反向补齐 `openclaw.spawn_agent` 等 Agent-step 待做（差距清单见 `docs/examples/drafts/`），带结构化输出契约与 Check
- **时间旅行调试**：✅ 已交付（`POST /debug/sessions/fork` 从任意步骤分叉调试 + `GET /runs/{base}/diff/{target}` 步骤级对比，见 [Runner 模块](zh/modules/runner.md)）
- **Check-first 可验证执行**：Flow 静态 lint（未知 action/check 类型、模板引用、参数 schema）；断言覆盖率；重放旧运行并对比即"流程回归 CI"
- **录制 → Flow（桌面闭环）**：Electron preload/IPC 录制鼠标键盘 → 生成 YAML 与候选 Check，AI 命名补全（与 desktop 插件配合）
- **FPR 插件能力沙箱**：落实 `plugin_manger` 规范（能力声明、权限校验、effect 生命周期）；执行前展示该流程将访问网络/执行命令/读写文件

说明：Trigger 运行时、动作库扩充等共性能力继续按第 0 节补齐，不作为差异化卖点；可视化画布编排不在当前路线（引擎为线性步骤语义，优先只读流程图）。
