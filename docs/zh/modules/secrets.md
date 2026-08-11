# Secrets（敏感信息管理）

框架层面约定：任何凭证（Cookie/Token/API Key/密码）不得写入 Flow/TriggerDoc 明文；应统一通过 Secrets 管理，并在执行时由 Runner 注入给 Action/插件。

## 基本原则

- Flow/TriggerDoc 里只允许引用 secrets 的“键”，不允许出现密钥值
- 日志与产物默认脱敏，必要时提供白名单式放开
- Secrets 的读取应可审计（谁在何时用过哪个 key）

## 与现有实现的关系

插件凭证通过插件级 `config.yaml` 的 `secrets` 块管理：每个值是一个环境变量名，由 `plugin_loader` 在加载时解析为环境变量值注入插件构造（见插件开发指南第 6 节）。框架不读取任何全局 secret 文件。
