<template>
  <a-card class="result-card">
    <template #title>
      <div class="card-header">
        <div class="card-title">
          <BarChartOutlined class="card-icon" />
          执行结果
        </div>
        <a-tag v-if="run" :color="statusColor">{{ statusText }}</a-tag>
      </div>
    </template>

    <div v-if="error" class="error-section">
      <a-alert :message="error" type="error" show-icon />
    </div>

    <div v-if="run" class="run-details">
      <div class="run-meta">
        <div class="meta-item">
          <span class="meta-label">Run ID</span>
          <span class="meta-value af-mono">{{ run.run_id }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">耗时</span>
          <span class="meta-value">{{ run.duration_ms !== null ? run.duration_ms + ' ms' : '—' }}</span>
        </div>
      </div>

      <div class="steps-section">
        <h4 class="steps-title">
          <UnorderedListOutlined />
          步骤
        </h4>
        <a-collapse v-if="run.steps.length > 0" class="steps-collapse">
          <a-collapse-panel v-for="step in run.steps" :key="step.step_id">
            <template #header>
              <div class="step-header">
                <span class="step-status" :class="'is-' + step.status"></span>
                <span class="step-id af-mono">{{ step.step_id }}</span>
                <span class="step-duration">{{ step.duration_ms }} ms</span>
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
            <div class="step-output">
              <span class="output-label">输出</span>
              <pre class="output-pre af-mono">{{ formatOutput(step.action_output) }}</pre>
            </div>
          </a-collapse-panel>
        </a-collapse>
        <a-empty v-else description="该流程没有步骤记录" :image="emptyImage" />
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
  BarChartOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import type { RunResult, RunStatus } from '../../types/runs'

const props = defineProps<{
  run: RunResult | null
  error: string | null
}>()

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const RUN_STATUS: Record<RunStatus, { color: string; text: string }> = {
  success: { color: 'green', text: '成功' },
  failed: { color: 'red', text: '失败' },
  running: { color: 'orange', text: '运行中' },
}

const statusColor = computed(() => (props.run ? RUN_STATUS[props.run.status].color : 'default'))
const statusText = computed(() => (props.run ? RUN_STATUS[props.run.status].text : ''))

const formatOutput = (output: unknown): string => {
  if (output === undefined || output === null) return '—'
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}
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

.error-section {
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

.step-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--flow-text-secondary);
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
