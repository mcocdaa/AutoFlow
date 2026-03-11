# 可观测性（日志与产物）

框架约定 Runner 的每次执行都应具备可追踪性：能回答“跑了什么、跑到哪、为什么失败、产物在哪里”。

## 日志

- 结构化字段：`runId`、`flowName`、`stepId`、`actionType`、`status`、`durationMs`
- 日志分级：debug/info/warn/error
- 日志脱敏：对 secrets、cookie、token 等做脱敏或剔除

## 产物（Artifacts）

建议产物类型：

- 截图/录屏（桌面/移动）
- HTML/DOM 快照（网页自动化）
- HTTP 请求/响应摘要（可配置是否落全量）
- OCR/识别结果（用于复现定位）

产物应能按 `runId/stepId` 组织，并提供索引方便前端查看。

