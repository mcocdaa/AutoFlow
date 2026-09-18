<template>
  <a-card class="result-card">
    <template #title>
      <div class="card-header">
        <div class="card-title">
          <BarChartOutlined class="card-icon" />
          执行结果
        </div>
        <a-tag v-if="run" :color="runStatus.color">{{ runStatus.text }}</a-tag>
      </div>
    </template>

    <div v-if="error" class="error-section">
      <a-alert :message="error" type="error" show-icon />
    </div>

    <div v-if="run" class="run-details">
      <div class="run-meta">
        <div class="meta-item">
          <span class="meta-label">流程</span>
          <span class="meta-value">{{ run.flow_name }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Run ID</span>
          <span class="meta-value af-mono">{{ run.run_id }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">耗时</span>
          <span class="meta-value">{{ run.duration_ms !== null ? run.duration_ms + ' ms' : '—' }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">开始</span>
          <span class="meta-value">{{ formatTime(run.started_at) }}</span>
        </div>
        <div v-if="run.parent_run_id" class="meta-item">
          <span class="meta-label">分叉自</span>
          <span class="meta-value af-mono">
            {{ run.parent_run_id }} · 第 {{ run.fork_step_index }} 步
          </span>
        </div>
      </div>

      <a-alert v-if="run.error" :message="run.error" type="error" show-icon class="run-error" />

      <div class="steps-section">
        <h4 class="steps-title">
          <UnorderedListOutlined />
          步骤
        </h4>
        <a-collapse v-if="run.steps.length > 0" class="steps-collapse">
          <a-collapse-panel v-for="(step, index) in run.steps" :key="step.step_id">
            <template #header>
              <div class="step-header">
                <span class="step-status" :class="'is-' + step.status"></span>
                <span class="step-id af-mono">{{ step.step_id }}</span>
                <a-tag
                  v-if="step.status !== 'success'"
                  :color="STEP_STATUS_META[step.status].color"
                  class="step-status-tag"
                >
                  {{ STEP_STATUS_META[step.status].text }}
                </a-tag>
                <span class="step-duration">{{ step.duration_ms }} ms</span>
                <a-dropdown v-if="forkable" class="step-fork" @click.stop>
                  <a-button type="link" size="small" @click.stop>
                    分叉
                    <DownOutlined />
                  </a-button>
                  <template #overlay>
                    <a-menu @click="onForkMenuClick($event, index)">
                      <a-menu-item key="retry">重试该步</a-menu-item>
                      <a-menu-item
                        key="after"
                        :disabled="index >= run.steps.length - 1"
                      >
                        从下一步继续
                      </a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
            </template>

            <div v-if="step.error" class="step-error">
              <a-alert :message="step.error" type="error" :closable="false" show-icon />
            </div>

            <div v-if="step.check_passed !== null" class="step-check">
              <span class="check-label">检查</span>
              <a-tag :color="step.check_passed ? 'success' : 'error'">
                {{ step.check_passed ? '通过' : '未通过' }}
              </a-tag>
            </div>

            <div v-if="step.iterations && step.iterations.length > 0" class="iterations">
              <span class="output-label">迭代（for_each，共 {{ step.iterations.length }} 次）</span>
              <div
                v-for="(iteration, index) in step.iterations"
                :key="index"
                class="iteration"
              >
                <div class="iteration-head">
                  <span class="iteration-index">#{{ index + 1 }}</span>
                  <span class="iteration-item af-mono">{{ formatInline(iteration.item) }}</span>
                  <a-tag
                    v-if="iteration.check_passed !== null"
                    :color="iteration.check_passed ? 'success' : 'error'"
                  >
                    {{ iteration.check_passed ? '通过' : '未通过' }}
                  </a-tag>
                  <span class="iteration-duration">{{ iteration.duration_ms }} ms</span>
                </div>
                <a-alert
                  v-if="iteration.error"
                  :message="iteration.error"
                  type="error"
                  :closable="false"
                  show-icon
                  class="iteration-error"
                />
                <pre class="output-pre af-mono">{{ formatOutput(iteration.output) }}</pre>
              </div>
            </div>

            <div v-if="artifactsOf(step).length > 0" class="artifacts">
              <span class="output-label">产物</span>
              <div class="artifact-list">
                <a
                  v-for="artifact in artifactsOf(step)"
                  :key="artifact.path"
                  class="artifact-link"
                  :href="artifactUrl(artifact.path)"
                  :download="artifact.path"
                >
                  <FileOutlined />
                  <span class="artifact-path af-mono">{{ artifact.path }}</span>
                  <span class="artifact-size">{{ formatSize(artifact.size) }}</span>
                </a>
              </div>
            </div>

            <div class="step-output">
              <span class="output-label">输出</span>
              <pre class="output-pre af-mono">{{ formatOutput(step.action_output) }}</pre>
            </div>
          </a-collapse-panel>
        </a-collapse>
        <a-empty v-else description="该流程没有步骤记录" :image="emptyImage" />
      </div>

      <div v-if="run.hook_results?.length" class="hooks-section">
        <h4 class="steps-title">
          <ApiOutlined />
          Hooks
        </h4>
        <div v-for="(hook, index) in run.hook_results" :key="index" class="hook-item">
          <div class="hook-head">
            <a-tag :color="hook.hook === 'on_success' ? 'green' : 'red'">
              {{ hook.hook === 'on_success' ? '成功钩子' : '失败钩子' }}
            </a-tag>
            <span class="hook-action af-mono">{{ hook.action_type }}</span>
            <a-tag :color="hook.status === 'success' ? 'success' : 'error'">
              {{ hook.status === 'success' ? '执行成功' : '执行失败' }}
            </a-tag>
            <span class="hook-duration">{{ hook.duration_ms }} ms</span>
          </div>
          <a-alert
            v-if="hook.error"
            :message="hook.error"
            type="error"
            :closable="false"
            show-icon
            class="hook-error"
          />
          <span class="output-label">输出</span>
          <pre class="output-pre af-mono">{{ formatOutput(hook.output) }}</pre>
          <div v-if="artifactsOfValue(hook.output).length > 0" class="artifacts">
            <span class="output-label">产物</span>
            <div class="artifact-list">
              <a
                v-for="artifact in artifactsOfValue(hook.output)"
                :key="artifact.path"
                class="artifact-link"
                :href="artifactUrl(artifact.path)"
                :download="artifact.path"
              >
                <FileOutlined />
                <span class="artifact-path af-mono">{{ artifact.path }}</span>
                <span class="artifact-size">{{ formatSize(artifact.size) }}</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <a-empty
      v-else-if="!error"
      class="empty-state"
      description="在左侧编辑或加载 Flow YAML 后点击执行"
      :image="emptyImage"
    />
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Empty } from 'ant-design-vue'
import {
  ApiOutlined,
  BarChartOutlined,
  DownOutlined,
  FileOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import { buildArtifactUrl } from '../../api'
import { RUN_STATUS_META, STEP_STATUS_META } from '../../constants/run-status'
import { artifactsOfValue, collectArtifacts, uniqueArtifacts } from '../../utils/artifacts'
import type { ArtifactRef, RunResult, RunStepResult } from '../../types/runs'

const props = defineProps<{
  run: RunResult | null
  error: string | null
  forkable?: boolean
}>()

const emit = defineEmits<{
  (e: 'fork', nextStepIndex: number): void
}>()

const onForkMenuClick = (event: { key: string | number }, index: number) => {
  emit('fork', event.key === 'retry' ? index : index + 1)
}

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const runStatus = computed(() =>
  props.run ? RUN_STATUS_META[props.run.status] : { color: 'default', text: '' },
)

const formatOutput = (output: unknown): string => {
  if (output === undefined || output === null) return '—'
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

const formatInline = (value: unknown): string => {
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

const formatTime = (value: string | null): string => {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

const formatSize = (size: number): string => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const artifactsOf = (step: RunStepResult): ArtifactRef[] => {
  const refs = collectArtifacts(step.action_output)
  step.iterations?.forEach((iteration) => collectArtifacts(iteration.output, refs))
  return uniqueArtifacts(refs)
}

const artifactUrl = (path: string): string =>
  props.run ? buildArtifactUrl(props.run.run_id, path) : '#'
</script>

<style scoped>
.result-card {
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

.error-section,
.run-error {
  margin-bottom: 20px;
}

.run-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px 24px;
  padding: 16px;
  background: var(--flow-bg-layer);
  border-radius: 10px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.meta-label {
  flex: none;
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-secondary);
}

.meta-value {
  font-size: 13px;
  color: var(--flow-text-primary);
  word-break: break-all;
}

.steps-section {
  margin-top: 24px;
}

.hooks-section {
  margin-top: 24px;
}

.hook-item {
  padding: 14px 16px;
  margin-bottom: 12px;
  background: var(--flow-bg-layer);
  border-radius: 10px;
}

.hook-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.hook-action {
  font-size: 13px;
  font-weight: 500;
  color: var(--flow-text-primary);
}

.hook-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.hook-error {
  margin-bottom: 10px;
}

.hook-item .output-pre {
  background: var(--flow-bg-card);
}

.steps-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.steps-title :deep(.anticon) {
  color: var(--flow-color-primary);
}

.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
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

.step-status-tag {
  margin-inline-end: 0;
}

.step-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.step-fork {
  margin-left: 8px;
}

.step-error {
  margin-bottom: 12px;
}

.step-check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.check-label,
.output-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-secondary);
}

.iterations {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.iteration {
  padding: 12px;
  background: var(--flow-bg-layer);
  border-radius: 8px;
}

.iteration-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.iteration-index {
  font-size: 12px;
  font-weight: 600;
  color: var(--flow-text-secondary);
}

.iteration-item {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: var(--flow-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.iteration-duration {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.iteration-error {
  margin-bottom: 8px;
}

.iteration .output-pre {
  background: var(--flow-bg-card);
}

.artifacts {
  margin-bottom: 12px;
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
  background: #DBEAFE;
}

.artifact-path {
  word-break: break-all;
}

.artifact-size {
  color: var(--flow-text-secondary);
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

.empty-state {
  padding: 32px 0;
}
</style>
