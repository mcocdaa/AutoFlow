<template>
  <a-card class="plugin-card" :hoverable="true">
    <template #title>
      <div class="card-header">
        <span class="plugin-name">{{ plugin.name }}</span>
        <a-tag class="version-tag">v{{ plugin.version }}</a-tag>
      </div>
    </template>
    <p v-if="description" class="plugin-description">{{ description }}</p>
    <p v-else class="plugin-description is-muted">暂无描述</p>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getPluginDescription } from '../../constants/plugins'
import type { Plugin } from '../../types/plugins'

const props = defineProps<{
  plugin: Plugin
}>()

const description = computed(() => getPluginDescription(props.plugin.name))
</script>

<style scoped>
.plugin-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.plugin-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--flow-text-title);
  word-break: break-all;
}

.version-tag {
  flex: none;
  margin-inline-end: 0;
  color: var(--flow-text-secondary);
}

.plugin-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--flow-text-secondary);
}

.plugin-description.is-muted {
  color: var(--flow-text-disabled);
}
</style>
