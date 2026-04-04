# Ant Design Vue 深色 Modal / Drawer 主题覆盖

**Extracted:** 2026-04-04
**Context:** AutoFlow 使用 `#0f172a` / `#1e293b` 深色主题，AntD Vue 组件默认白色，需要 `:deep()` 覆盖

## Problem

AntD Vue Modal、Drawer、Select、Input 等组件的背景色、标题、关闭按钮都是浅色。
普通 scoped CSS 无法穿透 AntD 内部 DOM，需要 `:deep()` 选择器。

## Solution

在组件的 `<style scoped>` 中用 `:deep()` 穿透，给 Modal 加 class 以缩小选择器范围。

## Example

### Modal

```vue
<a-modal class="dark-modal" ...>

<style scoped>
.dark-modal :deep(.ant-modal-content)  { background: #0f172a; border: 1px solid #334155; }
.dark-modal :deep(.ant-modal-header)   { background: #0f172a; border-bottom: 1px solid #334155; }
.dark-modal :deep(.ant-modal-title)    { color: #e2e8f0; }
.dark-modal :deep(.ant-modal-close)    { color: #64748b; }
.dark-modal :deep(.ant-modal-close:hover) { color: #e2e8f0; background: rgba(255,255,255,0.08); }

/* 内部输入框 */
.dark-modal :deep(.ant-input)          { background: #1e293b; border-color: #334155; color: #e2e8f0; }
.dark-modal :deep(.ant-input::placeholder) { color: #64748b; }
.dark-modal :deep(.ant-input:focus),
.dark-modal :deep(.ant-input:hover)    { border-color: #6366f1; }
</style>
```

### Drawer

```vue
<style scoped>
:deep(.ant-drawer-content) { background: #1e293b; box-shadow: -8px 0 24px rgba(0,0,0,0.4); }
:deep(.ant-drawer-body)    { background: #1e293b; padding: 0; }
:deep(.ant-drawer-header)  { background: #1e293b; border-bottom: 1px solid #334155; }
:deep(.ant-drawer-close)   { color: #64748b; }
:deep(.ant-drawer-close:hover) { color: #e2e8f0; background: rgba(255,255,255,0.08); }
</style>
```

### Select / InputNumber（在深色容器内）

```css
:deep(.ant-select-selector)         { background: #1e293b !important; border-color: #334155 !important; }
:deep(.ant-select-selection-item)   { color: #e2e8f0; }
:deep(.ant-input-number)            { background: #1e293b; border-color: #334155; color: #e2e8f0; }
```

## AutoFlow 色板速查

| 用途 | 颜色 |
|------|------|
| 页面背景 | `#0f172a` |
| 卡片/面板背景 | `#1e293b` |
| 边框 | `#334155` |
| 主文字 | `#e2e8f0` |
| 次要文字 | `#94a3b8` |
| 禁用/placeholder | `#64748b` |
| 主色（Indigo） | `#6366f1` |

## When to Use

- 在 AutoFlow 中新增使用 AntD Modal / Drawer / Select 的组件
- 出现白色背景"穿帮"时
- 优先用 scoped `:deep()` 而非全局 CSS，避免污染其他组件
