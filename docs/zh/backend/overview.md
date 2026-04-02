# 后端总览

后端主要承载框架运行时能力：任务/执行记录管理、调度入口、插件发现与配置管理、产物索引等。

## 建议边界

- 对外 API：触发执行、查询状态、查看日志与产物
- 调度：定时/事件触发的统一入口（与 Runner 组合）
- 存储：执行记录、产物索引、Secrets 元信息（不存明文）

相关约定：

- API 约定：[`api-conventions.md`](api-conventions.md)
- 可观测性：[`../modules/observability.md`](../modules/observability.md)
