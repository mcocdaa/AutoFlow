# 运行可观测性与单步调试(2026-09-15)

## 背景

后端已支持 retry/for_each/condition/hooks 与运行落盘、产物下载，但两类执行逻辑对用户不可见：

1. **hooks 结果不可见**：`_run_hooks` 只写日志，成功/失败/输出/错误不进入 `RunResult`，UI 无从展示。
2. **无法单步与回放**：Flow 只能整体执行；历史运行未持久化请求，无法回放；也没有逐步检查中间输出的手段。

另：CI 中 `actions/setup-node@v4` 等 action 触发 Node 20 弃用告警，且多个 action 落后于当前大版本。

## 变更摘要

1. **Hooks 可观测**：新增 `HookResult` 模型并挂到 `RunResult.hook_results`；runner 记录每次 hook 的 phase/action/status/duration/output/error（大输出同样外置），hook 失败不改 run 状态；前端结果面板新增 Hooks 区。
2. **可暂停执行会话**：把执行逻辑从 `Runner` 下沉为 `RunSession`（整条执行 = 会话跑到底，单一实现避免语义漂移）；会话状态可 JSON 序列化。
3. **调试 API**：`POST /api/v1/debug/sessions`、`GET /debug/sessions/{id}`、`POST .../step`、`POST .../run`、`DELETE .../{id}`；会话落盘 `_sessions/<id>.json` + `fcntl` 文件锁，4 worker 下一致；对已结束会话幂等。
4. **前端调试页**：`/debug` 单步调试（单步/继续到断点/运行到底/停止、步骤状态与详情、`?session=` 刷新恢复）；断点为纯前端语义。
5. **回放**：执行请求（flow_yaml/input/vars）随运行落盘 `request.json`；新增 `POST /api/v1/runs/{run_id}/replay` 重放请求生成新运行；历史详情抽屉提供"回放"。
6. **CI action 升级**：checkout v7 / setup-python v7 / cache v6 / setup-node v7 / docker actions v4/v6/v7，消除弃用告警（独立小 PR）。

## 约束遵循

- HTTP API 向后兼容：`RunResult` 仅新增可选字段；旧 `run.json` 正常读取，旧运行回放返回 404 明确提示
- 多 worker 一致性：会话与请求均落盘 + 原子写 + 文件锁
- 零新 Python 依赖；前端不新增 UI 库，图标保持 SVG
- hooks 不改变 run 状态语义（与既有 `test_hooks.py` 行为一致）

## 详细设计

见 `docs/superpowers/specs/2026-09-15-runtime-debug-observability-design.md`；
实施计划见 `docs/superpowers/plans/2026-09-15-runtime-debug-observability.md`。
