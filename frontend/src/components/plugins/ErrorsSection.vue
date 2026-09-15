<template>
  <div class="errors-section">
    <h3 class="section-title">
      <WarningOutlined class="title-icon" />
      插件加载错误
    </h3>
    <a-card>
      <a-table :data-source="errors" :pagination="false" :scroll="{ x: 640 }">
        <a-table-column title="插件 ID" data-index="plugin_id" width="180" />
        <a-table-column title="文件路径" data-index="file_path" />
        <a-table-column title="错误信息" data-index="error" />
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
  gap: 8px;
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.title-icon {
  color: var(--flow-color-warning);
}
</style>
