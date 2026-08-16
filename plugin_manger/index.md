---
title: Flow Plugin Runtime 规范索引
version: 1.0
keywords: [plugin, runtime, effect, dependency, flow]
description: 通用插件运行时规范索引
---

# Flow Plugin Runtime

本目录定义 AutoFlow、KnowFlow、HarvestFlow、MeetFlow 后续共同使用的插件系统。规范名称为 **Flow Plugin Runtime**，简称 **FPR**。

FPR 的规范名、Python 分发名和导入名固定如下：

| 用途 | 名称 |
| --- | --- |
| 规范名 | Flow Plugin Runtime |
| Python 分发名 | `flow-plugin-runtime` |
| Python 导入名 | `flow_plugin_runtime` |
| Manifest API | `flow-plugin/v1` |

当前目录名 `plugin_manger` 仅是本仓库中的设计落点，不进入公共 API，也不作为未来 Python 包名。

## 规范目标

FPR 把插件从“导入模块后手工 `start/stop/on_load/on_unload`”改为：

```text
插件声明 requires / provides / capabilities
              ↓
Runtime 维护动态 Context 与依赖图
              ↓
依赖满足时 activate
              ↓
activate 产生由 Runtime 托管的可逆 effects
              ↓
依赖消失、禁用、配置变化或热替换时逆序 dispose
```

插件作者只实现 `activate(ctx, config)`，不实现对称的 `deactivate()`。所有注册、订阅和外部资源都必须通过 effect 进入 Runtime 的所有权范围。

## 约束性关键词

本文使用以下关键词表达约束：

- **必须**：实现不可省略，否则不符合协议。
- **禁止**：实现不得出现该行为。
- **应当**：默认必须遵守，只有明确记录理由时才可偏离。
- **可以**：可选能力，不影响基础兼容性。

## 文件列表

- [architecture.md](architecture.md)：总体架构、包边界、上下文和扩展模型。
- [manifest.md](manifest.md)：Manifest 字段、版本、依赖和权限声明。
- [runtime.md](runtime.md)：状态机、依赖协调、effect 与 rollback 语义。
- [adapters.md](adapters.md)：Python 宿主适配器、配置、事件和管理 API。
- [frontend.md](frontend.md)：Python-only 插件的声明式前端协议。
- [example.md](example.md)：后端与前端接入的完整参考示例。
- [project-mapping.md](project-mapping.md)：四个现有项目到 FPR 的能力映射。
- [assurance.md](assurance.md)：错误、安全、可观测性和验证要求。

## 规范层级

从高到低依次为：

1. `flow-plugin/v1` Manifest 与 Runtime 语义；
2. Python SDK 公共接口；
3. Host Adapter 契约；
4. 具体项目的领域扩展点；
5. 插件自身实现。

下层不得改变上层语义。例如，HarvestFlow 可以定义 `curator` 扩展点，但不得把插件卸载重新解释为“只删除模块引用而不撤销 Hook”。

## 第一版范围

第一版只规定：

- Python 3.12+ 进程内运行时；
- 声明式 Manifest、配置和密钥引用；
- 动态服务依赖、拓扑协调和可逆 effect；
- Action、Check、Hook、Exporter、Event Subscriber 等宿主扩展点；
- 声明式 UI Descriptor 及 Vue/React Host Bridge；
- 受信任插件代码边界与可选的进程外执行扩展口。

第一版不包含：

- 浏览器执行 Python、Pyodide 或插件提供的任意 HTML；
- 任意前端 JavaScript 模块加载；
- Python 代码安全沙箱；
- 插件自有数据库迁移；
- 插件任意注入 FastAPI 路由；
- 跨机器分布式协调器的具体实现。

## 采用方式

未来可以把 FPR 独立为仓库，并以 Git submodule 引入源码；宿主仍应通过标准 Python 包安装方式使用：

```text
vendor/flow-plugin-runtime/       Git submodule
        ↓
pip/uv install -e vendor/flow-plugin-runtime
        ↓
import flow_plugin_runtime
```

Submodule 只是源码交付方式，不允许宿主通过修改 `sys.path` 或复制内部文件来依赖 FPR。
