<template>
  <a-card class="result-card">
    <template #title>
      <div class="card-header">
        <div class="card-title">
          <BarChartOutlined class="card-icon" />
          Execution Result
        </div>
        <a-tag v-if="run" :color="statusColor" class="status-tag">{{
          run.status
        }}</a-tag>
      </div>
    </template>

    <div v-if="error" class="error-section">
      <a-alert :message="error" type="error" show-icon />
    </div>

    <div v-if="run" class="run-details">
      <div class="run-info">
        <div class="info-item">
          <UserOutlined class="info-icon" />
          <span class="info-label">Run ID:</span>
          <span class="info-value">{{ run.run_id }}</span>
        </div>
        <div class="info-item">
          <ClockCircleOutlined class="info-icon" />
          <span class="info-label">Duration:</span>
          <span class="info-value">{{ run.duration_ms }} ms</span>
        </div>
      </div>

      <div class="steps-section">
        <h4 class="steps-title">
          <UnorderedListOutlined />
          Steps
        </h4>
        <a-collapse class="steps-collapse">
          <a-collapse-panel
            v-for="step in run.steps"
            :key="step.step_id"
            :header="step.step_id + ' (' + step.status + ')'"
          >
            <div v-if="step.error" class="step-error">
              <a-alert :message="step.error" type="error" :closable="false" />
            </div>
            <div class="step-output">
              <pre class="output-pre">{{
                JSON.stringify(step.action_output, null, 2)
              }}</pre>
            </div>
            <div v-if="step.check_passed !== null" class="step-check">
              <span class="check-label">Check:</span>
              <a-tag
                :color="step.check_passed ? 'green' : 'red'"
                class="check-tag"
              >
                {{ step.check_passed ? "Passed" : "Failed" }}
              </a-tag>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </div>
    </div>
    <div v-else class="empty-state">
      <a-empty description="Create a flow YAML and click Execute to run">
        <template #image>
          <div class="empty-icon">
            <CloudServerOutlined />
          </div>
        </template>
      </a-empty>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  BarChartOutlined,
  UserOutlined,
  ClockCircleOutlined,
  UnorderedListOutlined,
  CloudServerOutlined,
} from "@ant-design/icons-vue";
import type { RunResult } from "../../types/runs";

const props = defineProps<{
  run: RunResult | null;
  error: string | null;
}>();

const statusColor = computed(() => {
  if (!props.run) return "blue";
  if (props.run.status === "success") return "green";
  if (props.run.status === "failed") return "red";
  return "orange";
});
</script>

<style scoped>
.result-card {
  border-radius: 12px;
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.card-icon {
  margin-right: 8px;
  color: var(--flow-color-primary);
}

.status-tag {
  font-size: 13px;
}

.error-section {
  margin-bottom: 20px;
}

.run-details {
  padding: 10px 0;
}

.run-info {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background-color: var(--flow-bg-layer);
  border-radius: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-icon {
  color: var(--flow-color-primary);
  font-size: 16px;
}

.info-label {
  font-weight: 500;
  color: var(--flow-text-secondary);
}

.info-value {
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
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
  font-size: 16px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin-bottom: 16px;
  gap: 8px;
}

.steps-title :deep(.anticon) {
  color: var(--flow-color-primary);
}

.empty-icon {
  font-size: 64px;
  color: var(--flow-text-disabled);
}
</style>
