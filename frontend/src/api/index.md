---
title: API 接口层
description: API 接口层文档
keywords: [API, api, 接口, 请求]
version: "1.0"
---

# API 接口层

本目录存放所有与后端通信的 API 接口定义。

## 📁 文件结构

```
api/
└── index.ts          # 统一的 API 请求入口
```

## 🔧 使用指南

### 添加新 API

在 `index.ts` 中添加新的 API 请求函数：

```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
})

export async function getSomething() {
  const response = await apiClient.get('/something')
  return response.data
}

export async function createSomething(data: any) {
  const response = await apiClient.post('/something', data)
  return response.data
}
```

## 📋 命名规范

- 请求函数使用 `getXxx` / `createXxx` / `updateXxx` / `deleteXxx` 格式
- TypeScript 类型定义放在 `types/` 目录
