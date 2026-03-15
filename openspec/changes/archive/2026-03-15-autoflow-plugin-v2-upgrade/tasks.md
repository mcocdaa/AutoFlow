# Tasks: AutoFlow Plugin v2 Upgrade

## Task 1: 合并上游 main 更新
- [x] `git merge FETCH_HEAD` 将上游 main 合并到 openclaw 分支
- [x] 解决冲突（models/models.py 注释差异、runner.py 移位、测试文件 add/add）

## Task 2: 创建 backend.py
- [x] 上游 merge 已带入 `plugins/openclaw/backend.py`
- [x] import 路径已正确：`from app.plugin.registry import ActionContext, CheckContext`

## Task 3: 创建声明文件
- [x] `plugins/openclaw/plugin.yaml` 已由 merge 带入
- [x] `plugins/openclaw/config.yaml` 已由 merge 带入

## Task 4: 验证插件加载
- [x] 本地 Python 验证：`openclaw` 插件注册成功
- [x] 3 actions + 2 checks 全部注册

## Task 5: 提交并推送
- [x] `git commit`：merge commit `4203873`
- [x] `git push origin openclaw`：推送成功
