# Secrets（敏感信息管理）

框架层面约定：任何凭证（Cookie/Token/API Key/密码）不得写入 Flow/TriggerDoc 明文；应统一通过 Secrets 管理，并在执行时由 Runner 注入给 Action/插件。

## 基本原则

- Flow/TriggerDoc 里只允许引用 secrets 的“键”，不允许出现密钥值
- 日志与产物默认脱敏，必要时提供白名单式放开
- Secrets 的读取应可审计（谁在何时用过哪个 key）

## 与现有实现的关系

仓库当前已存在基于 Docker secrets 的敏感变量注入实践，可作为运行时与开发环境的一种落地方式：

- `tools/secrets/README.md`
- 后端 `.env.example` 中的 `*_FILE` 约定

