# AutoFlow 前端项目

## 📁 目录结构

```
src/
├── api/                    # API 接口层
│   └── index.ts           # 所有 API 请求定义
│
├── assets/                 # 静态资源
│   ├── images/            # 图片资源
│   └── fonts/             # 字体资源
│
├── components/             # Vue 组件
│   ├── plugins/           # 插件管理组件
│   ├── run/               # 运行流组件
│   ├── workflow/          # 工作流编辑器组件 ✨
│   └── shared/            # 共享组件
│
├── composables/            # 可复用组合式函数
│   ├── useClipboard.ts
│   └── useMobile.ts
│
├── constants/              # 常量定义
│   ├── plugins.ts
│   └── flow-examples.ts
│
├── layouts/                # 布局组件
│
├── router/                 # 路由配置
│   └── index.ts
│
├── stores/                 # Pinia 状态管理
│   ├── plugins.ts
│   ├── runs.ts
│   └── workflow.ts        # 工作流状态
│
├── theme/                  # 主题配置
│   └── flow-design-theme.ts
│
├── types/                  # TypeScript 类型定义
│   ├── plugins.ts
│   ├── runs.ts
│   └── workflow.ts
│
├── utils/                  # 工具函数
│   ├── format.ts
│   ├── storage.ts
│   └── workflow-yaml.ts   # 工作流 YAML 转换
│
├── views/                  # 页面组件
│   ├── PluginsView.vue
│   ├── RunFlowView.vue
│   └── WorkflowEditor.vue # 工作流编辑器
│
├── App.vue                 # 主应用组件
└── main.ts                 # 应用入口
```

---

## 🎨 组件使用指南

### 工作流组件 (`components/workflow/`)

#### 快速导入（推荐）

```typescript
import {
  Canvas,
  NodePalette,
  NodeConfigPanel,
  Toolbar,
  StartNode,
  OutputNode,
  LLMNode,
  PythonNode,
  APINode,
  ConditionNode,
  LoopNode,
  LLMConfigForm,
  PythonCodeEditor,
  APIConfigForm,
} from "../components/workflow";
```

#### 组件列表

| 组件              | 用途                     |
| ----------------- | ------------------------ |
| `Canvas`          | 画布组件，集成 Vue Flow  |
| `NodePalette`     | 节点库面板               |
| `NodeConfigPanel` | 节点配置面板             |
| `Toolbar`         | 工具栏（保存/重置/执行） |

#### 节点组件 (`nodes/`)

| 组件            | 类型      | 配色 |
| --------------- | --------- | ---- |
| `StartNode`     | start     | 深蓝 |
| `OutputNode`    | output    | 深蓝 |
| `LLMNode`       | llm       | 绿色 |
| `PythonNode`    | python    | 橙色 |
| `APINode`       | api       | 蓝色 |
| `ConditionNode` | condition | 紫色 |
| `LoopNode`      | loop      | 紫色 |

#### 配置表单 (`forms/`)

| 组件               | 对应节点   |
| ------------------ | ---------- |
| `LLMConfigForm`    | LLMNode    |
| `PythonCodeEditor` | PythonNode |
| `APIConfigForm`    | APINode    |

---

## 🔧 状态管理

### Workflow Store (`stores/workflow.ts`)

```typescript
import { useWorkflowStore } from "../stores/workflow";

const store = useWorkflowStore();

// 状态
store.nodes; // 节点列表
store.edges; // 连线列表
store.selectedNodeId; // 选中的节点 ID
store.name; // 工作流名称

// Getters
store.selectedNode; // 选中的节点对象
store.canUndo; // 是否可以撤销
store.canRedo; // 是否可以重做

// Actions
store.addNode(node); // 添加节点
store.deleteNode(id); // 删除节点
store.updateNode(id, updates); // 更新节点
store.addEdge(edge); // 添加连线
store.deleteEdge(id); // 删除连线
store.selectNode(id); // 选中节点
store.undo(); // 撤销
store.redo(); // 重做
store.copySelectedNode(); // 复制选中节点
store.pasteNodes(); // 粘贴节点
store.toYAML(); // 转换为 YAML
store.saveToLocalStorage(); // 保存到 localStorage
store.loadFromLocalStorage(); // 从 localStorage 加载
store.reset(); // 重置工作流
```

---

## ⌨️ 快捷键

| 快捷键                      | 功能                |
| --------------------------- | ------------------- |
| Delete / Backspace          | 删除选中节点        |
| Ctrl + C                    | 复制选中节点        |
| Ctrl + V                    | 粘贴节点            |
| Ctrl + S                    | 保存到 localStorage |
| Ctrl + Z                    | 撤销                |
| Ctrl + Y / Ctrl + Shift + Z | 重做                |

---

## 🎨 设计规范

本项目使用 **Flow Design System (FDS) v1.0** 设计规范。

### CSS 变量

```css
--flow-color-primary    # 主色调（蓝）
--flow-color-success    # 成功色（绿）
--flow-color-warning    # 警告色（橙）
--flow-color-info       # 信息色（蓝）
--flow-color-purple     # 紫色
--flow-bg-page          # 页面背景
--flow-bg-card          # 卡片背景
--flow-bg-layer         # 层级背景
--flow-text-primary     # 主要文字
--flow-text-secondary   # 次要文字
--flow-text-title       # 标题文字
--flow-border-radius-lg # 大圆角
--flow-border-radius-md # 中圆角
--flow-border-radius-sm # 小圆角
```

---

## 📚 开发指南

### 添加新节点类型

1. 在 `components/workflow/nodes/` 创建新节点组件
2. 在 `components/workflow/nodes/index.ts` 导出
3. 在 `types/workflow.ts` 添加类型
4. 在 `utils/workflow-yaml.ts` 添加转换逻辑
5. 在 `NodePalette` 添加节点项

### 添加新配置表单

1. 在 `components/workflow/forms/` 创建表单组件
2. 在 `components/workflow/forms/index.ts` 导出
3. 在 `NodeConfigPanel` 中引用

---

## 🔗 相关文档

- [Vue 3 文档](https://cn.vuejs.org/)
- [Ant Design Vue 文档](https://antdv.com/)
- [Pinia 文档](https://pinia.vuejs.org/zh/)
- [Vue Flow 文档](https://vueflow.dev/)
