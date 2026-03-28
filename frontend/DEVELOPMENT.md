# AutoFlow 前端开发指引

## 🚀 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

开发服务器将启动在 `http://localhost:5180/`

### 构建生产版本

```bash
npm run build
```

---

## 📂 目录导航（新手必看）

### 第一次接触？从这里开始：

1. **查看页面** → 去 `src/views/` 目录，看 `PluginsView.vue` 和 `RunFlowView.vue`
2. **了解布局** → 看 `src/App.vue`，了解 FDS 标准布局
3. **了解主题** → 看 `src/theme/flow-design-theme.ts`，了解 FDS 设计规范
4. **了解状态管理** → 看 `src/stores/` 目录

### 我想修改页面 → 去 `src/views/`

### 我想修改组件 → 去 `src/components/`

### 我想添加 API → 去 `src/api/index.ts`

### 我想添加工具函数 → 去 `src/utils/`

---

## 💡 常见开发任务

### 任务 1：添加一个新页面

**步骤：**

1. 在 `src/views/` 创建新组件，例如 `NewPage.vue`

```vue
<template>
  <div class="new-page">
    <div class="page-header">
      <div class="header-left">
        <SomeOutlined class="title-icon" />
        <h2 class="page-title">新页面标题</h2>
      </div>
    </div>
    <!-- 页面内容 -->
  </div>
</template>

<script setup lang="ts">
import { SomeOutlined } from '@ant-design/icons-vue'
</script>

<style scoped>
.new-page {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 24px;
  color: var(--flow-color-primary);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin: 0;
}
</style>
```

2. 在 `src/router/index.ts` 添加路由

```typescript
import NewPage from '../views/NewPage.vue'

const routes = [
  // ... 现有路由
  {
    path: '/new-page',
    name: 'newPage',
    component: NewPage,
  },
]
```

3. 在 `src/App.vue` 添加菜单项

```vue
<a-menu-item key="/new-page" @click="router.push('/new-page')">
  <template #icon><SomeOutlined /></template>
  <span>新页面</span>
</a-menu-item>
```

---

### 任务 2：使用状态管理（Pinia）

**读取状态：**

```vue
<script setup lang="ts">
import { usePluginsStore } from '../stores/plugins'

const store = usePluginsStore()

// 访问状态
console.log(store.plugins)

// 调用 action
store.fetchPlugins()
</script>
```

---

### 任务 3：使用 API

```typescript
import { fetchPlugins } from '../api'

const plugins = await fetchPlugins()
```

---

### 任务 4：使用工具函数

```typescript
import { formatDate, getStorage, setStorage } from '../utils'

const formattedDate = formatDate(new Date())
setStorage('key', 'value')
const value = getStorage('key', 'default')
```

---

## 🎨 FDS 设计规范（必须遵守）

### 使用 CSS 变量（不要硬编码颜色！）

| 用途 | CSS 变量 | 值 |
|------|----------|-----|
| 主色 | `--flow-color-primary` | #2563EB |
| 成功色 | `--flow-color-success` | #10B981 |
| 警告色 | `--flow-color-warning` | #F59E0B |
| 错误色 | `--flow-color-danger` | #EF4444 |
| 页面背景 | `--flow-bg-page` | #F8FAFC |
| 卡片背景 | `--flow-bg-card` | #FFFFFF |
| 标题文字 | `--flow-text-title` | #0F172A |
| 主要文字 | `--flow-text-primary` | #334155 |
| 辅助文字 | `--flow-text-secondary` | #64748B |
| 小圆角 | `--flow-border-radius-sm` | 6px |
| 中圆角 | `--flow-border-radius-md` | 8px |
| 大圆角 | `--flow-border-radius-lg` | 12px |

**示例：**

```css
/* ✅ 正确 */
color: var(--flow-color-primary);
background: var(--flow-bg-card);
border-radius: var(--flow-border-radius-lg);

/* ❌ 错误 */
color: #2563EB;
background: white;
border-radius: 12px;
```

### 使用 Ant Design Vue 组件

所有 UI 组件都使用 Ant Design Vue，不要自己写组件！

```vue
<template>
  <a-button type="primary">主按钮</a-button>
  <a-card>卡片内容</a-card>
  <a-input placeholder="输入框" />
</template>
```

---

## 📚 相关文档

- [Vue 3 文档](https://cn.vuejs.org/)
- [Ant Design Vue 文档](https://antdv.com/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [项目结构说明](./src/README.md)
- [FDS 设计规范](../task.md)
