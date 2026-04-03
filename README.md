
使用
```bash
# 1. 配置环境变量（首次）
cp .env.example .env
# 编辑 .env 修改密码

# 2. 初始化 secrets（Docker 模式必须）
./scripts/init-secrets.sh

# 3a. 本地开发
./scripts/start.sh local full     # 后端:3001  前端:5181

# 3b. Docker 开发
./scripts/start.sh dev full       # 后端:3001  前端:8001
./scripts/start.sh dev backend    # 仅后端:3001

# 4. 停止
./scripts/stop.sh dev
```
