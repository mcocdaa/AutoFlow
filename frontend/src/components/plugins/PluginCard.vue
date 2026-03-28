<template>
  <a-card class="plugin-card" :hoverable="true">
    <template #title>
      <div class="card-header">
        <div class="plugin-name">{{ plugin.name }}</div>
        <a-tag color="blue" class="version-tag">{{ plugin.version }}</a-tag>
      </div>
    </template>
    <div class="plugin-body">
      <div class="plugin-description">{{ description }}</div>
      <div class="plugin-status">
        <CheckCircleOutlined class="status-icon" />
        <span>Active</span>
      </div>
      <div class="plugin-actions">
        <a-button size="small" @click="$emit('configure', plugin)">配置</a-button>
        <a-button size="small" @click="$emit('disable', plugin)">禁用</a-button>
        <a-button size="small" type="primary" @click="$emit('viewDocs', plugin)">文档</a-button>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircleOutlined } from '@ant-design/icons-vue'
import { getPluginDescription } from '../../constants/plugins'
import type { Plugin } from '../../types/plugins'

const props = defineProps<{
  plugin: Plugin
}>()

defineEmits<{
  configure: [plugin: Plugin]
  disable: [plugin: Plugin]
  viewDocs: [plugin: Plugin]
}>()

const description = computed(() => getPluginDescription(props.plugin.name))
</script>

<style scoped>
.plugin-card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plugin-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--flow-text-title);
}

.version-tag {
  font-size: 12px;
}

.plugin-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plugin-description {
  font-size: 14px;
  color: var(--flow-text-secondary);
  line-height: 1.5;
}

.plugin-status {
  display: flex;
  align-items: center;
  color: var(--flow-color-success);
  font-weight: 500;
  gap: 8px;
}

.status-icon {
  font-size: 16px;
}

.plugin-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
