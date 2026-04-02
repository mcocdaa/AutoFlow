# AutoFlow 测试计划

## 1. 服务存活检查

### 目标

确认 AutoFlow 后端可访问，并且核心接口在线。

### 检查步骤

1. 访问 `GET http://localhost:8000/api/v1/plugins`
2. 若返回 200，则说明服务基本可用
3. 若失败，再检查：
   - 端口是否正确
   - 后端服务是否启动
   - Docker / 本地 Python 进程是否在运行

### PowerShell 示例

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/plugins" -Method Get
```

---

## 2. 四个接口测试方法

### A. execute 接口

**接口**: `POST /api/v1/runs/execute`

**测试目标**:

- 能接受合法的 flow_yaml
- 能返回 `run_id`、`flow_name`、`status`、`steps`

**测试方式**:

```powershell
$body = @{
  flow_yaml = @"
version: ""1""
name: ""smoke-demo""
steps:
  - id: ""fetch""
    action:
      type: ""http.request""
      params:
        method: ""GET""
        url: ""https://example.com""
"@
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/runs/execute" -Method Post -Body $body -ContentType "application/json"
```

### B. list 接口

**接口**: `GET /api/v1/runs`

**测试目标**:

- 能列出历史 run
- 返回数组结构稳定

### C. get 接口

**接口**: `GET /api/v1/runs/{run_id}`

**测试目标**:

- 能获取单个 run 详情
- 不存在的 run_id 返回 404

### D. plugins 接口

**接口**: `GET /api/v1/plugins`

**测试目标**:

- 能返回 plugins/actions/checks/errors
- 输出字段结构稳定

---

## 3. 最小 smoke test Flow

```yaml
version: "1"
name: "smoke-minimal"
steps:
  - id: "fetch-example"
    name: "Fetch example"
    action:
      type: "http.request"
      params:
        method: "GET"
        url: "https://example.com"
```

### 选择原因

- 步骤最少
- YAML 简单
- 便于验证 execute 基本通路

---

## 4. 失败场景测试

### 场景 1：坏 YAML

目标：验证服务对非法 flow_yaml 能返回 400

示例：

```json
{
  "flow_yaml": "not-a-valid-yaml:::"
}
```

### 场景 2：不存在的 run_id

目标：验证 `GET /runs/{id}` 对不存在资源返回 404

示例：

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/runs/not-exists" -Method Get
```

---

## 5. 清理策略

当前 API 未提供显式删除 run 的接口，因此清理策略为：

1. 测试前记录测试 run 的 `flow_name`
2. 测试后在报告中标记这些 run 为测试数据
3. 如后端后续支持删除接口，再纳入自动清理

---

## 6. 风险点

1. **端口不确定**
   - 设计默认用 `http://localhost:8000`
   - 实际部署可能不同，需要允许 BaseUrl 覆盖

2. **返回结构可能演进**
   - list/get 的字段依赖 `RunResult`
   - 桥接脚本宜保守解析，必要时透传原始 JSON

3. **插件能力缺失**
   - 最小 smoke test 使用的 action 类型必须真实已注册
   - 否则 execute 会失败

4. **示例 Flow 与真实插件不匹配**
   - 文档模板是示意，不保证每个环境都有相同插件
   - 测试前要先查 `/api/v1/plugins`

5. **外部依赖不稳定**
   - 若 Flow 使用外部 URL 或 AI 插件，可能受网络和密钥影响

---

## 7. 测试结论标准

认为桥接件“基本可用”的最低标准：

1. plugins 接口可访问
2. runs list/get 可访问
3. execute 能成功执行至少一个最小 Flow
4. 非法输入能正确报错
