# 代码库优化重构(2026-08-10)

## 背景
插件层 hooks 样板重复、工具函数复制粘贴;后端序列化/深拷贝三处重叠、死配置残留;前端 store loading/error 样板重复;文档停留在旧 register 协议。

## 变更摘要
1. **插件**:新增 `plugins/common/`(Plugin 基类 + 6 个共享 helpers);5 个目录插件与 2 个文件示例插件迁移为 `class XxxPlugin(Plugin)` + `PLUGIN` 导出;hooks.py 全部删除;register(registry) 协议废弃(不保留兼容层)。
2. **后端**:`plugin_loader` 收敛为 PLUGIN 协议;新增 `app/runtime/utils/serialization.py`(safe_deep_copy/to_jsonable),收敛 store/runner 三处重复;`PluginItem.from_info()` 工厂;删除 setting_manager DB/Redis 死配置与 env_secrets 死代码。
3. **前端**:api 层响应拦截器统一错误提取 + 类型化接口(api/plugins.ts、api/runs.ts);新增 useAsyncState composable;stores 重构为 setup store 风格。
4. **文档**:插件开发指南重写为新 ABI;plugin-sdk 规范更新;新增 en 版指南;目录对齐;代码目录中的 index.md 全部删除。

## 约束遵循
- HTTP API 兼容;零新依赖;每阶段独立验证(全量 pytest 95 passed、vue-tsc 构建通过)。

## 详细设计
见 `docs/superpowers/specs/2026-08-10-codebase-optimization-design.md` 与 `docs/superpowers/plans/2026-08-10-phase{1,2,3,4}-*.md`。
