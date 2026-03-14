# Tasks: AutoFlow × OpenClaw 深度融合

## Phase 1: 基础集成（MVP）

### Task 1: AutoFlow 后端 - 变量传递增强
- [ ] 在 models.py 中扩展 StepSpec，支持 output_var 字段
- [ ] 在 runner.py 中实现变量模板解析（{{steps.x.output}}、{{vars.xxx}}）
- [ ] 在 runner.py 中实现 step 间数据流转（通过 runtime_vars）
- [ ] 单元测试
- **负责人**: backend_dev

### Task 2: AutoFlow 侧 OpenClaw 插件
- [ ] 创建 plugins/openclaw/ 目录
- [ ] 实现 openclaw.exec action（通过 HTTP/subprocess 执行命令）
- [ ] 实现 openclaw.knowflow_record action（调用 KnowFlow API 记录）
- [ ] 实现 openclaw.http_request action（通用 HTTP 调用）
- [ ] 注册对应 check 类型
- [ ] 单元测试
- **负责人**: backend_dev

### Task 3: OpenClaw 侧 AutoFlow 插件
- [ ] 创建插件仓库 plugin-openclaw-to-autoflow
- [ ] 实现 autoflow_run tool（执行 Flow）
- [ ] 实现 autoflow_list tool（列出 runs）
- [ ] 实现 autoflow_plugins tool（查询可用 actions）
- [ ] 内置 SKILL.md
- [ ] 安装并测试
- **负责人**: backend_dev

### Task 4: 集成测试
- [ ] 端到端测试：OpenClaw Agent 调用 autoflow_run 执行包含 openclaw action 的 Flow
- [ ] 测试变量传递
- [ ] 测试错误处理
- **负责人**: qa_ops

## Phase 2: 控制流增强

### Task 5: if/else 条件分支
- [ ] 在 models.py 中扩展 StepSpec，支持 condition 字段
- [ ] 在 runner.py 中实现条件评估（基于变量表达式）
- [ ] 单元测试
- **负责人**: backend_dev

### Task 6: for 循环
- [ ] 在 models.py 中扩展 StepSpec，支持 forEach 字段
- [ ] 在 runner.py 中实现循环执行
- [ ] 单元测试
- **负责人**: backend_dev

### Task 7: 归档
- [ ] 审查所有产出
- [ ] git commit / push
- [ ] openspec archive
- **负责人**: coord
