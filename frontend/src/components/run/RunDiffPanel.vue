<template>
  <div v-if="diff" class="diff-panel">
    <div class="diff-summary">
      <div class="summary-card">
        <span class="summary-label">基准</span>
        <span class="summary-value">{{ diff.base.flow_name }}</span>
        <a-tag :color="RUN_STATUS_META[diff.base.status].color">
          {{ RUN_STATUS_META[diff.base.status].text }}
        </a-tag>
        <span class="summary-meta af-mono">{{ diff.base.run_id.slice(0, 8) }}</span>
        <span class="summary-meta">
          {{ diff.base.duration_ms !== null ? diff.base.duration_ms + ' ms' : '—' }}
        </span>
      </div>
      <div class="summary-card">
        <span class="summary-label">对比</span>
        <span class="summary-value">{{ diff.target.flow_name }}</span>
        <a-tag :color="RUN_STATUS_META[diff.target.status].color">
          {{ RUN_STATUS_META[diff.target.status].text }}
        </a-tag>
        <span class="summary-meta af-mono">{{ diff.target.run_id.slice(0, 8) }}</span>
        <span class="summary-meta">
          {{ diff.target.duration_ms !== null ? diff.target.duration_ms + ' ms' : '—' }}
        </span>
      </div>
    </div>

    <a-empty v-if="diff.steps.length === 0" description="没有可对比的步骤" />

    <a-collapse v-else class="diff-steps">
      <a-collapse-panel
        v-for="step in diff.steps"
        :key="step.step_id + ':' + step.base_index + ':' + step.target_index"
      >
        <template #header>
          <div class="diff-step-header">
            <span class="diff-step-id af-mono">{{ step.step_id }}</span>
            <a-tag v-if="step.status_changed" color="warning">状态变更</a-tag>
            <a-tag v-if="step.check_changed" color="warning">检查变更</a-tag>
            <a-tag v-if="step.output_changed" color="processing">输出变更</a-tag>
            <span v-if="step.base_index === null" class="diff-meta">仅对比侧存在</span>
            <span v-if="step.target_index === null" class="diff-meta">仅基准侧存在</span>
          </div>
        </template>

        <div class="diff-status-row">
          <div class="diff-side">
            <span class="diff-side-label">基准</span>
            <a-tag
              v-if="step.base_status"
              :color="STEP_STATUS_META[step.base_status].color"
            >
              {{ STEP_STATUS_META[step.base_status].text }}
            </a-tag>
            <span v-else class="diff-meta">—</span>
            <a-tag v-if="step.base_check_passed !== null" :color="step.base_check_passed ? 'success' : 'error'">
              {{ step.base_check_passed ? '检查通过' : '检查未通过' }}
            </a-tag>
          </div>
          <div class="diff-side">
            <span class="diff-side-label">对比</span>
            <a-tag
              v-if="step.target_status"
              :color="STEP_STATUS_META[step.target_status].color"
            >
              {{ STEP_STATUS_META[step.target_status].text }}
            </a-tag>
            <span v-else class="diff-meta">—</span>
            <a-tag v-if="step.target_check_passed !== null" :color="step.target_check_passed ? 'success' : 'error'">
              {{ step.target_check_passed ? '检查通过' : '检查未通过' }}
            </a-tag>
          </div>
        </div>

        <a-alert
          v-if="step.base_error || step.target_error"
          type="error"
          :closable="false"
          show-icon
          class="diff-error"
          :message="`基准: ${step.base_error || '—'} / 对比: ${step.target_error || '—'}`"
        />

        <div v-if="step.output_diff.length > 0" class="diff-output">
          <span class="output-label">输出差异（{{ step.output_diff.length }} 处）</span>
          <div v-for="entry in step.output_diff" :key="entry.path" class="diff-entry">
            <span class="diff-path af-mono">{{ entry.path }}</span>
            <div class="diff-values">
              <pre class="diff-value af-mono">{{ formatOutput(entry.base) }}</pre>
              <span class="diff-arrow">→</span>
              <pre class="diff-value af-mono">{{ formatOutput(entry.target) }}</pre>
            </div>
          </div>
        </div>
        <div v-else class="diff-output">
          <span class="output-label">输出无差异</span>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </div>
  <a-empty v-else description="请选择两个运行进行对比" />
</template>

<script setup lang="ts">
import { RUN_STATUS_META, STEP_STATUS_META } from '../../constants/run-status'
import type { RunDiff } from '../../types/runs'

defineProps<{
  diff: RunDiff | null
}>()

const formatOutput = (value: unknown): string => {
  if (value === undefined || value === null) return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}
</script>

<style scoped>
.diff-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diff-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  background: var(--flow-bg-layer);
  border-radius: 8px;
}

.summary-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--flow-text-secondary);
}

.summary-value {
  font-weight: 500;
  color: var(--flow-text-primary);
}

.summary-meta {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.diff-step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.diff-step-id {
  font-weight: 500;
  color: var(--flow-text-primary);
}

.diff-meta {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.diff-status-row {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.diff-side {
  display: flex;
  align-items: center;
  gap: 8px;
}

.diff-side-label {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.diff-error {
  margin-bottom: 12px;
}

.diff-output {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.output-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-secondary);
}

.diff-entry {
  padding: 8px 10px;
  background: var(--flow-bg-layer);
  border-radius: 8px;
}

.diff-path {
  font-size: 12px;
  color: var(--flow-color-primary);
}

.diff-values {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 6px;
}

.diff-value {
  flex: 1;
  min-width: 0;
  margin: 0;
  padding: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--flow-text-primary);
  background: var(--flow-bg-card);
  border-radius: 6px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-arrow {
  color: var(--flow-text-secondary);
}
</style>
