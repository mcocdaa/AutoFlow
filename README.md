# AutoFlow

**AutoFlow** 是一款面向"替换重复性劳动"的自动化（RPA）框架：用统一的流程描述（Flow）把触发（Trigger）→ 执行（Action）→ 校验（Check）串起来，并通过插件化机制接入具体业务。

当前仓库采用 Monorepo 统一管理后端、桌面端、移动端与插件示例。项目仍在快速迭代中，README 以"框架定位 + 未来计划"为主，便于后续按里程碑落地。

## 🚀 核心特性

- **可编排流程**：用统一流程描述把动作串起来，支持参数、上下文、失败重试与分支（逐步完善）。
- **可插拔触发**：定时触发 / 事件触发 / 文档触发（以"触发文档"为入口，逐步标准化）。
- **可选结果校验**：每步动作可配置 Check；不配置则默认不校验（适合先跑通，再加严）。
- **多端适配**：面向 Windows/macOS 桌面与 Android/iOS 移动端的统一抽象（能力逐步补齐）。
- **插件化扩展**：具体业务能力（如"知乎自动总结""桌面自动打卡"）以插件实现，框架提供运行时与安全边界。

## 🧠 核心概念

- **Flow（流程）**：由一系列 Step 组成，每个 Step 至少包含 Action，可选包含 Check。
- **Trigger（触发器）**：决定何时启动某个 Flow。支持多种 TriggerType。
- **Action（动作）**：执行具体操作（HTTP 调用、抓取、点击、拖拽、输入等）。
- **Check（校验）**：在 Action 后对结果做断言（例如"页面出现某元素""接口返回 200""OCR 识别包含某文本"）。
- **Runner（运行器）**：负责加载 Trigger/Flow，执行 Step，并产生日志、截图、录屏等产物（能力逐步补齐）。
- **Plugin（插件）**：封装领域能力，提供 TriggerType / Action / Check / UI 配置面板等扩展点。

## 🧩 "触发文档"约定（草案）

为便于把"自动化任务"当作一种可版本化的资产管理，推荐用 Markdown/YAML 作为"触发文档（TriggerDoc）"载体：

```yaml
name: zhihu-digest
trigger:
  type: zhihu.question
  mode: link # link | cron-random
  link: https://www.zhihu.com/question/xxxx
  cron: "0 9 * * *" # mode=cron-random 时生效
flow:
  ref: flows/zhihu-digest.flow.yaml
checks:
  enabled: true
```

说明：

- TriggerDoc 负责"为什么/何时跑"，Flow 负责"怎么跑"。
- 插件可以扩展 trigger.type 的枚举和值结构，并提供 UI 辅助生成。

## 📂 项目结构

本项目采用 Monorepo（单体仓库）结构，统一管理前后端与插件代码：

```
AutoFlow/
├── backend/               # 🐍 后端核心 (FastAPI + Python 3.10+)
│   ├── app/               # 业务逻辑与 API
│   ├── Dockerfile         # 生产环境 Docker 镜像
│   ├── docker-compose.yml # 后端服务编排（含 MySQL、Redis）
│   └── tests/             # 单元测试
├── frontend/              # 🖥️ 桌面客户端 (Electron + Vue3 + TypeScript)
│   ├── electron/          # Electron 主进程
│   └── src/               # Vue3 渲染进程
├── mobile/                # 📱 移动端 (UniApp)
├── plugins/               # 🔌 插件系统 (标准插件示例与文档)
├── docs/                  # 📚 项目文档
├── docker-compose.yml     # 🐳 服务编排入口（include backend/frontend）
└── build.sh               # 🔧 构建脚本（生成 secrets 文件）
```

## 🗺️ 路线图（框架 + 两个插件）

下面按"框架能力"与"插件落地"拆分待办，便于逐步交付可用闭环。

### 0. 框架必备能力（优先级从高到低）

- **Trigger 运行时**：定时/事件/文档触发的统一调度入口；支持启停、并发限制、失败重试、幂等标识。
- **Flow 规范与解析**：定义 Flow/Step/Action/Check 的数据结构与校验；提供版本号与向后兼容策略。
- **Action/Check 基础库**：最小可用集合（HTTP、抓取、点击/输入、等待、截图、文本匹配等）。
- **运行产物与可观测性**：结构化日志、执行记录、产物存储（截图/HTML/JSON）、任务追踪 ID。
- **安全与密钥管理**：统一管理第三方 Cookie/Token/API Key；避免写入明文；权限隔离与审计。
- **插件 SDK 与边界**：插件注册机制、配置 schema、权限声明、沙箱/能力限制、升级兼容策略。

### 1) 插件：知乎自动总结 + 文档撰写（草案）

目标：针对某个问题，读取高质量回答与评论，沉淀可追溯的原始材料，并调用指定 AI API 产出总结/改写内容，最终发布到知乎。

当前进展（MVP）：

- 已提供动作：`zhihu.fetch_answer` / `ai.deepseek_summarize` / `zhihu.post_answer_draft`（发布不做结果验证）
- 示例 Flow：`docs/examples/zhihu_digest.flow.yaml`（可配合 `vars: { dry_run: true }` 先验证链路与产物落盘）
- AI Provider 已拆分为独立插件（例如 `ai-deepseek`），通过环境变量 `DEEPSEEK_API_KEY`（或 `DEEPSEEK_API_KEY_FILE`）提供密钥

还需要做什么：

- **触发类型设计**：
  - `zhihu.question` + `mode=link`：给定具体问题链接触发
  - `zhihu.question` + `mode=cron-random`：定时触发，随机取一个问题回答
- **数据采集与存档**：抓取回答、评论、作者、时间、赞同数等元数据；按问题维度落盘成文档（Markdown/JSON）。
- **反爬与登录策略**：Cookie/登录态管理；速率限制；失败退避；必要时支持手动刷新凭证。
- **AI 生成链路**：构建可控的 Prompt/模板；支持多模型配置；输出格式约束（标题/要点/引用来源）。
- **发布链路**：知乎发布接口/自动化发布（取决于可用能力）；支持草稿、预览与人工确认开关。
- **合规与风控**：引用标注、敏感词检查、内容重复度检测、发布频率控制、可追责日志。

### 2) 插件：桌面自动打卡（草案）

目标：按触发逻辑执行一系列桌面操作（点击、双击、拖拽、输入等），并在每步结束后按需校验结果；默认不校验，但允许用户在触发逻辑中补充检查。

当前进展（MVP）：

- 已提供基础动作原语：`desktop.activate_window` / `desktop.click` / `desktop.double_click` / `desktop.drag` / `desktop.type_text` / `desktop.hotkey` / `desktop.wait` / `desktop.screenshot`
- 已提供基础校验：`desktop.image_exists` / `desktop.window_title_contains`
- 示例 Flow：`docs/examples/desktop_checkin.flow.yaml`（可配合 `vars: { dry_run: true }` 在无桌面环境下验证流程与产物落盘）

还需要做什么：

- **动作原语定义**：click/doubleClick/drag/typeText/hotkey/wait 等统一接口与参数（坐标、窗口、元素定位）。
- **定位与鲁棒性**：支持窗口匹配、图像/模板匹配、OCR 文本定位等；提供"找不到目标"的降级策略。
- **结果检查机制**：为每个 Step 绑定可选 Check（元素出现、OCR 包含、窗口标题匹配等）；默认关闭。
- **录制与回放闭环**：桌面端录制输出 Flow；回放展示实时状态；失败时可回溯到某一步重跑。
- **环境适配**：多分辨率/DPI、不同主题、不同机器的偏移校正；提供校准向导与重录策略。
- **安全与权限**：本地执行权限、敏感输入（密码）保护、日志脱敏、最小权限原则。

## 🛠️ 快速开始

### 前置要求

- **Docker**: 20.10+
- **Docker Compose**: v2.0+

### 1. 初始化配置

```bash
# 生成 secrets 文件
bash scripts/init-secrets.sh

# (可选) 复制环境变量模板并修改
# cp .env.example .env
```

### 2. 启动服务（选择模式）

**全栈模式**（推荐，前端 + 后端 + 数据库）：

```bash
bash scripts/start-fullstack.sh
```

**仅后端模式**（API 开发）：

```bash
bash scripts/start-backend.sh
```

**仅前端模式**（连接外部后端）：

```bash
# 编辑 .env 设置 VITE_API_URL 指向你的后端地址
bash scripts/start-frontend.sh
```

### 3. 访问服务

| 服务     | 地址                       | 说明         |
| -------- | -------------------------- | ------------ |
| 前端     | http://localhost:8001      | Web 演示模式 |
| 后端 API | http://localhost:3001      | REST API     |
| API 文档 | http://localhost:3001/docs | Swagger UI   |

### 4. 运行桌面端 (Frontend 本地开发)

```bash
cd frontend

# 安装依赖
npm install

# 启动开发模式 (同时启动 Vue 和 Electron)
npm run dev
```

## 📝 开发指南

- **插件开发**: 请参考 [plugins/README.md](plugins/README.md)
- **架构文档**: 详见 [docs/architecture/README.md](docs/architecture/README.md)

## 📄 License

[LICENSE](LICENSE)
