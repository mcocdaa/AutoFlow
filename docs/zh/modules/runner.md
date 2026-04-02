# Runner（执行器）

Runner 是 AutoFlow 的框架运行时核心：负责把 TriggerDoc/Flow 解析为一次可追踪的执行实例（Run），并驱动 Step 执行、校验、重试与产物收集。

## 责任边界

- 加载 TriggerDoc 与 Flow（含版本与 schema 校验）
- 生成 RunId，贯穿日志、产物与状态
- 调度 Step：执行 Action →（可选）执行 Check
- 失败处理：可重试/不可重试分类、退避、最大次数
- 产物收集：截图/页面快照/原始响应等

## 状态机（建议）

`pending` → `running` → `succeeded|failed|paused|canceled`

Step 级也应有对应状态，便于断点续跑。

## 与插件的关系

- Runner 不理解具体业务，只按 `type` 分发到注册的 Action/Check 实现。
- Runner 提供统一上下文：`triggerContext`、`flowParams`、`secrets`、`runMeta`。
