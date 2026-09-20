# AutoFlow — Notes for Coding Agents

本文件面向在 AutoFlow 仓库中工作的 AI Coding Agent。用户文档见 [README.md](README.md)，开发与规范详见 [docs/](docs/)。

## 1. Read First (必读指引)

1. 先阅读 [通用规范文档](docs/rules/index.md)，包括 [code.md](docs/rules/code.md)（代码规范）、[api-spec.md](docs/rules/api-spec.md)（API 规范）、[docker.md](docs/rules/docker.md)（部署规范）与 [docs.md](docs/rules/docs.md)（文档规范）。
2. AutoFlow 是面向 Agent 团队的确定性执行引擎（Flow: Trigger -> Action -> Check）。修改引擎核心行为时，必须阅读当前已有测试和 Flow 样例。
3. 工作区存在未提交变动时，先确认目标文件无冲突，只暂存与本次任务直接相关的文件。

## 2. Repository Rules & Constraints (核心契约与安全规则)

- **单镜像全栈**：项目默认以单容器形态交付（多阶段构建前端页面，后端同端口暴露 Web 页面与 API）。
- **统一脚本入口**：启动前后端或容器一律通过 `scripts/start.sh`（Docker 全栈或 local 模式），停止通过 `scripts/stop.sh`。
- **敏感信息隔离**：绝不提交 `.env`、API Key（如 `DEEPSEEK_API_KEY`、`ZHIHU_COOKIE`）、运行历史和调试快照至 Git。
- **API 契约**：接口遵循 `/api/v1/` 统一路由结构，支持路由自动扫描加载器；错误返回遵循统一标准结构。

## 3. Essential Commands (核心研发命令)

```bash
# 后端测试与检查
cd backend
poetry run pytest                      # 单元测试 (150+ 项)
poetry run ruff check app ../plugins   # 代码静态检查与导入排序
poetry run ruff format --check app     # 代码格式检查

# 前端开发与构建
cd ../frontend
npm run lint                           # ESLint 检查
npm run build                          # 前端构建验证

# 服务启动
cd ..
./scripts/start.sh                     # Docker 全栈启动
./scripts/start.sh local all           # 本地双进程启动 (前端 5173 + 后端 3001)
```

## 4. Verification Checklist (提交前自检)

- [ ] 后端 pytest 测试套件全绿
- [ ] 代码通过 Ruff 检查与格式化要求
- [ ] 前端构建 `npm run build` 无编译与类型错误
- [ ] 若增删环境变量或接口，已同步更新 `.env.example` 与相关文档
