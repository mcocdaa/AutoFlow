---
title: Flow Plugin Runtime 保障规范
version: 1.0
keywords: [security, diagnostics, testing, error, consistency]
description: 插件安全诊断与测试规范
---

# 保障规范

本文件属于 `flow-plugin/v1` 核心协议。

## 1. 一致性不变量

任何实现都必须保持：

1. 只有 `ACTIVE` generation 的 contribution 对调用者可见；
2. ACTIVE 插件的全部必需依赖均指向可用 provider generation；
3. provider 撤销前，其 consumer 已完成 deactivation；
4. 每个已 acquire effect 最终执行且只执行一次 disposer；
5. 激活失败不遗留已发布 service 或 contribution；
6. 插件不能访问 Manifest 未声明的 service、secret 和 capability；
7. 同一 contribution ID 在同一 Registry 中至多有一个 owner；
8. 配置、代码和依赖的旧 generation 不能覆盖新 generation；
9. 业务持久数据不因插件 deactivation 自动删除；
10. Runtime snapshot 能解释每个插件为什么 ACTIVE 或 INACTIVE。

## 2. 错误模型

公共错误结构：

```json
{
  "code": "missing_dependency",
  "plugin_id": "meeting-export",
  "generation": 7,
  "phase": "reconcile",
  "retryable": false,
  "message": "Required service is unavailable",
  "detail_ref": "diag-01J..."
}
```

稳定错误码至少包括：

```text
manifest_invalid
entrypoint_invalid
incompatible_runtime
missing_dependency
ambiguous_provider
dependency_cycle
config_invalid
permission_denied
activation_failed
cleanup_failed
plugin_inactive
command_input_invalid
command_output_invalid
command_timeout
stale_generation
```

面向普通用户的响应不得包含 Python traceback、文件系统路径、secret、配置值或第三方原始错误。管理员诊断可以包含经过脱敏的 exception class 和 `detail_ref`。

## 3. Runtime Snapshot

每个插件诊断至少包含：

```json
{
  "plugin_id": "meeting-export",
  "version": "1.2.0",
  "protocol": "flow-plugin/v1",
  "compatibility": "native",
  "desired_enabled": true,
  "state": "ACTIVE",
  "reason": null,
  "generation": 7,
  "config_epoch": 12,
  "required_services": [],
  "provided_services": [],
  "contributions": [],
  "effect_labels": [],
  "last_transition_at": "...",
  "last_error": null
}
```

effect 只暴露 label 和状态，不暴露连接对象、handler repr 或闭包内容。

## 4. Reconcile 日志

每轮 reconcile 生成唯一 `reconcile_id`，记录：

- 触发 mutation 类型和 epoch；
- snapshot 版本；
- 计划 deactivate/activate 的插件顺序；
- 每个状态转换耗时；
- acquire/dispose 的 effect label；
- cleanup error 数量；
- 最终 Runtime epoch。

日志使用结构化字段，禁止通过字符串拼接输出 config 或 secret。

## 5. 健康与就绪

Liveness 只表示进程存活。Readiness 至少检查：

- Runtime 初次 reconcile 已完成；
- 必需 Host Adapter ACTIVE；
- 没有阻止核心功能的 `FAILED/CLEANUP_FAILED`；
- StateStore 可读；
- 如果 Host 要求，MutationBus 已连接。

可选插件失败默认不使整个 Host unready，但必须进入 diagnostics。核心插件列表由 Host policy 明确配置。

## 6. 信任与隔离

进程内 Python 插件是受信任代码。FPR 能控制通过 SDK 产生的注册与资源，但不能阻止恶意插件：

- 导入 `os` 读文件；
- 直接建立网络连接；
- 修改进程全局状态；
- 阻塞 event loop；
- 访问同进程内存。

因此：

- 生产插件目录应只读；
- 只允许管理员安装经过审核的包；
- Web UI 禁止上传或安装代码；
- Manifest permission 只代表受控 Adapter 能力；
- 不得把它描述为 sandbox。

不可信插件需要独立进程/容器、IPC schema、资源限制和身份隔离，这属于未来 Execution Adapter。

## 7. 文件与网络

文件能力必须使用 Host 提供的 scope，例如 `artifacts`、`plugin-data`，而不是任意路径。Adapter 解析后必须验证目标仍位于允许根目录，防止路径穿越和符号链接逃逸。

网络 Adapter 使用 origin allowlist、超时、响应大小上限和脱敏日志。`external_network: true` 之类的布尔声明不足以授权所有网络；必须列出允许 origin。

## 8. Secrets

- Secret 与普通配置分库存储或至少分字段加密；
- 插件只能按声明 key 获取；
- Runtime Context 不提供“列出全部 secret”；
- UI 和 diagnostics 只显示 `configured: true/false`；
- exception、HTTP header、handler result 和 effect metadata 都经过脱敏；
- secret 更新产生新 config epoch 并触发 generation reload。

## 9. Invocation 安全

每次 Command、Action、Exporter 或 Event 调用都必须：

1. 校验插件当前 ACTIVE；
2. 绑定当前 generation；
3. 验证 actor 和 target 权限；
4. 校验输入 schema 和大小限制；
5. 设置 timeout/cancellation policy；
6. 校验输出 schema 和大小限制；
7. 记录 trace/invocation ID；
8. 在 generation 失效时阻止新调用。

对于正在执行的调用，Host policy 明确选择 drain 或 cancel。默认先停止接收新调用，再在有界超时内 drain。

## 10. 测试分层

### 10.1 Core 单元测试

必须覆盖：

- Manifest 严格校验；
- 必需/可选/many 依赖；
- provider 歧义和版本不兼容；
- 环检测；
- 稳定拓扑顺序；
- activate/deactivate 正常路径；
- activation 部分失败逆序 rollback；
- disposer 异常继续清理；
- config/provider/code generation 更新；
- stale async completion；
- FAILED retry gate；
- runtime.close 全量清理。

### 10.2 属性与状态机测试

对随机 mutation 序列验证一致性不变量：

```text
install / remove / enable / disable
provide / withdraw / replace
config update / activation fail / cleanup fail
```

任意序列完成并 settle 后，不得出现 ACTIVE consumer 指向缺失 provider、重复 contribution 或未归属 effect。

### 10.3 Adapter Contract Suite

FPR 发布共享测试套件，所有 Host Adapter 必须通过：

- register 返回可重复请求且只执行一次的 disposer；
- contribution 未声明时拒绝；
- 冲突不覆盖旧 owner；
- 卸载删除 Registry 可见项；
- Invocation 再次鉴权；
- secret 和错误脱敏；
- 多进程不支持时正确返回 restart-required。

### 10.4 项目集成测试

每个项目验证至少一个原生插件：

- AutoFlow：Action/Check 激活、执行、卸载后不可见；
- KnowFlow：Key/Command/UI Descriptor 注册与清理；
- HarvestFlow：before 短路、after 链式和 provider 替换；
- MeetFlow：Action/Exporter/Outbox/UI Slot 错误隔离。

### 10.5 前端协议测试

Vue/React 使用同一组 JSON fixtures 验证：

- slot、component 和 props 校验；
- 稳定排序；
- 未知 component 隔离；
- Command 请求不信任 Descriptor actor/target；
- 核心页面在插件查询或渲染失败时仍可用。

## 11. 兼容与发布

Python 包遵循 SemVer。`flow-plugin/v1` 在包大版本内保持兼容；新增可选 Manifest 字段只能以向后兼容方式加入。

兼容测试矩阵至少包含：

```text
Runtime current × Manifest v1
Runtime current × 上一个 Adapter minor
Host current × native example plugins
Host current × 声明支持的 legacy adapters
```

发布包必须包含 Manifest JSON Schema、Python typing、Contract Suite 和变更记录。只发布代码而没有协议测试不算完成。

## 12. 完成判据

FPR 可被称为“通用插件系统”前，必须同时满足：

- 四个 Host Adapter 的最小 contract tests 通过；
- 任意顺序启停和依赖变化的状态机测试通过；
- activation 失败与 cleanup 失败均有可解释诊断；
- Python 插件无需手写 stop/unload；
- Vue 和 React 至少各有一个 Descriptor Host Bridge；
- 生产多进程限制被显式报告；
- legacy 与 native 状态清晰区分；
- 没有把 Manifest permission 宣称为 Python 沙箱。
