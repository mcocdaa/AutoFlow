# AutoFlow 使用说明（OpenClaw 团队版）

## 1. AutoFlow 在 OpenClaw 中的定位

AutoFlow 适合把**多步、可预测、可复用**的操作，沉淀成一个可执行 Flow。

它不替代 Agent 的推理能力，而是把 Agent 已经想清楚、以后还会反复做的流程，固化成流程资产。

### 适合交给 AutoFlow 的场景

| 场景特征 | 说明 | 团队示例 |
|---------|------|---------|
| **步骤明确** | 每一步做什么、顺序怎样，基本确定 | 项目初始化、部署流程 |
| **重复出现** | 这套流程后面还会反复执行 | 每日构建、定期归档 |
| **需要留痕** | 希望有 run_id、步骤结果、失败位置、执行时长 | 审计日志、故障追溯 |
| **可以模板化** | 换参数就能复用，例如项目名、接口地址、文档标题 | 不同项目的初始化 |
| **多 Agent 协作** | 需要多个 Agent 按序执行，中间有状态传递 | 需求分析→开发→测试→部署 |
| **耗时较长** | 执行时间较长，需要异步执行和进度跟踪 | 大规模测试、数据迁移 |

### 不适合交给 AutoFlow 的场景

| 场景特征 | 说明 | 团队示例 |
|---------|------|---------|
| **高度开放式推理** | 需要大量创造性思考，无固定步骤 | "帮我想一个产品方向" |
| **过程不断变化** | 还没想清楚流程长什么样，边做边探索 | 技术调研、方案选型阶段 |
| **单步就能完成** | 没必要为了 1 个动作建 Flow | 查询单个接口状态 |
| **强依赖人工即时判断** | 中途必须频繁人工决策，而不是参数化判断 | 需要实时确认的设计评审 |
| **结果不可预测** | 输出高度不确定，无法定义成功标准 | 创意头脑风暴 |
| **需要复杂分支决策** | 每一步都有大量条件分支，难以用 YAML 表达 | 复杂的业务规则引擎 |

---

## 2. 哪些复杂流程适合封装为 Flow

### 场景 A：项目初始化流程
典型步骤：创建目录 → 初始化 OpenSpec → 创建基础文档 → 创建 Git 分支 → 输出初始化结果

适合原因：
- 步骤稳定
- 每个新项目都要做
- 可参数化（项目路径、项目名、分支名）

### 场景 B：API 冒烟测试流程
典型步骤：读取接口列表 → 调用接口 → 校验状态码/关键字段 → 汇总报告

适合原因：
- 测试步骤固定
- 可重复运行
- 需要明确日志与失败定位

### 场景 C：文档归档同步流程
典型步骤：读取 OpenSpec 变更 → 生成摘要 → 写入 KnowFlow / 文档库 → 记录归档结果

适合原因：
- 有稳定输入与输出
- 需要多步协同
- 适合作为规范化归档通道

### 场景 D：代码审查准备流程
典型步骤：拉取分支 → 获取 diff → 运行测试/检查 → 收集上下文 → 生成审查包

适合原因：
- 重复率高
- 可以把机械步骤前置
- Agent 后续只需要做真正的审查判断

### 场景 E：发布前检查流程
典型步骤：检查版本 → 运行 smoke test → 检查文档是否齐全 → 生成 checklist

适合原因：
- 发布前固定动作多
- 适合流程化执行和留痕

### 场景 F：Agent 技能发布流程
典型步骤：检查技能结构 → 运行安全审查 → 测试技能功能 → 打包 → 发布到仓库 → 更新索引

适合原因：
- 发布流程标准化
- 涉及多个检查点
- 失败需要精确定位

### 场景 G：定期知识库维护流程
典型步骤：扫描过期文档 → 标记待归档 → 生成维护报告 → 通知负责人

适合原因：
- 定期执行
- 步骤固定
- 需要记录维护历史

---

## 3. 判断标准：这件事该不该交给 AutoFlow？

可以用下面 6 个问题判断：

1. 这件事是不是至少有 **3 步以上**？
2. 这件事是不是 **以后还会再做**？
3. 这件事的步骤是否 **相对确定**？
4. 这件事是否需要 **执行日志、失败定位、可追溯性**？
5. 这件事是否可以通过 **换参数复用**？
6. 这件事是否需要 **跨多个工具/系统** 协调？

### 决策矩阵

| 满足条件数 | 建议方案 |
|-----------|---------|
| 0-2 条 | 直接 Agent 对话执行 |
| 3-4 条 | 考虑封装为简单 Flow |
| 5-6 条 | **强烈推荐**封装为 Flow |

### 快速决策流程图

```
开始
  │
  ▼
步骤 >= 3 且会重复做？
  │
  ├── 否 → 直接 Agent 执行
  │
  └── 是 → 步骤是否确定？
            │
            ├── 否 → 先用 Agent 探索，稳定后再封装
            │
            └── 是 → 需要日志/追溯？
                      │
                      ├── 否 → 简单脚本即可
                      │
                      └── 是 → 封装为 AutoFlow Flow ✓
```

---

## 4. Flow 模板草案

### 模板 1：项目初始化 Flow

适用于：新 Agent 技能 / OpenSpec 变更 / 前端组件项目初始化

```yaml
version: "1"
name: "project-bootstrap"
description: "新项目初始化流程 - 适用于 OpenClaw 团队"

vars:
  project_name: ""
  project_path: ""
  project_type: "skill"  # skill | openspec | frontend

defaults:
  timeoutMs: 30000
  retry:
    maxAttempts: 2
    backoffMs: 1000

steps:
  - id: "create-directory"
    name: "创建项目目录"
    action:
      type: "shell.exec"
      params:
        command: "mkdir -p {{project_path}}/{{project_name}}"
    check:
      type: "shell.exitCode"
      params:
        expected: 0

  - id: "init-git"
    name: "初始化 Git 仓库"
    action:
      type: "shell.exec"
      params:
        command: "cd {{project_path}}/{{project_name}} && git init"

  - id: "create-openspec"
    name: "初始化 OpenSpec 结构"
    action:
      type: "shell.exec"
      params:
        command: "openspec init {{project_path}}/{{project_name}} --type {{project_type}}"
    check:
      type: "text.contains"
      params:
        text: "initialized"

  - id: "create-readme"
    name: "创建 README 模板"
    action:
      type: "file.write"
      params:
        path: "{{project_path}}/{{project_name}}/README.md"
        content: |
          # {{project_name}}
          
          ## 项目说明
          
          ## 快速开始
          
          ## 目录结构
          
          ## 维护者

  - id: "verify-structure"
    name: "验证项目结构"
    action:
      type: "shell.exec"
      params:
        command: "ls -la {{project_path}}/{{project_name}}"
    check:
      type: "text.contains"
      params:
        text: "README.md"

  - id: "notify-complete"
    name: "通知初始化完成"
    action:
      type: "message.send"
      params:
        channel: "project-notifications"
        text: "✅ 项目 {{project_name}} 初始化完成"
```

---

### 模板 2：API 冒烟测试 Flow

适用于：AutoFlow 服务健康检查、技能 API 测试、后端服务验证

```yaml
version: "1"
name: "api-smoke-test"
description: "API 服务冒烟测试 - 验证核心接口可用性"

vars:
  base_url: "http://localhost:3000"
  timeout: 5000

defaults:
  timeoutMs: 10000

steps:
  - id: "health-check"
    name: "检查健康接口"
    action:
      type: "http.request"
      params:
        method: "GET"
        url: "{{base_url}}/health"
        timeout: {{timeout}}
    check:
      type: "json.path"
      params:
        path: "$.status"
        expected: "ok"

  - id: "plugins-list"
    name: "获取插件列表"
    action:
      type: "http.request"
      params:
        method: "GET"
        url: "{{base_url}}/api/v1/plugins"
    check:
      type: "json.path"
      params:
        path: "$.plugins"
        operator: "exists"

  - id: "runs-list"
    name: "检查运行记录接口"
    action:
      type: "http.request"
      params:
        method: "GET"
        url: "{{base_url}}/api/v1/runs?limit=5"
    check:
      type: "json.path"
      params:
        path: "$.runs"
        operator: "isArray"

  - id: "execute-test-flow"
    name: "执行测试 Flow"
    action:
      type: "http.request"
      params:
        method: "POST"
        url: "{{base_url}}/api/v1/runs/execute"
        json:
          flow:
            version: "1"
            name: "ping-test"
            steps:
              - id: "ping"
                action:
                  type: "http.request"
                  params:
                    method: "GET"
                    url: "{{base_url}}/health"
    check:
      type: "json.path"
      params:
        path: "$.runId"
        operator: "exists"

  - id: "generate-report"
    name: "生成测试报告"
    action:
      type: "file.write"
      params:
        path: "./smoke-test-report-{{date}}.json"
        content: |
          {
            "timestamp": "{{timestamp}}",
            "baseUrl": "{{base_url}}",
            "status": "passed",
            "tests": ["health", "plugins", "runs", "execute"]
          }
```

---

### 模板 3：OpenSpec 变更归档 Flow

适用于：将 OpenSpec 变更归档到 KnowFlow，建立变更追踪

```yaml
version: "1"
name: "spec-archive-sync"
description: "OpenSpec 变更归档到知识库"

vars:
  change_id: ""
  knowflow_url: "http://localhost:3002"
  archive_tag: "openspec"

defaults:
  timeoutMs: 60000

steps:
  - id: "fetch-change"
    name: "获取变更详情"
    action:
      type: "shell.exec"
      params:
        command: "openspec show {{change_id}} --json"
    check:
      type: "json.path"
      params:
        path: "$.id"
        operator: "exists"

  - id: "extract-summary"
    name: "提取关键信息"
    action:
      type: "json.transform"
      params:
        template: |
          {
            "title": "{{$.title}}",
            "type": "{{$.type}}",
            "status": "{{$.status}}",
            "createdAt": "{{$.createdAt}}",
            "summary": "{{$.description | truncate:200}}"
          }

  - id: "generate-archive-doc"
    name: "生成归档文档"
    action:
      type: "template.render"
      params:
        template: |
          # OpenSpec 变更归档: {{change_id}}
          
          ## 基本信息
          - **变更ID**: {{change_id}}
          - **归档时间**: {{timestamp}}
          - **状态**: {{status}}
          
          ## 摘要
          {{summary}}
          
          ## 相关链接
          - [原始变更](./openspec/changes/{{change_id}})

  - id: "create-knowflow-item"
    name: "创建知识库条目"
    action:
      type: "http.request"
      params:
        method: "POST"
        url: "{{knowflow_url}}/api/v1/items"
        headers:
          Content-Type: "application/json"
        json:
          title: "[OpenSpec] {{change_id}}"
          content: "{{steps.generate-archive-doc.output}}"
          tags: ["{{archive_tag}}", "auto-archived"]
          metadata:
            source: "openspec"
            changeId: "{{change_id}}"
    check:
      type: "json.path"
      params:
        path: "$.itemId"
        operator: "exists"

  - id: "record-archive"
    name: "记录归档结果"
    action:
      type: "file.append"
      params:
        path: "./archive-log.csv"
        content: "{{timestamp}},{{change_id}},{{steps.create-knowflow-item.output.itemId}}\n"
```

---

### 模板 4：Agent 技能安全审查 Flow

适用于：发布前对 Agent 技能进行安全检查

```yaml
version: "1"
name: "skill-security-review"
description: "Agent 技能发布前安全检查流程"

vars:
  skill_path: ""
  skill_name: ""

defaults:
  timeoutMs: 60000

steps:
  - id: "check-structure"
    name: "检查技能结构"
    action:
      type: "shell.exec"
      params:
        command: "test -f {{skill_path}}/SKILL.md && test -d {{skill_path}}/scripts"
    check:
      type: "shell.exitCode"
      params:
        expected: 0

  - id: "scan-secrets"
    name: "扫描敏感信息"
    action:
      type: "shell.exec"
      params:
        command: "grep -r -i 'password\|secret\|token\|key' {{skill_path}} --include='*.js' --include='*.ts' --include='*.py' || true"
    check:
      type: "text.doesNotContain"
      params:
        text: "hardcoded"

  - id: "check-permissions"
    name: "检查权限声明"
    action:
      type: "file.read"
      params:
        path: "{{skill_path}}/SKILL.md"
    check:
      type: "text.contains"
      params:
        text: "权限"

  - id: "run-tests"
    name: "运行技能测试"
    action:
      type: "shell.exec"
      params:
        command: "cd {{skill_path}} && npm test 2>/dev/null || echo 'No tests found'"

  - id: "generate-report"
    name: "生成审查报告"
    action:
      type: "file.write"
      params:
        path: "./security-reports/{{skill_name}}-{{date}}.md"
        content: |
          # 技能安全审查报告
          
          **技能名称**: {{skill_name}}
          **审查时间**: {{timestamp}}
          **路径**: {{skill_path}}
          
          ## 检查结果
          - [x] 结构检查
          - [x] 敏感信息扫描
          - [x] 权限声明
          - [x] 功能测试
          
          ## 结论
          技能已通过安全审查，可以发布。
```

---

## 5. 与 OpenSpec / KnowFlow 的协同

### 与 OpenSpec 的关系

| 维度 | OpenSpec | AutoFlow |
|-----|----------|----------|
| **核心问题** | "为什么做、改什么、如何验证" | "怎么把重复流程稳定执行出来" |
| **输出物** | 变更提案、设计文档 | 可执行的 Flow YAML |
| **生命周期** | 规划 → 设计 → 实现 → 验证 | 执行 → 监控 → 重试 → 完成 |

**建议协同方式**：

```
OpenSpec 变更提案
      │
      ▼
┌─────────────────┐
│ 识别可流程化部分  │ ← Agent 判断哪些步骤适合 AutoFlow
└─────────────────┘
      │
      ▼
创建 AutoFlow Flow  ← 在变更目录下创建 flow.yaml
      │
      ▼
执行 Flow 验证      ← 通过桥接件执行
      │
      ▼
OpenSpec archive   ← 归档结果，包含执行日志
```

**具体实践**：
1. 在 OpenSpec 变更的 `specs/` 目录下放置关联的 Flow 文件
2. 使用 `openspec exec-flow <change-id>` 触发关联 Flow
3. 将 Flow 执行结果作为变更验收的一部分
4. 在 OpenSpec archive 时，同时归档 Flow 的执行历史

### 与 KnowFlow 的关系

| 维度 | KnowFlow | AutoFlow |
|-----|----------|----------|
| **核心职责** | 记录结构化知识和文档 | 执行流程并产出结果 |
| **数据流向** | 接收归档内容 | 输出执行产物 |
| **查询方式** | 搜索、浏览知识图谱 | 查询运行状态、日志 |

**建议协同方式**：

```
AutoFlow 执行
      │
      ├──→ 执行日志 → KnowFlow (技术运维知识)
      │
      ├──→ 执行报告 → KnowFlow (项目文档)
      │
      └──→ 失败分析 → KnowFlow (经验沉淀)
```

**具体实践**：
1. Flow 执行完成后，自动将摘要写入 KnowFlow
2. 失败的 Flow 在 KnowFlow 中创建故障案例
3. KnowFlow 中保存"发生了什么"，AutoFlow 保存"怎么执行的"
4. 在 KnowFlow 中建立 Flow 执行索引，便于追溯

### 三者协同工作流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  OpenSpec   │────→│  AutoFlow   │────→│  KnowFlow   │
│  (规划层)    │     │  (执行层)    │     │  (知识层)    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │ 1.定义变更         │ 2.执行流程         │ 3.归档结果
       │                   │                   │
       └───────────────────┴───────────────────┘
                    闭环工作流
```

**典型场景示例**：

1. **新功能开发**：
   - OpenSpec：编写功能变更提案
   - AutoFlow：执行"开发准备 Flow"（创建分支、初始化环境）
   - KnowFlow：归档设计决策和开发记录

2. **发布流程**：
   - OpenSpec：定义发布检查清单
   - AutoFlow：执行"发布检查 Flow"（测试、构建、部署）
   - KnowFlow：记录发布版本和变更摘要

3. **故障处理**：
   - KnowFlow：查询历史故障案例
   - AutoFlow：执行"诊断 Flow"（收集日志、运行检查）
   - OpenSpec：如有必要，创建修复变更

---

## 6. 团队实践建议

### 入门阶段
1. **先从小流程开始**：先做冒烟测试、项目初始化，不要一开始就做超大编排
2. **模板先于平台增强**：先用现有 API 桥接，不急着改 AutoFlow 核心
3. **一个 Flow 只做一类事**：不要做过度庞杂的万能流程

### 进阶阶段
4. **Flow 参数化**：把项目名、URL、分支名等做成变量，提高复用性
5. **Agent 负责判断，AutoFlow 负责执行**：推理和协调还是由 Agent 完成
6. **建立 Flow 版本管理**：将 Flow YAML 纳入版本控制，便于追踪变更

### 最佳实践
7. **命名规范**：`{领域}-{动作}-{目标}`，如 `skill-security-review`
8. **文档化**：每个 Flow 都要有 description，说明用途和参数
9. **错误处理**：为关键步骤配置 check 和 retry
10. **日志保留**：定期归档运行日志到 KnowFlow

### 避坑指南

| ❌ 不推荐 | ✅ 推荐 |
|---------|--------|
| 一个 Flow 超过 20 个步骤 | 拆分为多个子 Flow |
| 在 Flow 中做复杂条件判断 | 简单判断用 check，复杂判断交给 Agent |
| 硬编码敏感信息 | 使用 Secrets 引用 |
| 忽略失败处理 | 每个关键步骤配置 retry 和失败通知 |
| Flow 逻辑频繁变动 | 先在 Agent 对话中验证流程，稳定后再固化 |

---

## 附录：快速参考

### 常用 Action 类型

| 类型 | 用途 | 示例 |
|-----|------|------|
| `http.request` | 调用 API | 健康检查、数据同步 |
| `shell.exec` | 执行命令 | Git 操作、构建脚本 |
| `file.read/write/append` | 文件操作 | 生成报告、记录日志 |
| `message.send` | 发送通知 | 执行完成提醒 |

### 常用 Check 类型

| 类型 | 用途 |
|-----|------|
| `shell.exitCode` | 验证命令退出码 |
| `text.contains` | 检查文本包含 |
| `text.doesNotContain` | 检查文本不包含 |
| `json.path` | JSON 路径验证 |

### 变量引用语法

```yaml
# 使用双花括号引用变量
{{variable_name}}

# 使用步骤输出
{{steps.step_id.output}}

# 内置变量
{{timestamp}}  # 当前时间戳
{{date}}       # 当前日期
```
