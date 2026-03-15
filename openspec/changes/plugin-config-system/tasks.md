# Tasks: Plugin Configuration System

实现插件配置系统，使 AutoFlow 插件能够从 config.yaml 读取配置项，实现配置与代码解耦。

## Task 1: 修改 OpenClawPlugin.__init__，接收 config dict 参数
- [ ] 打开 `plugins/openclaw/backend.py`
- [ ] 修改 `OpenClawPlugin.__init__` 方法签名，添加 `config: dict` 参数
- [ ] 在 `__init__` 中从 config 解析 `defaults` 和 `secrets` 两个顶层配置
- [ ] 将解析后的配置存储为实例属性 `self.config_defaults` 和 `self.config_secrets`
- [ ] 添加配置读取失败的异常处理，确保读取失败时使用空字典作为默认值

## Task 2: 修改 http_request，timeout 优先从 config.defaults.http_timeout 读取
- [ ] 定位 `http_request` 方法
- [ ] 获取 config 中的 http_timeout：`config_defaults.get('http_timeout')` 或 `config_defaults.get('http', {}).get('timeout')`
- [ ] 如果配置中存在，使用配置值；否则使用硬编码默认值（如 30 秒）
- [ ] 将 timeout 参数传递给实际的 HTTP 请求调用

## Task 3: 修改 exec_command，timeout 优先从 config.defaults.exec_timeout 读取
- [ ] 定位 `exec_command` 方法
- [ ] 获取 config 中的 exec_timeout：`config_defaults.get('exec_timeout')` 或 `config_defaults.get('exec', {}).get('timeout')`
- [ ] 如果配置中存在，使用配置值；否则使用硬编码默认值（如 300 秒）
- [ ] 将 timeout 参数传递给 subprocess 调用

## Task 4: 修改 knowflow_record，base_url 优先从 config.secrets.knowflow_base_url 或环境变量 KNOWFLOW_BASE_URL 读取
- [ ] 定位 `knowflow_record` 方法
- [ ] 获取 base_url 的优先级：config_secrets.knowflow_base_url > 环境变量 KNOWFLOW_BASE_URL > 硬编码默认值
- [ ] 使用 `os.environ.get('KNOWFLOW_BASE_URL')` 读取环境变量
- [ ] 将最终确定的 base_url 用于 KnowFlow API 调用

## Task 5: 修改 plugin_loader.py，加载插件时将 config 传入 register()
- [ ] 打开插件加载器文件（查找 plugin_loader.py 或类似文件）
- [ ] 修改插件加载逻辑，在调用插件的 `register()` 或初始化方法时传入 config
- [ ] 确保 config 在加载时从 config.yaml 读取并传递给所有插件
- [ ] 测试加载多个插件时 config 传递正确

## Task 6: 更新 config.yaml，补充完整的配置项说明
- [ ] 打开 `config.yaml` 文件
- [ ] 在 plugins.openclaw 下添加详细的配置项说明注释
- [ ] 配置项应包括：
  - `defaults.http_timeout`: HTTP 请求默认超时时间（秒）
  - `defaults.exec_timeout`: 命令执行默认超时时间（秒）
  - `secrets.knowflow_base_url`: KnowFlow API 地址
- [ ] 添加环境变量覆盖说明（环境变量优先级高于配置文件）

## Task 7: 验证：运行测试确认配置读取生效
- [ ] 编写或更新单元测试，验证 config 能正确传入插件
- [ ] 测试 http_request 使用配置中的 timeout
- [ ] 测试 exec_command 使用配置中的 timeout
- [ ] 测试 knowflow_record 优先使用 config 中的 base_url，其次环境变量
- [ ] 测试配置缺失时的降级逻辑（使用硬编码默认值）
- [ ] 运行测试并确认全部通过