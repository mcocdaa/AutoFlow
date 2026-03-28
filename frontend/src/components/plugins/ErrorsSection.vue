<template>
  <div class="errors-section">
    <div class="section-title">
      <WarningOutlined class="title-icon" />
      Load Errors
    </div>
    <a-card>
      <a-table :data-source="errors" :pagination="false" :scroll="{ x: 600 }">
        <a-table-column title="Plugin ID" data-index="plugin_id" width="180" />
        <a-table-column title="Path" data-index="file_path" />
        <a-table-column title="Error" data-index="error" />
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { WarningOutlined } from '@ant-design/icons-vue'
import type { PluginError } from '../../types/plugins'

defineProps<{
  errors: PluginError[]
}>()
</script>

<style scoped>
.errors-section {
  margin-top: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin-bottom: 16px;
}

.title-icon {
  margin-right: 8px;
  color: var(--flow-color-warning);
  font-size: 20px;
}
</style>
