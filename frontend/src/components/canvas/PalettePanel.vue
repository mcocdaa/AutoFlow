<template>
  <div class="palette-panel">
    <div class="palette-header">
      <div class="palette-title">
        <span class="icon">🧩</span>
        <span>{{ t('palette.title') }}</span>
      </div>
      <a-input
        v-model:value="searchQuery"
        :placeholder="t('palette.searchPlaceholder')"
        allow-clear
        size="small"
        class="search-input"
      >
        <template #prefix><SearchOutlined /></template>
      </a-input>
    </div>

    <div class="palette-content">
      <a-empty
        v-if="filteredGroups.length === 0"
        :description="t('common.noMatch')"
        style="margin: 32px 0"
      />
      <div
        v-for="group in filteredGroups"
        :key="group.id"
        class="component-group"
      >
        <div class="group-title">
          <span>{{ group.icon }}</span>
          <span>{{ group.title }}</span>
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
                :title="t('palette.addToCanvas')"
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
import { computed, onMounted, ref } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { getPluginCatalog, type PluginCatalogItem } from '../../api/client'
import { COMPONENT_I18N, useI18n } from '../../i18n'

const { locale, t } = useI18n()

export interface ComponentItem {
  type: string
  label: string
  desc: string
  icon: string
  category: string
  kind?: 'action' | 'check'
  defaultParams?: Record<string, unknown>
  defaultCheck?: { type: string; params: Record<string, unknown> }
}

type GroupId = 'core' | 'ai' | 'desktop' | 'check'

interface ComponentGroup {
  id: GroupId
  icon: string
  items: ComponentItem[]
}

const emit = defineEmits<{
  (e: 'add-node', item: ComponentItem): void
}>()

const searchQuery = ref('')

const DEFAULT_COMPONENT_GROUPS: ComponentGroup[] = [
  {
    id: 'core',
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
        defaultParams: { message: 'hello' },
      },
      {
        type: 'openclaw.http_request',
        label: 'HTTP 请求',
        desc: '向外部 REST API 发起 GET/POST 请求',
        icon: '🌐',
        category: 'core',
        defaultParams: { url: 'https://api.example.com', method: 'GET' },
      },
      {
        type: 'openclaw.exec',
        label: '命令执行',
        desc: '执行本地 Bash 脚本或系统指令',
        icon: '💻',
        category: 'core',
        defaultParams: { command: 'echo "hello from shell"' },
      },
    ],
  },
  {
    id: 'ai',
    icon: '🤖',
    items: [
      {
        type: 'ai.deepseek_summarize',
        label: 'DeepSeek 推理',
        desc: '调用大模型进行智能摘要与信息提取',
        icon: '🧠',
        category: 'ai',
        defaultParams: { input: '请精炼以下要点: {{input}}', dry_run: true },
      },
      {
        type: 'zhihu.fetch_answer',
        label: '知乎回答采集',
        desc: '拉取知乎指定问题回答正文内容',
        icon: '📑',
        category: 'scraper',
        defaultParams: {
          url: 'https://www.zhihu.com/question/784489052/answer/1946200783080125276',
          dry_run: true,
        },
      },
      {
        type: 'openclaw.knowflow_record',
        label: 'KnowFlow 归档',
        desc: '将流程结果沉淀至 KnowFlow 知识库',
        icon: '🕷️',
        category: 'scraper',
        defaultParams: { name: 'digest_report', project_id: 'default' },
      },
    ],
  },
  {
    id: 'desktop',
    icon: '🖥️',
    items: [
      {
        type: 'desktop.click',
        label: '模拟鼠标点击',
        desc: '控制桌面鼠标在指定坐标点击',
        icon: '🖱️',
        category: 'desktop',
        defaultParams: { x: 500, y: 300, dry_run: true },
      },
      {
        type: 'desktop.screenshot',
        label: '屏幕截屏',
        desc: '截取当前桌面屏幕保存为产物',
        icon: '📸',
        category: 'desktop',
        defaultParams: { name: 'screenshot.png', dry_run: true },
      },
    ],
  },
  {
    id: 'check',
    icon: '🛡️',
    items: [
      {
        type: 'core.assert_truthy',
        label: '真值断言',
        desc: '强校验 Action 输出必须为真',
        icon: '✅',
        category: 'check',
        defaultParams: { value: true },
      },
      {
        type: 'core.assert_status',
        label: '状态码断言',
        desc: '校验 HTTP 请求状态码为 200/201',
        icon: '🎯',
        category: 'check',
        defaultParams: { expected_status: 200 },
      },
      {
        type: 'core.assert_equals',
        label: '相等断言',
        desc: '强校验输出或字段等于期望值',
        icon: '⚖️',
        category: 'check',
        defaultParams: { actual: '{{input}}', expected: 'ok' },
      },
      {
        type: 'text.contains',
        label: '文本包含断言',
        desc: '校验输出文本包含指定关键字',
        icon: '🔍',
        category: 'check',
        defaultParams: { needle: 'ok' },
      },
      {
        type: 'core.always_true',
        label: '恒真断言',
        desc: '始终通过的占位校验断言',
        icon: '🟢',
        category: 'check',
        defaultParams: {},
      },
    ],
  },
]

const componentGroups = ref<ComponentGroup[]>(
  DEFAULT_COMPONENT_GROUPS.map((g) => ({
    ...g,
    items: g.items.map((item) => ({ ...item })),
  })),
)

function resolveGroupId(item: PluginCatalogItem): GroupId {
  if (item.kind === 'check' || item.category === 'check') {
    return 'check'
  }
  if (item.category === 'desktop' || item.type.startsWith('desktop.')) {
    return 'desktop'
  }
  if (
    item.category === 'ai' ||
    item.category === 'scraper' ||
    item.type.startsWith('ai.') ||
    item.type.startsWith('zhihu.')
  ) {
    return 'ai'
  }
  return 'core'
}

function localizeItem(item: ComponentItem): ComponentItem {
  const i18nMeta = COMPONENT_I18N[item.type]?.[locale.value]
  const defaultParams =
    locale.value === 'en' && item.type === 'ai.deepseek_summarize'
      ? { ...item.defaultParams, input: 'Summarize the following points: {{input}}' }
      : item.defaultParams
  if (i18nMeta) {
    return {
      ...item,
      label: i18nMeta.label,
      desc: i18nMeta.desc,
      defaultParams,
    }
  }
  if (locale.value === 'en') {
    return {
      ...item,
      desc:
        item.kind === 'check' || item.category === 'check'
          ? t('palette.dynamicCheckDesc', { type: item.type })
          : t('palette.dynamicActionDesc', { type: item.type }),
      defaultParams,
    }
  }
  return item
}

const loadPluginCatalog = async () => {
  try {
    const res = await getPluginCatalog()
    const groups = componentGroups.value.map((g) => ({
      ...g,
      items: [...g.items],
    }))
    const existingTypes = new Set<string>()
    groups.forEach((g) => g.items.forEach((i) => existingTypes.add(i.type)))

    const catalogItems: PluginCatalogItem[] = [...(res.catalog || [])]
    for (const actionType of res.actions || []) {
      if (!catalogItems.some((c) => c.type === actionType)) {
        catalogItems.push({
          type: actionType,
          label: actionType.split('.').pop() || actionType,
          desc: `动态注册动作插件: ${actionType}`,
          icon: '🔌',
          category: actionType.split('.')[0] || 'core',
          kind: 'action',
          defaultParams: {},
        })
      }
    }
    for (const checkType of res.checks || []) {
      if (!catalogItems.some((c) => c.type === checkType)) {
        catalogItems.push({
          type: checkType,
          label: checkType.split('.').pop() || checkType,
          desc: `动态注册校验断言: ${checkType}`,
          icon: '🛡️',
          category: 'check',
          kind: 'check',
          defaultParams: {},
        })
      }
    }

    for (const catItem of catalogItems) {
      if (existingTypes.has(catItem.type)) continue
      const targetGroupId = resolveGroupId(catItem)
      let group = groups.find((g) => g.id === targetGroupId)
      if (!group) {
        group = { id: targetGroupId, icon: '🔌', items: [] }
        groups.push(group)
      }
      group.items.push({
        type: catItem.type,
        label: catItem.label,
        desc: catItem.desc,
        icon: catItem.icon || '🔌',
        category: catItem.kind === 'check' ? 'check' : catItem.category,
        kind: catItem.kind,
        defaultParams: catItem.defaultParams || {},
      })
      existingTypes.add(catItem.type)
    }

    componentGroups.value = groups
  } catch {
    // 离线或接口不可用时回退至默认组件列表
  }
}

onMounted(() => {
  loadPluginCatalog()
})

const filteredGroups = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const localized = componentGroups.value.map((group) => ({
    ...group,
    title: t(`palette.group.${group.id}`),
    items: group.items.map(localizeItem),
  }))

  if (!query) return localized

  return localized
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) =>
          item.type.toLowerCase().includes(query) ||
          item.label.toLowerCase().includes(query) ||
          item.desc.toLowerCase().includes(query),
      ),
    }))
    .filter((group) => group.items.length > 0)
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
