# 阶段三:前端 — API 层增强 / useAsyncState 状态层重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-subagent-driven-development (recommended) or superpowers-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强 api 层(响应拦截器统一错误提取 + 类型化接口函数)与状态层(useAsyncState composable 收敛 loading/error 样板,stores 重构为 setup store 风格),视图层零改动保持兼容,vue-tsc 严格模式构建通过。

**Architecture:** 错误提取逻辑从各 store 收敛到 axios 响应拦截器与 `getErrorMessage` 工具;API 调用按资源拆分 `api/plugins.ts`、`api/runs.ts` 类型化函数;新增泛型 `useAsyncState` composable 封装 data/loading/error/execute 生命周期;两个 Pinia store 改为 setup store 风格组合 useAsyncState,ref 天然成为 store state,视图既有用法(`store.loading`、`store.error`、`store.executeFlow(...)`、`@click="store.fetchPlugins"`)不变。

**Tech Stack:** Vue 3.3+、TypeScript(vue-tsc 严格模式)、Pinia、axios。验证命令:`cd frontend && npm run build:web`(即 `vue-tsc && vite build`,预期 `✓ built in ...`)。

---

## 0. 前置状态与约定

1. 仓库 main 分支当前形态(阶段一/二未影响前端)。
2. 现有文件:`frontend/src/api/index.ts`(16 行,仅 axios client)、`frontend/src/stores/plugins.ts`(options store)、`frontend/src/stores/runs.ts`(options store)、`frontend/src/types/plugins.ts`、`frontend/src/types/runs.ts`、`frontend/src/composables/useClipboard.ts`。
3. 视图消费方式(必须保持兼容):
   - `PluginsView.vue`:`store.fetchPlugins`(直接方法引用 `@click="store.fetchPlugins"`)、`store.loading`、`store.plugins`、`store.actions`、`store.checks`、`store.errors`、`store.error`(computed 使用)。
   - `RunFlowView.vue`:`store.loading`、`store.error`、`store.currentRun`、`await store.executeFlow(yaml, {}, vars)`(executeFlow 抛错,视图有 catch)。
   - `ResultsPanel.vue` 经 props 接收 `currentRun`。
4. 约定:commit 前缀 `refactor(frontend):`;每个任务独立 commit;不引入新依赖;无测试框架,vue-tsc 严格模式为类型验证,vite build 为产物验证。

## 1. 文件结构

### 新建
- `frontend/src/api/plugins.ts` — 类型化接口:`fetchPlugins()`
- `frontend/src/api/runs.ts` — 类型化接口:`executeFlow()`、`fetchRun()`
- `frontend/src/composables/useAsyncState.ts` — 泛型异步状态封装

### 修改
- `frontend/src/api/index.ts` — 响应拦截器 + 导出 `getErrorMessage`
- `frontend/src/types/plugins.ts` — 补充 `PluginsResponse`
- `frontend/src/stores/plugins.ts` — 重构为 setup store
- `frontend/src/stores/runs.ts` — 重构为 setup store

### 不动
- `frontend/src/views/*`、`frontend/src/components/*`、`frontend/src/types/runs.ts`、`frontend/src/composables/useClipboard.ts`

---

## Task 1: types 补充 + api 拦截器与 getErrorMessage

**Files:**
- Modify: `frontend/src/types/plugins.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: types/plugins.ts 补充 PluginsResponse**

在 `frontend/src/types/plugins.ts` 末尾追加:

```ts
export interface PluginsResponse {
  plugins: Plugin[]
  actions: string[]
  checks: string[]
  errors: PluginError[]
}
```

- [ ] **Step 2: api/index.ts 加拦截器与 getErrorMessage**

`frontend/src/api/index.ts` 全文替换为:

```ts
import axios from 'axios'

interface AutoflowBridge {
  apiBase?: string
}
const bridge = (window as unknown as { autoflow?: AutoflowBridge }).autoflow
const baseURL = bridge?.apiBase ? `${bridge.apiBase}/api/v1` : '/api/v1'

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 统一错误标准化:优先提取后端返回的 response.data.detail
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    if (detail !== undefined && detail !== null) {
      error.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    return Promise.reject(error)
  },
)

export default apiClient
```

- [ ] **Step 3: 类型验证**

Run: `cd frontend && npm run build:web`
Expected: vue-tsc 无错误,`✓ built in ...`,exit 0。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/plugins.ts frontend/src/api/index.ts
git commit -m "refactor(frontend): unify error extraction via axios interceptor (T1)"
```

## Task 2: api 类型化接口函数

**Files:**
- Create: `frontend/src/api/plugins.ts`
- Create: `frontend/src/api/runs.ts`

- [ ] **Step 1: 新建 api/plugins.ts**

```ts
import apiClient from './index'
import type { PluginsResponse } from '../types/plugins'

export async function fetchPlugins(): Promise<PluginsResponse> {
  const { data } = await apiClient.get<PluginsResponse>('/plugins')
  return data
}
```

- [ ] **Step 2: 新建 api/runs.ts**

```ts
import apiClient from './index'
import type { RunResult } from '../types/runs'

export async function executeFlow(
  flowYaml: string,
  input: unknown = {},
  vars: Record<string, unknown> = {},
): Promise<RunResult> {
  const { data } = await apiClient.post<RunResult>('/runs/execute', {
    flow_yaml: flowYaml,
    input,
    vars,
  })
  return data
}

export async function fetchRun(runId: string): Promise<RunResult> {
  const { data } = await apiClient.get<RunResult>(`/runs/${runId}`)
  return data
}
```

- [ ] **Step 3: 类型验证**

Run: `cd frontend && npm run build:web`
Expected: 无错误,`✓ built in ...`。(新文件尚未被引用,类型检查仍覆盖。)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/plugins.ts frontend/src/api/runs.ts
git commit -m "refactor(frontend): add typed API functions (T2)"
```

## Task 3: useAsyncState composable

**Files:**
- Create: `frontend/src/composables/useAsyncState.ts`

- [ ] **Step 1: 新建 useAsyncState.ts**

```ts
import { ref } from 'vue'
import { getErrorMessage } from '../api'

export function useAsyncState<TArgs extends unknown[], TData>(
  fetcher: (...args: TArgs) => Promise<TData>,
) {
  const data = ref<TData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const execute = async (...args: TArgs): Promise<TData> => {
    loading.value = true
    error.value = null
    try {
      const result = await fetcher(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = getErrorMessage(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}
```

- [ ] **Step 2: 类型验证**

Run: `cd frontend && npm run build:web`
Expected: 无错误,`✓ built in ...`。(未引用不报错;vue-tsc 校验语法与类型。)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useAsyncState.ts
git commit -m "refactor(frontend): add useAsyncState composable (T3)"
```

## Task 4: stores/plugins.ts 重构为 setup store

**Files:**
- Modify: `frontend/src/stores/plugins.ts`

- [ ] **Step 1: 全文替换 stores/plugins.ts**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchPlugins as apiFetchPlugins } from '../api/plugins'
import { useAsyncState } from '../composables/useAsyncState'
import type { Plugin, PluginError } from '../types/plugins'

export const usePluginsStore = defineStore('plugins', () => {
  const plugins = ref<Plugin[]>([])
  const actions = ref<string[]>([])
  const checks = ref<string[]>([])
  const errors = ref<PluginError[]>([])

  const { loading, error, execute } = useAsyncState(async () => {
    const data = await apiFetchPlugins()
    plugins.value = data.plugins
    actions.value = data.actions
    checks.value = data.checks
    errors.value = data.errors || []
    return data
  })

  return { plugins, actions, checks, errors, loading, error, fetchPlugins: execute }
})
```

- [ ] **Step 2: 类型验证 + 视图引用核对**

Run: `cd frontend && npm run build:web`
Expected: 无错误,`✓ built in ...`。

核对 PluginsView.vue 的用法不变:`store.fetchPlugins`、`store.loading`、`store.plugins/actions/checks/errors`、`store.error` — setup store 返回的 ref 自动解包为 state,`execute` 是函数引用可直接绑定。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/plugins.ts
git commit -m "refactor(frontend): convert plugins store to setup style with useAsyncState (T4)"
```

## Task 5: stores/runs.ts 重构为 setup store

**Files:**
- Modify: `frontend/src/stores/runs.ts`

- [ ] **Step 1: 全文替换 stores/runs.ts**

```ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { executeFlow as apiExecuteFlow, fetchRun as apiFetchRun } from '../api/runs'
import { useAsyncState } from '../composables/useAsyncState'
import type { RunResult } from '../types/runs'

export const useRunsStore = defineStore('runs', () => {
  const currentRun = ref<RunResult | null>(null)

  const { loading: execLoading, error: execError, execute: execFlow } = useAsyncState(
    async (flowYaml: string, input: unknown, vars: Record<string, unknown>) => {
      const data = await apiExecuteFlow(flowYaml, input, vars)
      currentRun.value = data
      return data
    },
  )

  const { loading: fetchLoading, error: fetchError, execute: fetchOne } = useAsyncState(
    async (runId: string) => {
      const data = await apiFetchRun(runId)
      currentRun.value = data
      return data
    },
  )

  const loading = computed(() => execLoading.value || fetchLoading.value)
  const error = computed(() => execError.value ?? fetchError.value)

  return { currentRun, loading, error, executeFlow: execFlow, fetchRun: fetchOne }
})
```

- [ ] **Step 2: 类型验证 + 视图引用核对**

Run: `cd frontend && npm run build:web`
Expected: 无错误,`✓ built in ...`。

核对 RunFlowView.vue 用法不变:`store.loading`、`store.error`、`store.currentRun`、`await store.executeFlow(yaml, {}, vars)`(executeFlow 抛错路径保留,视图 catch 后 console.error)。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/runs.ts
git commit -m "refactor(frontend): convert runs store to setup style with useAsyncState (T5)"
```

## Task 6: 全量验证与冒烟

**Files:** 无代码改动

- [ ] **Step 1: 类型与构建全量验证**

Run: `cd frontend && npm run build:web`
Expected: vue-tsc 无错误,`✓ built in 17s` 左右,exit 0。

- [ ] **Step 2: 运行时冒烟(dev server + 后端)**

后端已由阶段二验证,此步验证前端数据链路:

```bash
cd backend && env PYTHONPATH=$PWD setsid .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 3001 > /tmp/opencode/backend-dev.log 2>&1 < /dev/null &
cd frontend && env DOCKER_WEB=true setsid npm run dev > /tmp/opencode/frontend-dev.log 2>&1 < /dev/null &
sleep 10
curl -s --max-time 8 http://127.0.0.1:5180/api/v1/plugins | head -c 200
curl -s --max-time 8 http://127.0.0.1:5180/api/v1/runs/execute -X POST -H "Content-Type: application/json" -d '{"flow_yaml":"version: \"1\"\nname: \"smoke\"\nsteps:\n  - id: \"s1\"\n    action:\n      type: \"core.log\"\n      params:\n        message: \"smoke\"","vars":{}}' | head -c 200
```

Expected: plugins JSON 含 6 个插件(经 vite 代理,HTTP 200);execute 返回 `"status":"success"`。

错误路径验证(detail 提取):

```bash
curl -s --max-time 8 http://127.0.0.1:5180/api/v1/runs/execute -X POST -H "Content-Type: application/json" -d '{"flow_yaml":"not yaml"}'
```

Expected: 400 响应,JSON detail 字段(前端拦截器会将其作为 error.message 展示)。

- [ ] **Step 3: 清理进程**

```bash
pkill -f "uvicorn app.main" ; pkill -f "vite" ; sleep 1; echo cleaned
```

- [ ] **Step 4: 工作区状态确认**

Run: `cd /home/mcocdaa/AI_CODE/AutoFlow && git status --short`
Expected: 干净(或仅未跟踪的构建产物,确认无意外改动)。

- [ ] **Step 5: 阶段验收 grep**

Run: `cd frontend && grep -rn "\.response?\.\.data" src/`
Expected: 无命中(错误提取逻辑已全部收敛到 api 层)。
