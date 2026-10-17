<template>
  <div class="af-page">
    <PageHeader
      :title="t('debug.title')"
      :description="t('debug.desc')"
      :icon="BugOutlined"
    />

    <a-row :gutter="[20, 20]">
      <a-col :xs="24" :md="12">
        <a-card class="source-card">
          <template #title>
            <div class="card-header">
              <div class="card-title">
                <FileTextOutlined class="card-icon" />
                Flow YAML
              </div>
              <a-select
                v-model:value="selectedExample"
                :placeholder="t('debug.loadExample')"
                class="example-select"
                @change="handleLoadExample"
              >
                <a-select-option
                  v-for="(example, key) in FLOW_EXAMPLES"
                  :key="key"
                  :value="key"
                >
                  {{ getFlowExampleLabel(example) }}
                </a-select-option>
              </a-select>
            </div>
          </template>

          <CodeEditor v-model="yamlContent" :min-height="320" />

          <FlowParamsEditor
            v-model:input-text="inputText"
            v-model:vars-text="varsText"
            :hint="exampleHint"
          />

          <div class="source-footer">
            <a-button type="primary" :loading="loading" @click="startSession">
              <template #icon><PlayCircleOutlined /></template>
              {{ t('debug.startDebug') }}
            </a-button>
          </div>
        </a-card>
      </a-col>

      <a-col :xs="24" :md="12">
        <a-card class="session-card">
          <template #title>
            <div class="card-header">
              <div class="card-title">
                <BugOutlined class="card-icon" />
                {{ t('debug.sessionTitle') }}
              </div>
              <a-tag v-if="session" :color="statusColor">{{ statusText }}</a-tag>
            </div>
          </template>

          <template v-if="session">
            <div class="session-toolbar">
              <a-button size="small" :disabled="finished || loading" @click="stepOnce">
                <template #icon><StepForwardOutlined /></template>
                {{ t('debug.stepOnce') }}
              </a-button>
              <a-button
                size="small"
                :disabled="finished || loading"
                @click="continueToBreakpoint"
              >
                <template #icon><FastForwardOutlined /></template>
                {{ t('debug.continueBp') }}
              </a-button>
              <a-button size="small" :disabled="finished || loading" @click="runToEnd">
                <template #icon><ThunderboltOutlined /></template>
                {{ t('debug.runToEnd') }}
              </a-button>
              <a-button size="small" type="text" danger :disabled="loading" @click="stopSession">
                <template #icon><StopOutlined /></template>
                {{ t('debug.stop') }}
              </a-button>
            </div>

            <div class="session-progress">
              <span>{{ t('debug.progress', { index: session.index, total: session.total_steps }) }}</span>
              <span class="session-run af-mono">{{ t('debug.runIdPrefix') }}: {{ session.run_id.slice(0, 8) }}</span>
              <span v-if="session.parent_run_id" class="session-fork af-mono">
                {{ t('debug.forkedFrom', { runId: session.parent_run_id.slice(0, 8), stepIdx: session.fork_step_index ?? 0 }) }}
              </span>
            </div>

            <a-alert
              v-if="session.error"
              :message="session.error"
              type="error"
              show-icon
              class="session-error"
            />

            <div class="step-list">
              <div
                v-for="(info, idx) in session.steps"
                :key="info.id"
                class="step-row"
                :class="{
                  'is-current': idx === session.index && !finished,
                  'is-pending': !resultOf(info.id),
                  'is-selected': selectedStepId === info.id,
                }"
                @click="selectedStepId = info.id"
              >
                <a-tooltip :title="breakpoints.has(info.id) ? t('debug.removeBp') : t('debug.setBp')">
                  <span
                    class="breakpoint"
                    :class="{ 'is-active': breakpoints.has(info.id) }"
                    @click.stop="toggleBreakpoint(info.id)"
                  >
                    <BugOutlined />
                  </span>
                </a-tooltip>
                <span class="step-status" :class="'is-' + stepStatus(info.id)"></span>
                <span class="step-id af-mono">{{ info.id }}</span>
                <span v-if="info.name" class="step-name">{{ displayStepName(info.name) }}</span>
                <a-tag v-if="info.for_each" class="step-flag">{{ t('debug.flagLoop') }}</a-tag>
                <a-tag v-if="info.has_condition" class="step-flag">{{ t('debug.flagCond') }}</a-tag>
                <a-tag v-if="info.retry_attempts > 0" class="step-flag">
                  {{ t('debug.flagRetry', { count: info.retry_attempts }) }}
                </a-tag>
                <span v-if="resultOf(info.id)" class="step-duration">
                  {{ resultOf(info.id)?.duration_ms }} ms
                </span>
              </div>
            </div>

            <div class="step-detail">
              <template v-if="selectedResult">
                <a-alert
                  v-if="selectedResult.error"
                  :message="selectedResult.error"
                  type="error"
                  :closable="false"
                  show-icon
                  class="detail-error"
                />
                <div v-if="selectedResult.check_passed !== null" class="detail-line">
                  <span class="detail-label">{{ t('debug.checkLabel') }}</span>
                  <a-tag :color="selectedResult.check_passed ? 'success' : 'error'">
                    {{ selectedResult.check_passed ? t('debug.checkPassed') : t('debug.checkFailed') }}
                  </a-tag>
                </div>
                <div v-if="selectedResult.iterations?.length" class="detail-block">
                  <span class="detail-label">
                    {{ t('debug.iterationsLabel', { count: selectedResult.iterations.length }) }}
                  </span>
                  <div
                    v-for="(iteration, i) in selectedResult.iterations"
                    :key="i"
                    class="iteration"
                  >
                    <span class="af-mono">
                      #{{ i + 1 }} {{ formatInline(iteration.item) }}
                    </span>
                    <span class="iteration-duration">{{ iteration.duration_ms }} ms</span>
                  </div>
                </div>
                <div v-if="selectedArtifacts.length" class="detail-block">
                  <span class="detail-label">{{ t('debug.artifactsLabel') }}</span>
                  <div class="artifact-list">
                    <a
                      v-for="artifact in selectedArtifacts"
                      :key="artifact.path"
                      class="artifact-link"
                      :href="artifactUrl(artifact.path)"
                      :download="artifact.path"
                    >
                      <FileOutlined />
                      <span class="af-mono">{{ artifact.path }}</span>
                      <span>{{ formatSize(artifact.size) }}</span>
                    </a>
                  </div>
                </div>
                <div class="detail-block">
                  <span class="detail-label">{{ t('debug.outputLabel') }}</span>
                  <pre class="output-pre af-mono">{{ formatOutput(selectedResult.action_output) }}</pre>
                </div>
              </template>
              <a-empty
                v-else
                :image="emptyImage"
                :description="t('debug.selectStepEmpty')"
              />
            </div>

            <div v-if="session.hook_results.length" class="hooks">
              <h4 class="hooks-title">
                <ApiOutlined />
                {{ t('debug.hooksTitle') }}
              </h4>
              <div
                v-for="(hook, index) in session.hook_results"
                :key="index"
                class="hook-item"
              >
                <a-tag :color="hook.hook === 'on_success' ? 'green' : 'red'">
                  {{ hook.hook === 'on_success' ? t('debug.hookOnSuccess') : t('debug.hookOnFailure') }}
                </a-tag>
                <span class="af-mono">{{ hook.action_type }}</span>
                <a-tag :color="hook.status === 'success' ? 'success' : 'error'">
                  {{ hook.status === 'success' ? t('debug.hookExecSuccess') : t('debug.hookExecFailed') }}
                </a-tag>
                <span class="hook-duration">{{ hook.duration_ms }} ms</span>
                <a-alert
                  v-if="hook.error"
                  :message="hook.error"
                  type="error"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>

            <div v-if="finished" class="session-done">
              <span>{{ t('debug.sessionDone') }}</span>
              <a-button type="link" size="small" @click="router.push('/runs')">
                {{ t('nav.runs') }}
              </a-button>
            </div>
          </template>

          <a-empty v-else :image="emptyImage" :description="t('debug.emptySession')" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import {
  ApiOutlined,
  BugOutlined,
  FastForwardOutlined,
  FileOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  StepForwardOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { buildArtifactUrl, getErrorMessage } from '../api'
import {
  createDebugSession,
  deleteDebugSession,
  fetchDebugSession,
  runDebugSession,
  stepDebugSession,
} from '../api/debug'
import {
  DEFAULT_FLOW_YAML_EN,
  DEFAULT_FLOW_YAML_ZH,
  FLOW_EXAMPLES,
  getDefaultFlowYaml,
  getFlowExampleHint,
  getFlowExampleLabel,
} from '../constants/flow-examples'
import { localizeFlowYaml, STEP_NAME_EN_MAP, useI18n } from '../i18n'
import { artifactsOfValue } from '../utils/artifacts'
import { formatInline, formatOutput, formatSize } from '../utils/format'
import { parseJsonInput, parseJsonObject } from '../utils/json'
import PageHeader from '../components/shared/PageHeader.vue'
import CodeEditor from '../components/shared/CodeEditor.vue'
import FlowParamsEditor from '../components/run/FlowParamsEditor.vue'
import type { DebugSessionSnapshot } from '../types/debug'

const { locale, t } = useI18n()
const route = useRoute()
const router = useRouter()
const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const yamlContent = ref(getDefaultFlowYaml())
watch(locale, (newLocale) => {
  const trimmed = yamlContent.value.trim()
  if (
    trimmed === DEFAULT_FLOW_YAML_ZH.trim() ||
    trimmed === DEFAULT_FLOW_YAML_EN.trim()
  ) {
    yamlContent.value = getDefaultFlowYaml()
    return
  }
  yamlContent.value = localizeFlowYaml(yamlContent.value, newLocale)
})
const selectedExample = ref<string>()
const inputText = ref('{}')
const varsText = ref('{}')
const session = ref<DebugSessionSnapshot | null>(null)
const breakpoints = ref(new Set<string>())
const selectedStepId = ref<string | null>(null)
const loading = ref(false)

const exampleHint = computed(() => {
  if (!selectedExample.value) return ''
  const example = FLOW_EXAMPLES[selectedExample.value as keyof typeof FLOW_EXAMPLES]
  return example ? getFlowExampleHint(example) : ''
})

const displayStepName = (name?: string | null) => {
  if (!name) return ''
  if (locale.value === 'en' && STEP_NAME_EN_MAP[name]) {
    return STEP_NAME_EN_MAP[name]
  }
  return name
}

const finished = computed(() => session.value?.status !== 'paused')
const statusText = computed(() => {
  if (!session.value) return ''
  if (session.value.status === 'success') return t('debug.status.success')
  if (session.value.status === 'failed') return t('debug.status.failed')
  return t('debug.status.paused')
})
const statusColor = computed(() => {
  if (session.value?.status === 'success') return 'green'
  if (session.value?.status === 'failed') return 'red'
  return 'orange'
})

const resultOf = (stepId: string) =>
  session.value?.results.find((result) => result.step_id === stepId)

const stepStatus = (stepId: string) => resultOf(stepId)?.status ?? 'pending'

const selectedResult = computed(() =>
  selectedStepId.value ? (resultOf(selectedStepId.value) ?? null) : null,
)

const selectedArtifacts = computed(() =>
  selectedResult.value ? artifactsOfValue(selectedResult.value.action_output) : [],
)

const artifactUrl = (path: string) =>
  session.value ? buildArtifactUrl(session.value.run_id, path) : '#'

const apply = (snapshot: DebugSessionSnapshot) => {
  session.value = snapshot
}

const withLoading = async (fn: () => Promise<void>) => {
  loading.value = true
  try {
    await fn()
  } catch (err) {
    message.error(getErrorMessage(err))
  } finally {
    loading.value = false
  }
}

const handleLoadExample = (key: string) => {
  const example = FLOW_EXAMPLES[key as keyof typeof FLOW_EXAMPLES]
  if (!example) return
  yamlContent.value = localizeFlowYaml(example.yaml, locale.value)
}

const startSession = () =>
  withLoading(async () => {
    const input = parseJsonInput(inputText.value, 'input')
    if (!input.ok) return
    const vars = parseJsonObject(varsText.value, 'vars')
    if (!vars) return
    if (session.value) {
      await deleteDebugSession(session.value.session_id).catch(() => {})
    }
    breakpoints.value = new Set()
    selectedStepId.value = null
    const snapshot = await createDebugSession(yamlContent.value, input.value, vars)
    apply(snapshot)
    await router.replace({ query: { session: snapshot.session_id } })
    if (snapshot.total_steps === 0) {
      message.info(t('debug.noStepsMsg'))
    }
  })

const stepOnce = () =>
  withLoading(async () => {
    if (!session.value) return
    apply(await stepDebugSession(session.value.session_id))
  })

const runToEnd = () =>
  withLoading(async () => {
    if (!session.value) return
    apply(await runDebugSession(session.value.session_id))
  })

const continueToBreakpoint = () =>
  withLoading(async () => {
    while (session.value && session.value.status === 'paused') {
      const next = session.value.steps[session.value.index]
      if (!next) break
      if (breakpoints.value.has(next.id)) {
        message.info(t('debug.pausedAtBp', { id: next.id }))
        break
      }
      apply(await stepDebugSession(session.value.session_id))
    }
  })

const stopSession = () =>
  withLoading(async () => {
    if (!session.value) return
    await deleteDebugSession(session.value.session_id)
    session.value = null
    selectedStepId.value = null
    await router.replace({ query: {} })
  })

const toggleBreakpoint = (stepId: string) => {
  const set = breakpoints.value
  if (set.has(stepId)) {
    set.delete(stepId)
  } else {
    set.add(stepId)
  }
}

onMounted(async () => {
  const pendingDebugYaml = sessionStorage.getItem('autoflow_debug_yaml')
  if (pendingDebugYaml) {
    sessionStorage.removeItem('autoflow_debug_yaml')
    yamlContent.value = localizeFlowYaml(pendingDebugYaml, locale.value)
  }
  const sessionId = route.query.session
  if (typeof sessionId !== 'string' || !sessionId) return
  loading.value = true
  try {
    apply(await fetchDebugSession(sessionId))
  } catch (err) {
    message.warning(t('debug.restoreFailed', { msg: getErrorMessage(err) }))
    await router.replace({ query: {} })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.source-card,
.session-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.card-icon {
  color: var(--flow-color-primary);
}

.example-select {
  width: 190px;
}

.source-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.session-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.session-toolbar :deep(.ant-btn) {
  white-space: nowrap;
  flex-shrink: 0;
  padding: 0 8px;
}

.session-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.session-run {
  margin-left: auto;
}

.session-fork {
  color: var(--flow-color-primary);
}

.session-error {
  margin-bottom: 12px;
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow: auto;
  padding-right: 4px;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--flow-border-color);
  border-radius: 8px;
  cursor: pointer;
}

.step-row.is-current {
  border-color: var(--flow-color-primary);
  background: var(--flow-color-primary-soft);
}

.step-row.is-selected {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.step-row.is-pending .step-id,
.step-row.is-pending .step-name {
  color: var(--flow-text-secondary);
}

.breakpoint {
  display: inline-flex;
  color: var(--flow-text-disabled);
}

.breakpoint.is-active {
  color: var(--flow-color-danger);
}

.step-status {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--flow-text-disabled);
}

.step-status.is-success {
  background: var(--flow-color-success);
}

.step-status.is-failed {
  background: var(--flow-color-danger);
}

.step-status.is-skipped {
  background: var(--flow-color-warning);
}

.step-id {
  font-size: 13px;
  font-weight: 500;
  color: var(--flow-text-primary);
}

.step-name {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.step-flag {
  margin-inline-end: 0;
  font-size: 11px;
}

.step-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.step-detail {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--flow-border-color-soft);
}

.detail-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.detail-block {
  margin-bottom: 12px;
}

.detail-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-secondary);
}

.detail-error {
  margin-bottom: 10px;
}

.iteration {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  margin-top: 6px;
  font-size: 12px;
  background: var(--flow-bg-layer);
  border-radius: 6px;
}

.iteration-duration {
  color: var(--flow-text-secondary);
}

.artifact-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
}

.artifact-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--flow-color-primary);
  background: var(--flow-color-primary-soft);
  border-radius: 8px;
}

.artifact-link:hover {
  background: #dbeafe;
}

.output-pre {
  margin: 6px 0 0;
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--flow-text-primary);
  background: var(--flow-bg-layer);
  border-radius: 8px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.hooks {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--flow-border-color-soft);
}

.hooks-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.hook-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 12px;
  margin-bottom: 8px;
  font-size: 12px;
  background: var(--flow-bg-layer);
  border-radius: 8px;
}

.hook-duration {
  margin-left: auto;
  color: var(--flow-text-secondary);
}

.session-done {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 16px;
  font-size: 12px;
  color: var(--flow-text-secondary);
}
</style>
