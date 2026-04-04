# Vue 3 TypeScript 字符串字面量类型窄化

**Extracted:** 2026-04-04
**Context:** Vue 3 + TypeScript 项目中操作 string 字面量联合类型时的常见编译错误修复

## Problem

以下场景会产生 `vue-tsc` 编译错误：
1. `Map<'a'|'b', V>.get(string)` — key 类型不匹配
2. `{ type: "any" }` 传给 `{ type: PortDataType }` — 推断为宽泛 `string` 而非字面量
3. `Object.entries(record)` 返回 `[string, unknown][]` — value 失去类型信息
4. 回调参数 `(e) =>` 隐式 `any`

## Solution

| 场景 | 修复方式 |
|------|---------|
| `Map<Union, V>` 查询 | 创建时 cast key — `[t.type as string, t.color]` |
| 字符串字面量赋给联合类型字段 | `"any" as const` |
| `Object.entries` value 类型丢失 | `Object.entries(obj) as [string, MyType][]` |
| map/filter 回调参数 | `(e: EdgeData) => ...` 显式标注 |

## Example

```ts
// 1. Map key cast
const map = new Map(templates.map(t => [t.type as string, t.color]));
const color = map.get(someStringVar); // OK

// 2. as const — 字符串字面量保持类型
const port = { id: "x", name: "X", type: "any" as const, required: false };
// type: "any" 而非 string，满足 PortDataType 约束

// 3. Object.entries 类型断言
for (const [id, node] of Object.entries(workflow.nodes) as [string, NodeData][]) {
  const typed = { ...node, id: newId }; // node 现在是 NodeData 而非 unknown
}

// 4. 回调参数类型
const newEdges = edges.map((e: EdgeData) => ({ ...e, id: crypto.randomUUID() }));
```

## When to Use

- `vue-tsc --noEmit` 出现 `string is not assignable to 'a' | 'b' | 'c'` 类型错误
- 使用 `Map<NodeType, ...>` 等带联合类型 key 的 Map 时
- Pinia store 中用 `Object.entries` 遍历 `Record<string, KnownType>` 时
- 内联对象字面量传给强类型 interface 字段时
