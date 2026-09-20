<template>
  <div class="palette-panel">
    <div class="palette-header">
      <div class="palette-title">
        <span class="icon">🧩</span>
        <span>组件库</span>
      </div>
      <a-input
        v-model:value="searchQuery"
        placeholder="搜索动作或插件..."
        allow-clear
        size="small"
        class="search-input"
      >
        <template #prefix><SearchOutlined /></template>
      </a-input>
    </div>

    <div class="palette-content">
      <div
        v-for="group in filteredGroups"
        :key="group.name"
        class="component-group"
      >
        <div class="group-title">
          <span>{{ group.icon }}</span>
          <span>{{ group.name }}</span>
          <span class="group-count">{{ group.items.length }}</span>
        </div>

        <div class="component-list">
          <div
            v-for="item in group.items"
            :key="item.type"
            class="component-card"
            draggable="true"
            @dragstart="onDragStart($event, item)"
            @click="emit('add-node', item)"
          >
            <div class="card-top">
              <span class="card-icon">{{ item.icon }}</span>
              <span class="card-label">{{ item.label }}</span>
              <a-button
                type="text"
                size="small"
                class="add-btn"
                title="添加到画布"
                @click.stop="emit('add-node', item)"
              >
                +
              </a-button>
            </div>
            <div class="card-type af-mono">{{ item.type }}</div>
            <div class="card-desc">{{ item.desc }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'

export interface ComponentItem {
  type: string
  label: string
  desc: string
  icon: string
  category: string
  defaultParams?: Record<string, unknown>
  defaultCheck?: { type: string; params: Record<string, unknown> }
}

const emit = defineEmits<{
  (e: 'add-node', item: ComponentItem): void
}>()

const searchQuery = ref('')

const COMPONENT_GROUPS = [
  {
    name: '基础与调试',
    icon: '⚡',
    items: [
      {
        type: 'core.log',
        label: '输出日志',
        desc: '在执行日志中记录调试信息',
        icon: '📝',
        category: 'core',
        defaultParams: { message: 'Processing flow step...' },
      },
      {
        type: 'dummy.echo',
        label: '数据回显',
        desc: '原样回显输入数据或构造结构化结果',
        icon: '📦',
        category: 'dummy',
        defaultParams: { status: 'ok', data: 'hello' },
      },
      {
        type: 'http.request',
        label: 'HTTP 请求',
        desc: '向外部 REST API 发起 GET/POST 请求',
        icon: '🌐',
        category: 'core',
        defaultParams: { url: 'https://api.example.com', method: 'GET' },
      },
      {
        type: 'shell.exec',
        label: '命令执行',
        desc: '执行本地 Bash 脚本或系统指令',
        icon: '💻',
        category: 'core',
        defaultParams: { command: 'echo "hello from shell"' },
      },
    ],
  },
  {
    name: 'AI 与智能抓取',
    icon: '🤖',
    items: [
      {
        type: 'ai.deepseek',
        label: 'DeepSeek 推理',
        desc: '调用 DeepSeek/LLM 进行摘要、分析或提取',
        icon: '🧠',
        category: 'ai',
        defaultParams: { prompt: '请精炼以下要点: {{input}}' },
      },
      {
        type: 'zhihu.fetch_hot',
        label: '知乎热榜采集',
        desc: '拉取知乎实时热榜话题与高赞回答',
        icon: '📑',
        category: 'scraper',
        defaultParams: { limit: 10 },
      },
      {
        type: 'openclaw.crawl',
        label: 'OpenClaw 爬虫',
        desc: '驱动 OpenClaw 采集目标网页正文',
        icon: '🕷️',
        category: 'scraper',
        defaultParams: { target_url: 'https://news.ycombinator.com' },
      },
    ],
  },
  {
    name: '桌面自动化 (RPA)',
    icon: '🖥️',
    items: [
      {
        type: 'desktop.click',
        label: '模拟鼠标点击',
        desc: '控制桌面鼠标在指定坐标点击',
        icon: '🖱️',
        category: 'desktop',
        defaultParams: { x: 500, y: 300 },
      },
      {
        type: 'desktop.screenshot',
        label: '屏幕截屏',
        desc: '截取当前桌面屏幕保存为产物',
        icon: '📸',
        category: 'desktop',
        defaultParams: { save_artifact: true },
      },
    ],
  },
  {
    name: '强断言校验 (Check)',
    icon: '🛡️',
    items: [
      {
        type: 'core.assert_truthy',
        label: '真值断言',
        desc: '强校验 Action 输出必须为真',
        icon: '✅',
        category: 'check',
        defaultParams: { value: '{{steps.prev.output.ok}}' },
      },
      {
        type: 'core.assert_status',
        label: '状态码断言',
        desc: '校验 HTTP 请求状态码为 200/201',
        icon: '🎯',
        category: 'check',
        defaultParams: { expected_status: 200 },
      },
    ],
  },
]

const filteredGroups = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return COMPONENT_GROUPS

  return COMPONENT_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter(
      (item) =>
        item.type.toLowerCase().includes(query) ||
        item.label.toLowerCase().includes(query) ||
        item.desc.toLowerCase().includes(query),
    ),
  })).filter((group) => group.items.length > 0)
})

const onDragStart = (event: DragEvent, item: ComponentItem) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/autoflow-node', JSON.stringify(item))
    event.dataTransfer.effectAllowed = 'copy'
  }
}
</script>

<style scoped>
.palette-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  overflow: hidden;
}

.palette-header {
  padding: 14px 16px 10px;
  border-bottom: 1px solid #f1f5f9;
}

.palette-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 650;
  color: #0f172a;
  margin-bottom: 10px;
}

.palette-title .icon {
  font-size: 16px;
}

.search-input {
  width: 100%;
}

.palette-content {
  flex: 1;
  padding: 12px 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.component-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.group-count {
  margin-left: auto;
  font-size: 10px;
  background: #f1f5f9;
  color: #94a3b8;
  padding: 1px 6px;
  border-radius: 999px;
}

.component-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.component-card {
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.2s;
}

.component-card:hover {
  background: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.08);
  transform: translateY(-1px);
}

.component-card:active {
  cursor: grabbing;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-icon {
  font-size: 13px;
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
}

.add-btn {
  padding: 0 4px;
  height: 20px;
  font-size: 14px;
  line-height: 1;
  color: #3b82f6;
  font-weight: bold;
}

.add-btn:hover {
  color: #1d4ed8;
  background: #eff6ff;
}

.card-type {
  font-size: 10.5px;
  color: #64748b;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  font-size: 10.5px;
  color: #94a3b8;
  margin-top: 2px;
  line-height: 1.3;
}
</style>
