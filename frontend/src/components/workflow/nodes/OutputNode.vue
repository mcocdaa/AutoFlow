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
  min-width: 200px;
  max-width: 260px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
  background: #1a1f2e;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.04) inset;
}

.node-selected {
  border-color: rgba(129, 140, 248, 0.6) !important;
  box-shadow:
    0 0 0 2px rgba(129, 140, 248, 0.25),
    0 8px 24px rgba(0, 0, 0, 0.5) !important;
  transform: scale(1.015);
}

.node-header {
  height: 32px;
  background-color: #10b981;
  color: white;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-weight: 600;
  font-size: 12px;
  padding: 0 10px;
  gap: 7px;
  background: linear-gradient(180deg, #10b981 0%, color-mix(in srgb, #10b981 85%, black) 100%);
}

.node-icon {
  font-size: 13px;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.toggle-btn {
  background: rgba(255, 255, 255, 0.12);
  border: none;
  color: rgba(255, 255, 255, 0.8);
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.22);
  color: white;
}

.output-content {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: #131827;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: rgba(16, 185, 129, 0.08);
  border-bottom: 1px solid rgba(16, 185, 129, 0.12);
}

.output-label {
  font-size: 11px;
  font-weight: 600;
  color: #34d399;
}

.copy-btn {
  font-size: 10px;
  padding: 3px 8px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 4px;
  cursor: pointer;
  color: #34d399;
  transition: all 0.15s;
}

.copy-btn:hover {
  background: rgba(16, 185, 129, 0.25);
}

.output-text {
  margin: 0;
  padding: 8px 10px;
  font-size: 11px;
  font-family: "SF Mono", "Fira Code", "Consolas", monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 180px;
  overflow-y: auto;
  color: #cbd5e1;
}
</style>
