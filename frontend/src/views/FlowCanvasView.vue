<template>
  <div class="canvas-studio">
    <!-- 顶部操作栏 -->
    <div class="studio-toolbar">
      <div class="toolbar-left">
        <div class="flow-meta">
          <div class="flow-name-row">
            <span class="flow-icon">⚡</span>
            <input
              v-model="flowName"
              class="flow-name-input"
              :placeholder="t('canvas.flowNamePlaceholder')"
              @change="syncCanvasToYaml"
            />
          </div>
          <input
            v-model="flowDesc"
            class="flow-desc-input"
            :placeholder="t('canvas.flowDescPlaceholder')"
            @change="syncCanvasToYaml"
          />
        </div>
      </div>

      <div class="toolbar-actions">
        <a-select
          v-model:value="selectedServerFlow"
          :placeholder="t('canvas.savedFlows')"
          style="width: 118px"
          size="small"
          allow-clear
          :dropdown-match-select-width="false"
          option-label-prop="label"
          :loading="loadingServerFlows"
          @change="handleSelectServerFlow"
        >
          <a-select-option
            v-for="item in serverFlows"
            :key="item.slug"
            :value="item.slug"
            :label="item.name"
          >
            {{ item.name }}{{ item.description ? ` — ${localizeFlowYaml(item.description, locale)}` : '' }}
          </a-select-option>
        </a-select>

        <a-select
          v-model:value="selectedExampleKey"
          :placeholder="t('canvas.presets')"
          style="width: 112px"
          size="small"
          @change="handleSelectExample"
        >
          <a-select-option
            v-for="(example, key) in FLOW_EXAMPLES"
            :key="key"
            :value="key"
          >
            {{ getFlowExampleLabel(example) }}
          </a-select-option>
        </a-select>

        <a-button
          size="small"
          :loading="savingServerFlow"
          @click="handleSaveServerFlow"
        >
          <template #icon><SaveOutlined /></template>
          {{ t('canvas.save') }}
        </a-button>

        <a-button size="small" @click="autoLayout">
          <template #icon><ApartmentOutlined /></template>
          {{ t('canvas.layout') }}
        </a-button>

        <a-button
          size="small"
          :type="showTimeline ? 'primary' : 'default'"
          :ghost="showTimeline"
          @click="showTimeline = !showTimeline"
        >
          <template #icon><BarChartOutlined /></template>
          {{ t('canvas.gantt') }}
        </a-button>

        <a-button
          size="small"
          @click="handleStepDebug"
        >
          <template #icon><BugOutlined /></template>
          {{ t('canvas.debug') }}
        </a-button>

        <a-button
          type="primary"
          size="small"
          :loading="store.loading"
          class="run-btn"
          @click="handleRunFlow"
        >
          <template #icon><CaretRightOutlined /></template>
          {{ t('canvas.run') }}
        </a-button>
      </div>
    </div>

    <!-- 三栏主体工作区 -->
    <div class="studio-body">
      <!-- 1. 左侧组件库 -->
      <div class="sider-left">
        <PalettePanel @add-node="addNodeFromPalette" />
      </div>

      <!-- 2. 中间 Vue Flow 可视化画布 -->
      <div
        class="canvas-center"
        @dragover.prevent="onDragOver"
        @drop="onDrop"
      >
        <div class="flow-container">
          <VueFlow
            v-model:nodes="nodes"
            v-model:edges="edges"
            :default-viewport="{ zoom: 1, x: 120, y: 40 }"
            :min-zoom="0.2"
            :max-zoom="3"
            :fit-view-on-init="true"
            @node-click="onNodeClick"
            @pane-click="onPaneClick"
            @connect="onConnect"
          >
            <Background :gap="20" color="#e2e8f0" />
            <Controls />

            <template #node-flowNode="customNodeProps">
              <FlowNode
                :id="customNodeProps.id"
                :data="customNodeProps.data"
                :selected="customNodeProps.selected"
              />
            </template>
          </VueFlow>
        </div>

        <!-- 底部甘特图/瀑布流时间轴 -->
        <div v-if="showTimeline" class="timeline-drawer">
          <ExecutionTimeline :run="currentRun" />
        </div>
      </div>

      <!-- 3. 右侧属性与代码配置 -->
      <div class="sider-right">
        <PropertyPanel
          :selected-step="currentSelectedStep"
          :selected-index="selectedStepIndex"
          :yaml-text="yamlCode"
          :flow-name="flowName"
          :cron-value="cronValue"
          :webhook-token-value="webhookTokenValue"
          @update-step="onStepUpdated"
          @update-id="onStepIdChanged"
          @delete-step="deleteStep"
          @update-yaml="onYamlEdited"
          @format-yaml="formatYaml"
          @cron-change="onCronChanged"
          @webhook-change="onWebhookChanged"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ApartmentOutlined,
  BarChartOutlined,
  BugOutlined,
  CaretRightOutlined,
  SaveOutlined,
} from '@ant-design/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import * as yaml from 'js-yaml'

import { getFlow, listFlows, saveFlow, type FlowRecord } from '../api/client'
import { useRunsStore } from '../stores/runs'
import {
  FLOW_EXAMPLES,
  getDefaultFlowYaml,
  getFlowExampleLabel,
} from '../constants/flow-examples'
import { localizeFlowYaml, useI18n } from '../i18n'
import type { FlowNodeData, FlowSpec, StepSpec } from '../types/flow'
import type { RunStepResult } from '../types/runs'
import type { ComponentItem } from '../components/canvas/PalettePanel.vue'

import FlowNode from '../components/canvas/FlowNode.vue'
import PalettePanel from '../components/canvas/PalettePanel.vue'
import PropertyPanel from '../components/canvas/PropertyPanel.vue'
import ExecutionTimeline from '../components/canvas/ExecutionTimeline.vue'

const { t, locale } = useI18n()
const router = useRouter()
const store = useRunsStore()
const { fitView } = useVueFlow()

const flowName = ref('my_workflow')
const flowDesc = ref(t('canvas.defaultFlowDesc'))
const cronValue = ref('')
const webhookTokenValue = ref('')
const flowHooks = ref<FlowSpec['hooks']>(undefined)
const flowTrigger = ref<FlowSpec['trigger']>(undefined)
const selectedExampleKey = ref<string>()
const serverFlows = ref<FlowRecord[]>([])
const selectedServerFlow = ref<string>()
const loadingServerFlows = ref(false)
const savingServerFlow = ref(false)
const showTimeline = ref(true)

const selectedNodeId = ref<string | null>(null)
const yamlCode = ref(getDefaultFlowYaml())

const nodes = ref<any[]>([])
const edges = ref<any[]>([])

const currentRun = computed(() => store.currentRun)

// 当前选中的步骤
const selectedStepIndex = computed(() => {
  if (!selectedNodeId.value) return -1
  return nodes.value.findIndex((n) => n.id === selectedNodeId.value)
})

const currentSelectedStep = computed<StepSpec | null>(() => {
  const idx = selectedStepIndex.value
  if (idx === -1) return null
  return nodes.value[idx]?.data?.step ?? null
})

// ---------------- 画布与 YAML 双向同步 ----------------

/** 将 YAML 代码无损解析并投影到画布 */
const parseYamlToCanvas = (rawYaml: string, preserveState = false) => {
  try {
    const doc = yaml.load(rawYaml) as FlowSpec
    if (!doc || !Array.isArray(doc.steps)) return

    const prevNodeMap = new Map<string, any>(
      preserveState ? nodes.value.map((n) => [n.id, n]) : [],
    )

    flowName.value = doc.name || 'unnamed_flow'
    if (doc.description !== undefined) {
      flowDesc.value = doc.description
    } else if (!preserveState) {
      flowDesc.value = ''
    }
    cronValue.value = doc.cron || doc.trigger?.cron || ''
    webhookTokenValue.value = doc.trigger?.webhook_token || ''
    flowHooks.value = doc.hooks
    flowTrigger.value = doc.trigger ? { ...doc.trigger } : undefined

    const newNodes: any[] = []
    const newEdges: any[] = []

    const startX = 180
    const startY = 40
    const nodeGapY = 160

    doc.steps.forEach((step: StepSpec, index: number) => {
      const prevNode = prevNodeMap.get(step.id)
      newNodes.push({
        id: step.id,
        type: 'flowNode',
        position: prevNode?.position ?? { x: startX, y: startY + index * nodeGapY },
        data: {
          step,
          index,
          status: prevNode?.data?.status ?? 'idle',
          duration_ms: prevNode?.data?.duration_ms,
          check_passed: prevNode?.data?.check_passed,
          error: prevNode?.data?.error,
        } as FlowNodeData,
      })

      // 默认线性连线或按 depends_on 连线
      if (step.depends_on && step.depends_on.length > 0) {
        step.depends_on.forEach((depId: string) => {
          newEdges.push({
            id: `edge-${depId}-${step.id}`,
            source: depId,
            target: step.id,
            animated: true,
            style: { stroke: '#3b82f6', strokeWidth: 2 },
          })
        })
      } else if (index > 0) {
        const prevId = doc.steps[index - 1].id
        newEdges.push({
          id: `edge-${prevId}-${step.id}`,
          source: prevId,
          target: step.id,
          animated: true,
          style: { stroke: '#3b82f6', strokeWidth: 2 },
        })
      }
    })

    nodes.value = newNodes
    edges.value = newEdges

    if (newNodes.length > 0 && !selectedNodeId.value) {
      selectedNodeId.value = newNodes[0].id
    }
  } catch (err) {
    console.warn('YAML parse error during sync:', err)
  }
}

/** 将画布节点序列化回 YAML 代码 */
const syncCanvasToYaml = () => {
  const validIds = new Set(nodes.value.map((n) => n.id))
  const steps: StepSpec[] = nodes.value.map((n) => {
    const incomingDeps = Array.from(
      new Set(
        edges.value
          .filter(
            (e) =>
              e.target === n.id &&
              e.source &&
              e.source !== n.id &&
              validIds.has(e.source),
          )
          .map((e) => String(e.source)),
      ),
    )
    const stepCopy: StepSpec = { ...n.data.step }
    if (incomingDeps.length > 0) {
      stepCopy.depends_on = incomingDeps
      n.data.step.depends_on = incomingDeps
    } else {
      delete stepCopy.depends_on
      delete n.data.step.depends_on
    }
    return stepCopy
  })

  const doc: FlowSpec = {
    version: '1',
    name: flowName.value,
    description: flowDesc.value || undefined,
    steps,
  }

  if (cronValue.value) {
    doc.cron = cronValue.value
  }
  if (webhookTokenValue.value) {
    doc.trigger = {
      ...(flowTrigger.value || {}),
      webhook_enabled: true,
      webhook_token: webhookTokenValue.value,
    }
  } else if (flowTrigger.value) {
    doc.trigger = { ...flowTrigger.value }
  }
  if (flowHooks.value) {
    doc.hooks = flowHooks.value
  }

  const lines = yamlCode.value.split('\n')
  const headerCommentLines: string[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('#')) {
      headerCommentLines.push(line)
    } else if (trimmed === '') {
      if (headerCommentLines.length > 0) headerCommentLines.push(line)
    } else {
      break
    }
  }
  const headerPrefix = headerCommentLines.join('\n').trim()
  const dumped = yaml.dump(doc, { indent: 2, noRefs: true, lineWidth: -1 })
  yamlCode.value = headerPrefix ? `${headerPrefix}\n\n${dumped}` : dumped
}

/** 格式化当前 YAML */
const formatYaml = () => {
  try {
    const doc = yaml.load(yamlCode.value)
    yamlCode.value = yaml.dump(doc, { indent: 2, noRefs: true, lineWidth: -1 })
    message.success(t('canvas.yamlFormatted'))
  } catch {
    message.error(t('canvas.yamlFormatError'))
  }
}

const onYamlEdited = (newYaml: string) => {
  yamlCode.value = newYaml
  parseYamlToCanvas(newYaml, true)
}

// ---------------- 节点交互与拖拽 ----------------

const onNodeClick = (event: any) => {
  selectedNodeId.value = event.node.id
}

const onPaneClick = () => {
  selectedNodeId.value = null
}

const onConnect = (connection: any) => {
  if (
    !connection.source ||
    !connection.target ||
    connection.source === connection.target
  ) {
    return
  }
  const exists = edges.value.some(
    (e) => e.source === connection.source && e.target === connection.target,
  )
  if (!exists) {
    edges.value.push({
      id: `edge-${connection.source}-${connection.target}`,
      ...connection,
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
    })
  }
  const targetNode = nodes.value.find((n) => n.id === connection.target)
  if (targetNode) {
    const deps = new Set(targetNode.data.step.depends_on || [])
    deps.add(String(connection.source))
    targetNode.data.step.depends_on = Array.from(deps)
  }
  syncCanvasToYaml()
}

const addNodeFromPalette = (item: ComponentItem) => {
  if (item.category === 'check') {
    const targetNode =
      nodes.value.find((n) => n.id === selectedNodeId.value) ||
      nodes.value[nodes.value.length - 1]
    if (targetNode) {
      targetNode.data.step.check = {
        type: item.type,
        params: item.defaultParams ? { ...item.defaultParams } : { value: true },
      }
      selectedNodeId.value = targetNode.id
      syncCanvasToYaml()
      message.success(t('canvas.checkAttached', { id: targetNode.id, label: item.label }))
      return
    }
  }

  const count = nodes.value.length
  const stepId = `step_${count + 1}_${item.type.split('.').pop()}`
  const lastNode = nodes.value[nodes.value.length - 1]

  const newStep: StepSpec =
    item.category === 'check'
      ? {
          id: stepId,
          name: item.label,
          action: {
            type: 'core.log',
            params: { message: t('canvas.checkStepMessage', { label: item.label }) },
          },
          check: {
            type: item.type,
            params: item.defaultParams ? { ...item.defaultParams } : { value: true },
          },
        }
      : {
          id: stepId,
          name: item.label,
          action: {
            type: item.type,
            params: item.defaultParams ? { ...item.defaultParams } : {},
          },
        }

  const newNode = {
    id: stepId,
    type: 'flowNode',
    position: {
      x: 180,
      y: lastNode ? lastNode.position.y + 160 : 40,
    },
    data: {
      step: newStep,
      index: count,
      status: 'idle',
    } as FlowNodeData,
  }

  nodes.value.push(newNode)

  if (lastNode) {
    edges.value.push({
      id: `edge-${lastNode.id}-${stepId}`,
      source: lastNode.id,
      target: stepId,
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
    })
  }

  selectedNodeId.value = stepId
  syncCanvasToYaml()
  message.success(t('canvas.stepAdded', { label: item.label }))
}

const onDragOver = (e: DragEvent) => {
  e.dataTransfer!.dropEffect = 'copy'
}

const onDrop = (e: DragEvent) => {
  const raw = e.dataTransfer?.getData('application/autoflow-node')
  if (!raw) return
  try {
    const item: ComponentItem = JSON.parse(raw)
    addNodeFromPalette(item)
  } catch (err) {
    console.error('Drop node error:', err)
  }
}

const onStepUpdated = (updatedStep: StepSpec) => {
  const node = nodes.value.find((n) => n.id === updatedStep.id)
  if (node) {
    node.data.step = { ...updatedStep }
    syncCanvasToYaml()
  }
}

const onStepIdChanged = (oldId: string, newId: string) => {
  const trimmed = newId.trim()
  if (!trimmed || trimmed === oldId) return
  if (nodes.value.some((n) => n.id === trimmed && n.id !== oldId)) return
  const node = nodes.value.find((n) => n.id === oldId)
  if (!node) return
  node.id = trimmed
  node.data.step.id = trimmed

  // 更新连线关联与下游 depends_on
  edges.value.forEach((edge) => {
    if (edge.source === oldId) edge.source = trimmed
    if (edge.target === oldId) edge.target = trimmed
    edge.id = `edge-${edge.source}-${edge.target}`
  })
  nodes.value.forEach((n) => {
    if (Array.isArray(n.data.step.depends_on)) {
      n.data.step.depends_on = n.data.step.depends_on.map((dep: string) =>
        dep === oldId ? trimmed : dep,
      )
    }
  })

  selectedNodeId.value = trimmed
  syncCanvasToYaml()
}

const deleteStep = (stepId: string) => {
  nodes.value = nodes.value.filter((n) => n.id !== stepId)
  edges.value = edges.value.filter((e) => e.source !== stepId && e.target !== stepId)
  // 重新编号并清理下游 depends_on
  nodes.value.forEach((n, idx) => {
    n.data.index = idx
    if (Array.isArray(n.data.step.depends_on)) {
      const filtered = n.data.step.depends_on.filter((dep: string) => dep !== stepId)
      if (filtered.length > 0) {
        n.data.step.depends_on = filtered
      } else {
        delete n.data.step.depends_on
      }
    }
  })
  selectedNodeId.value = nodes.value[0]?.id || null
  syncCanvasToYaml()
  message.info(t('canvas.stepDeleted'))
}

const autoLayout = () => {
  const startX = 180
  const startY = 40
  const gapY = 160

  nodes.value.forEach((node, idx) => {
    node.position = { x: startX, y: startY + idx * gapY }
  })
  setTimeout(() => fitView({ padding: 0.2 }), 50)
}

const onCronChanged = (expr: string) => {
  cronValue.value = expr
  syncCanvasToYaml()
}

const onWebhookChanged = (token: string) => {
  webhookTokenValue.value = token.trim()
  if (!webhookTokenValue.value && flowTrigger.value) {
    delete flowTrigger.value.webhook_token
    flowTrigger.value.webhook_enabled = false
    if (!flowTrigger.value.cron) {
      flowTrigger.value = undefined
    }
  }
  syncCanvasToYaml()
}

const handleSelectExample = (key: string) => {
  const ex = FLOW_EXAMPLES[key as keyof typeof FLOW_EXAMPLES]
  if (!ex) return
  selectedServerFlow.value = undefined
  store.currentRun = null
  const localizedYaml = localizeFlowYaml(ex.yaml, locale.value)
  yamlCode.value = localizedYaml
  parseYamlToCanvas(localizedYaml)
  setTimeout(() => fitView({ padding: 0.2 }), 100)
}

const loadServerFlows = async () => {
  loadingServerFlows.value = true
  try {
    serverFlows.value = await listFlows()
  } catch {
    // 忽略加载异常，保持本地示例可用
  } finally {
    loadingServerFlows.value = false
  }
}

const handleSelectServerFlow = async (slug?: string) => {
  if (!slug) return
  try {
    const record = await getFlow(slug)
    selectedExampleKey.value = undefined
    store.currentRun = null
    const localizedYaml = localizeFlowYaml(record.flow_yaml, locale.value)
    yamlCode.value = localizedYaml
    parseYamlToCanvas(localizedYaml)
    setTimeout(() => fitView({ padding: 0.2 }), 100)
    message.destroy()
    message.success(t('canvas.flowLoaded', { name: record.name }))
  } catch (err: any) {
    message.error(t('canvas.flowLoadError', { msg: err?.message || err }))
  }
}

const handleSaveServerFlow = async () => {
  syncCanvasToYaml()
  const rawSlug =
    selectedServerFlow.value ||
    flowName.value.trim().replace(/[^a-zA-Z0-9_-]/g, '_') ||
    'my_workflow'
  savingServerFlow.value = true
  try {
    const saved = await saveFlow(rawSlug, yamlCode.value)
    selectedServerFlow.value = saved.slug
    await loadServerFlows()
    message.destroy()
    message.success(t('canvas.flowSaved', { name: saved.name || saved.slug }))
  } catch (err: any) {
    message.error(t('canvas.flowSaveError', { msg: err?.message || err }))
  } finally {
    savingServerFlow.value = false
  }
}

// ---------------- 执行与状态光效反馈 ----------------

const handleRunFlow = async () => {
  syncCanvasToYaml()

  // 重置节点状态为运行呼吸态
  nodes.value.forEach((n) => {
    n.data.status = 'running'
    n.data.duration_ms = undefined
    n.data.check_passed = null
    n.data.error = null
  })

  try {
    const runResult = await store.executeFlow(yamlCode.value, {}, {})
    showTimeline.value = true

    // 执行完成，回填每个步骤的执行状态与光效
    if (runResult && runResult.steps) {
      const stepMap = new Map<string, RunStepResult>(
        runResult.steps.map((s: RunStepResult) => [s.step_id, s]),
      )
      nodes.value.forEach((node) => {
        const res = stepMap.get(node.id)
        if (res) {
          node.data.status = res.status
          node.data.duration_ms = res.duration_ms
          node.data.check_passed = res.check_passed
          node.data.error = res.error
        } else {
          node.data.status = 'skipped'
        }
      })
    }
    message.destroy()
    message.success(t('canvas.runSuccess'))
  } catch (err: any) {
    nodes.value.forEach((n) => {
      n.data.status = 'failed'
    })
    message.destroy()
    message.error(t('canvas.runError', { msg: err.message || err }))
  }
}

const handleStepDebug = () => {
  message.destroy()
  syncCanvasToYaml()
  sessionStorage.setItem('autoflow_debug_yaml', yamlCode.value)
  router.push('/debug')
}

// 监听运行状态，同步光效
watch(
  () => store.currentRun,
  (run) => {
    if (!run || !run.steps) return
    const stepMap = new Map<string, RunStepResult>(
      run.steps.map((s: RunStepResult) => [s.step_id, s]),
    )
    nodes.value.forEach((node) => {
      const res = stepMap.get(node.id)
      if (res) {
        node.data.status = res.status
        node.data.duration_ms = res.duration_ms
        node.data.check_passed = res.check_passed
        node.data.error = res.error
      }
    })
  },
  { deep: true },
)

watch(locale, (newLocale) => {
  message.destroy()
  if (flowDesc.value) {
    flowDesc.value = localizeFlowYaml(flowDesc.value, newLocale)
  }
  yamlCode.value = localizeFlowYaml(yamlCode.value, newLocale)
  parseYamlToCanvas(yamlCode.value, true)
})

onMounted(() => {
  const pendingYaml = sessionStorage.getItem('autoflow_canvas_yaml')
  if (pendingYaml) {
    sessionStorage.removeItem('autoflow_canvas_yaml')
    store.currentRun = null
    yamlCode.value = localizeFlowYaml(pendingYaml, locale.value)
  }
  parseYamlToCanvas(yamlCode.value)
  loadServerFlows()
  setTimeout(() => fitView({ padding: 0.2 }), 150)
})
</script>

<style scoped>
.canvas-studio {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--flow-header-height));
  margin: -24px;
  background: #f8fafc;
  overflow: hidden;
}

/* 顶部操作条 */
.studio-toolbar {
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 14px;
  flex: none;
  z-index: 10;
  overflow: hidden;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1 1 auto;
}

.flow-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.flow-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.flow-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.flow-name-input {
  border: none;
  outline: none;
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
  background: transparent;
  padding: 0;
  width: 155px;
  text-overflow: ellipsis;
}

.flow-name-input:focus {
  border-bottom: 1px solid #3b82f6;
}

.flow-desc-input {
  border: none;
  outline: none;
  font-size: 11px;
  color: #64748b;
  background: transparent;
  padding: 0;
  width: 175px;
  text-overflow: ellipsis;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.toolbar-actions :deep(.ant-btn) {
  white-space: nowrap;
  flex-shrink: 0;
  padding: 0 9px;
  font-size: 12px;
}

.run-btn {
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35);
}

/* 三栏布局 */
.studio-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.sider-left {
  width: 236px;
  flex: none;
  height: 100%;
}

.canvas-center {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  background: #f1f5f9;
  min-width: 0;
}

.flow-container {
  flex: 1;
  position: relative;
  min-height: 0;
}

.timeline-drawer {
  flex: none;
  max-height: 220px;
  overflow-y: auto;
  z-index: 5;
}

.sider-right {
  width: 340px;
  flex: none;
  height: 100%;
}

@media (max-width: 1100px) {
  .sider-left {
    width: 205px;
  }

  .sider-right {
    width: 290px;
  }
}
</style>
