<script setup lang="ts">
import { computed, ref } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useExecutionStore } from "../../../stores/execution";

const props = defineProps<{
  data: any;
  selected?: boolean;
  id?: string;
}>();

const executionStore = useExecutionStore();
const showOutput = ref(false);

const executionState = computed(() => {
  if (!props.id) return null;
  return executionStore.nodes[props.id];
});

const hasOutput = computed(
  () =>
    executionState.value?.output !== null &&
    executionState.value?.output !== undefined,
);
const outputDisplay = computed(() => {
  if (!executionState.value?.output) return "";
  const output = executionState.value.output;
  if (typeof output === "object") {
    return JSON.stringify(output, null, 2);
  }
  return String(output);
});

const copyOutput = () => {
  if (outputDisplay.value) {
    navigator.clipboard.writeText(outputDisplay.value);
  }
};
</script>

<template>
  <div class="node-container" :class="{ 'node-selected': selected }">
    <Handle type="target" :position="Position.Left" />
    <div class="node-header">
      <span class="node-icon">📤</span>
      <span class="node-title">{{ data.label || "Output" }}</span>
      <button
        v-if="hasOutput"
        type="button"
        class="toggle-btn"
        @click.stop="showOutput = !showOutput"
      >
        {{ showOutput ? "▼" : "▶" }}
      </button>
    </div>

    <div v-if="showOutput && hasOutput" class="output-content">
      <div class="output-header">
        <span class="output-label">执行结果</span>
        <button type="button" class="copy-btn" @click.stop="copyOutput">
          📋 复制
        </button>
      </div>
      <pre class="output-text">{{ outputDisplay }}</pre>
    </div>
  </div>
</template>

<style scoped>
.node-container {
  width: 220px;
  border: 2px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  transition: all 0.2s ease;
}

.node-selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

.node-header {
  height: 40px;
  background-color: #10b981;
  color: white;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-weight: 600;
  font-size: 14px;
  padding: 0 12px;
  gap: 8px;
}

.node-icon {
  font-size: 18px;
}

.node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toggle-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.output-content {
  border-top: 1px solid #d1d5db;
  background: #f9fafb;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f0fdf4;
  border-bottom: 1px solid #bbf7d0;
}

.output-label {
  font-size: 12px;
  font-weight: 600;
  color: #166534;
}

.copy-btn {
  font-size: 11px;
  padding: 4px 8px;
  background: white;
  border: 1px solid #86efac;
  border-radius: 4px;
  cursor: pointer;
  color: #166534;
}

.copy-btn:hover {
  background: #f0fdf4;
}

.output-text {
  margin: 0;
  padding: 12px;
  font-size: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  color: #1f2937;
}
</style>
