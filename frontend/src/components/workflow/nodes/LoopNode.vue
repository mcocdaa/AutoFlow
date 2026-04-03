<script setup lang="ts">
import { Handle, Position } from "@vue-flow/core";

defineProps<{ data: any; selected?: boolean }>();
</script>

<template>
  <div class="node-container" :class="{ 'node-selected': selected }">
    <Handle type="target" :position="Position.Left" />
    <div class="node-header">
      {{ data.label || "Loop" }}
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<style scoped>
.node-container {
  min-width: 180px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
  background: #1a1f2e;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.04) inset;
}

.node-container.node-selected {
  border-color: rgba(129, 140, 248, 0.6) !important;
  box-shadow:
    0 0 0 2px rgba(129, 140, 248, 0.25),
    0 8px 24px rgba(0, 0, 0, 0.5) !important;
  transform: scale(1.015);
}

.node-header {
  height: 32px;
  background-color: var(--flow-color-purple);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.3px;
  background: linear-gradient(180deg, var(--flow-color-purple) 0%, color-mix(in srgb, var(--flow-color-purple) 85%, black) 100%);
}
</style>
