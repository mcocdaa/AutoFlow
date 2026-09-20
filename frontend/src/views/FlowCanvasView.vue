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
              placeholder="Flow 名称"
              @change="syncCanvasToYaml"
            />
          </div>
          <input
            v-model="flowDesc"
            class="flow-desc-input"
            placeholder="填写工作流简短说明..."
            @change="syncCanvasToYaml"
          />
        </div>
      </div>

      <div class="toolbar-actions">
        <a-select
          v-model:value="selectedExampleKey"
          placeholder="加载预设示例"
          style="width: 170px"
          size="small"
          @change="handleSelectExample"
        >
          <a-select-option
            v-for="(example, key) in FLOW_EXAMPLES"
            :key="key"
            :value="key"
          >
            {{ example.label }}
          </a-select-option>
        </a-select>

        <a-button size="small" @click="autoLayout">
          <template #icon><ApartmentOutlined /></template>
          自动排版
        </a-button>

        <a-button
          size="small"
          :type="showTimeline ? 'primary' : 'default'"
          :ghost="showTimeline"
          @click="showTimeline = !showTimeline"
        >
          <template #icon><BarChartOutlined /></template>
          甘特图
        </a-button>

        <a-button
          size="small"
          @click="handleStepDebug"
        >
          <template #icon><BugOutlined /></template>
          单步调试
        </a-button>

        <a-button
          type="primary"
          size="small"
          :loading="store.loading"
          class="run-btn"
          @click="handleRunFlow"
        >
          <template #icon><CaretRightOutlined /></template>
          一键执行
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
} from '@ant-design/icons-vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import * as yaml from 'js-yaml'

import { useRunsStore } from '../stores/runs'
import { DEFAULT_FLOW_YAML, FLOW_EXAMPLES } from '../constants/flow-examples'
import type { FlowNodeData, FlowSpec, StepSpec } from '../types/flow'
import type { RunStepResult } from '../types/runs'
import type { ComponentItem } from '../components/canvas/PalettePanel.vue'

import FlowNode from '../components/canvas/FlowNode.vue'
import PalettePanel from '../components/canvas/PalettePanel.vue'
import PropertyPanel from '../components/canvas/PropertyPanel.vue'
import ExecutionTimeline from '../components/canvas/ExecutionTimeline.vue'

const router = useRouter()
const store = useRunsStore()
const { fitView } = useVueFlow()

const flowName = ref('my_workflow')
const flowDesc = ref('AutoFlow 自动化流程')
const cronValue = ref('')
const webhookTokenValue = ref('token-123')
const selectedExampleKey = ref<string>()
const showTimeline = ref(true)

const selectedNodeId = ref<string | null>(null)
const yamlCode = ref(DEFAULT_FLOW_YAML)

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
const parseYamlToCanvas = (rawYaml: string) => {
  try {
    const doc = yaml.load(rawYaml) as FlowSpec
    if (!doc || !Array.isArray(doc.steps)) return

    flowName.value = doc.name || 'unnamed_flow'
    flowDesc.value = doc.description || ''
    cronValue.value = doc.cron || (doc.trigger as any)?.cron || ''
    webhookTokenValue.value = (doc.trigger as any)?.webhook_token || 'token-123'

    const newNodes: any[] = []
    const newEdges: any[] = []

    const startX = 180
    const startY = 40
    const nodeGapY = 160

    doc.steps.forEach((step: StepSpec, index: number) => {
      newNodes.push({
        id: step.id,
        type: 'flowNode',
        position: { x: startX, y: startY + index * nodeGapY },
        data: {
          step,
          index,
          status: 'idle',
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
  const steps: StepSpec[] = nodes.value.map((n) => n.data.step)
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
      webhook_enabled: true,
      webhook_token: webhookTokenValue.value,
    }
  }

  yamlCode.value = yaml.dump(doc, { indent: 2, noRefs: true })
}

/** 格式化当前 YAML */
const formatYaml = () => {
  try {
    const doc = yaml.load(yamlCode.value)
    yamlCode.value = yaml.dump(doc, { indent: 2, noRefs: true })
    message.success('YAML 格式化完成')
  } catch {
    message.error('YAML 语法错误，无法格式化')
  }
}

const onYamlEdited = (newYaml: string) => {
  yamlCode.value = newYaml
  parseYamlToCanvas(newYaml)
}

// ---------------- 节点交互与拖拽 ----------------

const onNodeClick = (event: any) => {
  selectedNodeId.value = event.node.id
}

const onPaneClick = () => {
  selectedNodeId.value = null
}

const onConnect = (connection: any) => {
  edges.value.push({
    ...connection,
    animated: true,
    style: { stroke: '#3b82f6', strokeWidth: 2 },
  })
}

const addNodeFromPalette = (item: ComponentItem) => {
  const count = nodes.value.length
  const stepId = `step_${count + 1}_${item.type.split('.').pop()}`
  const lastNode = nodes.value[nodes.value.length - 1]

  const newStep: StepSpec = {
    id: stepId,
    name: item.label,
    action: {
      type: item.type,
      params: item.defaultParams || {},
    },
  }

  if (item.category === 'check') {
    newStep.check = {
      type: item.type,
      params: item.defaultParams || { value: true },
    }
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
  message.success(`已添加步骤: ${item.label}`)
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
  const node = nodes.value.find((n) => n.id === oldId)
  if (!node) return
  node.id = newId
  node.data.step.id = newId

  // 更新连线关联
  edges.value.forEach((edge) => {
    if (edge.source === oldId) edge.source = newId
    if (edge.target === oldId) edge.target = newId
  })

  selectedNodeId.value = newId
  syncCanvasToYaml()
}

const deleteStep = (stepId: string) => {
  nodes.value = nodes.value.filter((n) => n.id !== stepId)
  edges.value = edges.value.filter((e) => e.source !== stepId && e.target !== stepId)
  // 重新编号
  nodes.value.forEach((n, idx) => {
    n.data.index = idx
  })
  selectedNodeId.value = nodes.value[0]?.id || null
  syncCanvasToYaml()
  message.info('步骤已删除')
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
  webhookTokenValue.value = token
  syncCanvasToYaml()
}

const handleSelectExample = (key: string) => {
  const ex = FLOW_EXAMPLES[key as keyof typeof FLOW_EXAMPLES]
  if (!ex) return
  yamlCode.value = ex.yaml
  parseYamlToCanvas(ex.yaml)
  setTimeout(() => fitView({ padding: 0.2 }), 100)
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
    message.success('流程执行完成！')
  } catch (err: any) {
    nodes.value.forEach((n) => {
      n.data.status = 'failed'
    })
    message.error(`流程执行失败: ${err.message || err}`)
  }
}

const handleStepDebug = () => {
  syncCanvasToYaml()
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

onMounted(() => {
  const pendingYaml = sessionStorage.getItem('autoflow_canvas_yaml')
  if (pendingYaml) {
    sessionStorage.removeItem('autoflow_canvas_yaml')
    yamlCode.value = pendingYaml
  }
  parseYamlToCanvas(yamlCode.value)
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
  padding: 0 16px;
  flex: none;
  z-index: 10;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.flow-meta {
  display: flex;
  flex-direction: column;
}

.flow-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.flow-icon {
  font-size: 14px;
}

.flow-name-input {
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  background: transparent;
  padding: 0;
  width: 180px;
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
  width: 260px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
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
  width: 250px;
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
  width: 360px;
  flex: none;
  height: 100%;
}
</style>
