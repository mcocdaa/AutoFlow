<script setup lang="ts">
import { Handle, Position } from "@vue-flow/core";

defineProps<{ data: any; selected?: boolean }>();
</script>

<template>
  <div class="node-container" :class="{ 'node-selected': selected }">
    <Handle type="target" :position="Position.Left" />
    <div class="node-header">
      {{ data.label || "LLM" }}
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<style scoped>
.node-container {
  width: 200px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  background: white;
  transition: all 0.2s ease;
}

.node-container.node-selected {
  border: 3px solid #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

.node-header {
  height: 36px;
  background-color: var(--flow-color-success);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
}
</style>
