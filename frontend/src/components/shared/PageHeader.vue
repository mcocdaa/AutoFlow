<template>
  <div class="page-header">
    <div class="page-header-main">
      <span class="page-header-icon">
        <component :is="icon" />
      </span>
      <div class="page-header-text">
        <h2 class="page-header-title">{{ title }}</h2>
        <p v-if="description" class="page-header-description">{{ description }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  description?: string
  icon: Component
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: nowrap;
}

.page-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.page-header-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 40px;
  height: 40px;
  font-size: 20px;
  color: var(--flow-color-primary);
  background: var(--flow-color-primary-soft);
  border-radius: 10px;
}

.page-header-text {
  min-width: 0;
  flex: 1;
}

.page-header-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--flow-text-title);
  white-space: nowrap;
}

.page-header-description {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--flow-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
